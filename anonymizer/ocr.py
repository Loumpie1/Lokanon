"""OCR für gescannte PDF-Seiten – RapidOCR (ONNX Runtime, läuft offline mit den mitgelieferten
PP-OCRv6-Modellen, keine Adminrechte, kein Download; Deutsch inkl. Umlaute/ß getestet).

Aufgaben:
1. erkenne_seite(): Seite rendern (200 dpi), Ausrichtung bestimmen (0°/90°/270° – gedrehte Scans sind häufig),
   Text und Wortboxen erkennen, Lesereihenfolge herstellen. Der Text ist so aufgebaut, dass er sich 1:1 auf die
   Wörter abbilden lässt (für die Schwärzung). Koordinaten beziehen sich auf die AUFRECHTE Ansicht.
2. richte_seite_auf(): eine gedrehte Scan-Seite im Dokument durch eine aufrechte Bildseite ersetzen, damit
   Sichtkopie, Platzhalter und Leseansicht zusammenpassen.
3. schwaerze_scanseiten(): Treffer auf Scan-Seiten per Pixel-Schwärzung entfernen (PyMuPDF-Redaction mit
   images=PIXELS), Platzhalter als Text darüber schreiben, danach Gegenprüfung durch erneutes OCR.
   Findet die Gegenprüfung noch ein Original, gibt es ValueError – die Sichtkopie wird dann verworfen.

Tempo: ca. 4–6 s je Seite auf einer Büro-CPU (bei Drehungsprüfung bis zu 3 OCR-Läufe); die Engine wird einmal
geladen und wiederverwendet.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

DPI = 200
_engine = None
# OCR-Ergebnisse je (Dokument-Hash, Seite) – Lesen und Schwärzen derselben Datei erkennen die Seite nur einmal
_CACHE: dict[tuple[str, int], "Seite"] = {}
_CACHE_MAX = 400


@dataclass
class Wort:
    text: str
    rect: tuple[float, float, float, float]  # x0, y0, x1, y1 in PDF-Punkten (aufrechte Ansicht)
    zeile: int = 0


@dataclass
class Seite:
    nr: int
    text: str = ""
    woerter: list[Wort] = field(default_factory=list)
    zeilen: int = 0
    rotation: int = 0          # Grad, um die das Bild im Uhrzeigersinn gedreht werden muss, damit es aufrecht ist
    score: float = 0.0         # mittlere OCR-Sicherheit
    breite: float = 0.0        # Seitenmaße der aufrechten Ansicht in Punkten
    hoehe: float = 0.0


def engine():
    """RapidOCR einmal laden (Modelle liegen im Paket)."""
    global _engine
    if _engine is None:
        import logging

        logging.getLogger("RapidOCR").setLevel(logging.WARNING)
        from rapidocr import RapidOCR

        _engine = RapidOCR()
    return _engine


def ist_scan(page) -> bool:
    """Seite ohne nennenswerte Textebene, aber mit Bild = Scan."""
    return len(page.get_text().strip()) < 20 and bool(page.get_images(full=False))


def _render(page, dpi: int = DPI, rotation: int = 0):
    """Seite als RGB-Array; rotation (0/90/180/270, im Uhrzeigersinn) dreht das Bild vor der Erkennung."""
    import numpy as np
    import pymupdf

    mat = pymupdf.Matrix(dpi / 72, dpi / 72).prerotate(rotation)
    pix = page.get_pixmap(matrix=mat, annots=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    elif pix.n == 1:
        img = np.repeat(img, 3, axis=2)
    return np.ascontiguousarray(img), 72.0 / dpi, pix


def _rect(points, scale) -> tuple[float, float, float, float]:
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return (min(xs) * scale, min(ys) * scale, max(xs) * scale, max(ys) * scale)


def _ocr_roh(img):
    return engine()(img, return_word_box=True)


def _ist_gedreht(res) -> bool:
    """Hinweis auf einen quer liegenden Scan: die meisten Zeilenboxen sind höher als breit."""
    if not res.txts or len(res.txts) < 3:
        return False
    hoch = 0
    for box in res.boxes:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        if (max(ys) - min(ys)) > 1.3 * (max(xs) - min(xs)):
            hoch += 1
    return hoch >= 0.5 * len(res.txts)


def _guete(res) -> float:
    """Vergleichsmaß für Ausrichtungen: mittlere Sicherheit × Anzahl erkannter Wörter."""
    if not res.txts:
        return 0.0
    import numpy as np

    woerter = sum(len(t.split()) for t in res.txts)
    return float(np.mean(res.scores)) * woerter


def ausrichtung(page, dpi: int = DPI) -> tuple[int, object]:
    """Bestimmt, um wie viel Grad (im Uhrzeigersinn) die Seite gedreht werden muss, damit der Text aufrecht steht.
    Rückgabe: (rotation, OCR-Ergebnis der aufrechten Ansicht)."""
    img, _, _ = _render(page, dpi, 0)
    res0 = _ocr_roh(img)
    if not _ist_gedreht(res0):
        return 0, res0
    # Senkrechte Zeilen = Seite liegt quer. Die Zeilenklassifikation von RapidOCR liest auch senkrechte Zeilen
    # mit hoher Sicherheit, deshalb entscheidet nur der Vergleich 90° gegen 270°.
    best = None
    for rot in (90, 270):
        img_r, _, _ = _render(page, dpi, rot)
        res_r = _ocr_roh(img_r)
        g = _guete(res_r)
        if best is None or g > best[2]:
            best = (rot, res_r, g)
    return best[0], best[1]


def _seite_aus_ergebnis(nr: int, res, scale: float, rotation: int, breite: float, hoehe: float) -> Seite:
    import numpy as np

    if not res.txts:
        return Seite(nr, rotation=rotation, breite=breite, hoehe=hoehe)
    frags = []
    for i, (box, txt) in enumerate(zip(res.boxes, res.txts)):
        x0, y0, x1, y1 = _rect(box, scale)
        words: list[Wort] = []
        wr = res.word_results[i] if res.word_results is not None and i < len(res.word_results) else None
        if wr:
            for w in wr:
                if w[0] and str(w[0]).strip():
                    words.append(Wort(str(w[0]).strip(), _rect(w[2], scale)))
        if not words:
            words.append(Wort(txt.strip(), (x0, y0, x1, y1)))
        frags.append(((y0 + y1) / 2, x0, y1 - y0, words))
    frags.sort(key=lambda f: (f[0], f[1]))
    rows: list[list] = []
    for f in frags:
        if rows and abs(rows[-1][0][0] - f[0]) < 0.5 * max(f[2], rows[-1][0][2]):
            rows[-1].append(f)
        else:
            rows.append([f])
    lines, woerter = [], []
    for zi, row in enumerate(rows):
        row.sort(key=lambda f: f[1])
        zeile = []
        for f in row:
            for w in f[3]:
                w.zeile = zi
                zeile.append(w)
        lines.append(" ".join(w.text for w in zeile))
        woerter.extend(zeile)
    return Seite(nr, "\n".join(lines), woerter, len(rows), rotation, float(np.mean(res.scores)), breite, hoehe)


def erkenne_seite(page, dpi: int = DPI, rotation: int | None = None, key: str | None = None) -> Seite:
    """OCR einer Seite in aufrechter Ausrichtung. rotation=None: Ausrichtung automatisch bestimmen.
    key: Dokument-Hash für den Zwischenspeicher (nur bei automatischer Ausrichtung)."""
    if rotation is None and key is not None and (key, page.number) in _CACHE:
        return _CACHE[(key, page.number)]
    if rotation is None:
        rotation, res = ausrichtung(page, dpi)
    else:
        img, _, _ = _render(page, dpi, rotation)
        res = _ocr_roh(img)
    scale = 72.0 / dpi
    w, h = page.rect.width, page.rect.height
    if rotation in (90, 270):
        w, h = h, w
    seite = _seite_aus_ergebnis(page.number, res, scale, rotation, w, h)
    if key is not None and rotation is not None and len(_CACHE) < _CACHE_MAX:
        _CACHE[(key, page.number)] = seite
    return seite


def ocr_text(doc, key: str | None = None) -> tuple[list[str], int]:
    """Text aller Seiten; Scan-Seiten per OCR (mit Ausrichtung). Rückgabe: (Seitentexte, Anzahl OCR-Seiten)."""
    texte, n = [], 0
    for page in doc:
        if ist_scan(page):
            texte.append(erkenne_seite(page, key=key).text)
            n += 1
        else:
            texte.append(page.get_text())
    return texte, n


# ---------------------------------------------------------------------------
# Aufrichten und Schwärzung auf Scan-Seiten
# ---------------------------------------------------------------------------

def richte_seite_auf(doc, pno: int, rotation: int, dpi: int = DPI):
    """Ersetzt die Seite pno durch eine aufrechte Bildseite (Scan um `rotation` Grad gedreht gerendert).
    Gibt die neue Seite zurück. Die alte Seite verschwindet; Metadaten/Anhänge bleiben beim Dokument."""
    import pymupdf

    old = doc[pno]
    _, _, pix = _render(old, dpi, rotation)
    w, h = old.rect.width, old.rect.height
    if rotation in (90, 270):
        w, h = h, w
    new = doc.new_page(pno=pno + 1, width=w, height=h)
    new.insert_image(new.rect, pixmap=pix)
    doc.delete_page(pno)
    return doc[pno]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _needle(orig: str) -> re.Pattern:
    parts = [re.escape(p) for p in orig.split()]
    return re.compile(r"(?<!\w)" + r"\s+".join(parts) + r"(?!\w)", re.IGNORECASE)


def finde_treffer(seite: Seite, pairs: list[tuple[str, str]]) -> list[tuple[str, tuple[float, float, float, float]]]:
    """Originale im OCR-Text suchen und auf Wortboxen abbilden. Rückgabe: (Platzhalter, Rechteck) je Zeile.
    Längste Originale zuerst; bereits belegte Wörter werden nicht doppelt verwendet."""
    if not seite.woerter:
        return []
    spans, pos = [], 0
    for i, w in enumerate(seite.woerter):
        if i > 0:
            pos += 1  # Leerzeichen bzw. Zeilenumbruch
        spans.append((pos, pos + len(w.text), i))
        pos += len(w.text)
    belegt: set[int] = set()
    out = []
    for orig, ph in sorted(pairs, key=lambda t: -len(t[0])):
        if not orig or len(orig.strip()) < 3:
            continue
        for m in _needle(orig).finditer(seite.text):
            idx = [i for s, e, i in spans if s < m.end() and e > m.start()]
            if not idx or any(i in belegt for i in idx):
                continue
            belegt.update(idx)
            by_line: dict[int, list[Wort]] = {}
            for i in idx:
                by_line.setdefault(seite.woerter[i].zeile, []).append(seite.woerter[i])
            for ws in by_line.values():
                out.append((ph, (min(w.rect[0] for w in ws), min(w.rect[1] for w in ws),
                                 max(w.rect[2] for w in ws), max(w.rect[3] for w in ws))))
    return out


def _platzhalter_einsetzen(page, rect, ph: str) -> bool:
    """Platzhalter als Text über die geschwärzte Fläche schreiben. Schrift wird verkleinert, bis er in die
    Breite passt; die Box ist mindestens so hoch wie eine Textzeile dieser Schriftgröße."""
    import pymupdf

    r = pymupdf.Rect(*rect)
    fs = max(5.0, min(r.height * 0.8, 11.0))
    while fs > 5.0 and pymupdf.get_text_length(ph, fontname="helv", fontsize=fs) > max(r.width, 20):
        fs -= 0.5
    for _ in range(4):
        breite = max(r.width, pymupdf.get_text_length(ph, fontname="helv", fontsize=fs)) + 4
        hoehe = max(r.height, fs * 1.4) + 2
        box = pymupdf.Rect(r.x0 - 1, r.y0 - 1, r.x0 + breite, r.y0 - 1 + hoehe)
        rc = page.insert_textbox(box, ph, fontname="helv", fontsize=fs, color=(0, 0, 0), align=0)
        if rc >= 0:
            return True
        fs = max(4.0, fs - 1.0)
    return False


def schwaerze_scanseiten(doc, pairs: list[tuple[str, str]], dpi: int = DPI, key: str | None = None) -> dict[int, int]:
    """Scan-Seiten: Ausrichtung prüfen (gedrehte Seiten werden aufgerichtet), OCR, Treffer per Pixel-Schwärzung
    entfernen, Platzhalter einsetzen, Gegenprüfung per OCR. Rückgabe: {Seitennummer: Anzahl geschwärzter Stellen}.
    ValueError, wenn ein Original nach der Schwärzung noch erkannt wird.
    key: Dokument-Hash; mit ihm wird das OCR-Ergebnis aus dem Lesen wiederverwendet."""
    import pymupdf

    ergebnis: dict[int, int] = {}
    originals = [o for o, _ in pairs if o and len(o.strip()) >= 3]
    pno = 0
    while pno < len(doc):
        page = doc[pno]
        if not ist_scan(page):
            pno += 1
            continue
        seite = erkenne_seite(page, dpi, key=key)
        if seite.rotation:
            # Aufgerichtete Seite = Render mit derselben Drehung -> Wortboxen aus `seite` gelten unverändert
            page = richte_seite_auf(doc, pno, seite.rotation, dpi)
        hits = finde_treffer(seite, pairs)
        if hits:
            pad = 2.0
            for _ph, (x0, y0, x1, y1) in hits:
                page.add_redact_annot(pymupdf.Rect(x0 - pad, y0 - pad, x1 + pad, y1 + pad), fill=(1, 1, 1))
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS,
                                  graphics=pymupdf.PDF_REDACT_LINE_ART_NONE, text=pymupdf.PDF_REDACT_TEXT_REMOVE)
            while page.first_annot:
                page.delete_annot(page.first_annot)
            fehlend = [ph for ph, rect in hits if not _platzhalter_einsetzen(page, rect, ph)]
            if fehlend:
                raise ValueError(f"Scan-Seite {pno + 1}: Platzhalter nicht einsetzbar: {sorted(set(fehlend))}")
            ergebnis[pno] = len(hits)
            # Gegenprüfung: erneut lesen, kein Original darf übrig sein
            kontrolle = _norm(erkenne_seite(page, dpi, rotation=0).text)
            rest = [o for o in originals if _needle(o).search(kontrolle)]
            if rest:
                raise ValueError(f"Scan-Seite {pno + 1}: nach der Schwärzung noch lesbar: {rest}")
        pno += 1
    return ergebnis
