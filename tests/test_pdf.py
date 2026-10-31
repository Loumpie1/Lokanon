"""Tests für write_pdf / verify_pdf. Läuft mit pytest oder direkt als Skript:

    C:\\Users\\david\\Lokanon\\venv\\Scripts\\python.exe tests\\test_pdf.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "testdaten" / "pdf"))

import pymupdf  # noqa: E402

from anonymizer.files import _pdf_placeholder_stufen, _pdf_short_placeholder, verify_pdf, write_pdf  # noqa: E402

FALL4 = ROOT / "testdaten" / "kanzlei" / "Fall4_Verkehrsrecht_Einspruch_Bussgeld_Engel.pdf"
REF = ROOT / "testdaten" / "kanzlei" / "referenz_markierungen.jsonl"
OUT = ROOT / "testdaten" / "pdf"


def _fall4_pairs() -> list[tuple[str, str]]:
    for line in REF.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["datei"] == FALL4.name:
            break
    else:
        raise AssertionError("Fall4 nicht in der Referenzdatei")
    counters: dict[str, int] = {}
    mapping: dict[str, str] = {}
    pairs = []
    for s, e, label in rec["spans"]:
        orig = rec["text"][s:e]
        if orig not in mapping:
            counters[label] = counters.get(label, 0) + 1
            mapping[orig] = f"[{label}_{counters[label]}]"
        pairs.append((orig, mapping[orig]))
    return sorted(set(pairs), key=lambda t: -len(t[0]))


def _full_text(data: bytes) -> str:
    with pymupdf.open(stream=data, filetype="pdf") as d:
        return "\n".join(p.get_text() for p in d)


def test_verify_detects_originals_in_source():
    data = FALL4.read_bytes()
    pairs = _fall4_pairs()
    found = verify_pdf(data, [o for o, _ in pairs])
    assert "Dr. Claudia Engel" in found
    assert "Dr. Annette Lehmkuhl" in verify_pdf(data, ["Dr. Annette Lehmkuhl"])  # Metadaten
    assert verify_pdf(data, ["gibt es nicht 12345"]) == []


def test_fall4_redacted():
    data = FALL4.read_bytes()
    pairs = _fall4_pairs()
    pairs.append(("Dr. Annette Lehmkuhl", "[Person_9]"))
    out = write_pdf(data, pairs)
    (OUT / "Fall4_geschwaerzt.pdf").write_bytes(out)
    assert verify_pdf(out, [o for o, _ in pairs]) == []
    text = _full_text(out)
    flat = text.replace("\n", "").replace(" ", "")
    for _orig, ph in pairs:
        assert any(stufe in flat for stufe in _pdf_placeholder_stufen(ph)), f"{ph} fehlt im Ergebnis"
# "Engel" allein ist zu schmal für [PERSON_2] bei 5 pt -> lesbare Kurzform
    assert "[PERSON_2]" not in flat and re.search(r"(?i)\[P(ers[a-z]*_)?2\]", flat)
    # Unbeteiligter Text bleibt stehen
    assert "Einspruch" in text and "Dortmund" in text
    with pymupdf.open(stream=out, filetype="pdf") as d:
        meta = {k: v for k, v in d.metadata.items() if v and k != "format" and k != "encryption"}
        assert meta == {}, meta
        assert d.get_toc() == []
        assert d.embfile_count() == 0
        assert not d.get_xml_metadata()
        assert d.page_count == 1
        # Ergebnis ist weiterhin eine Textseite (nicht gerastert)
        assert d[0].get_text().strip()


def test_xobject_pdf():
    from make_xobject_pdf import build

    src = build()
    data = src.read_bytes()
    pairs = [
        ("Dr. Claudia Engel", "[Person_1]"),
        ("Markus Engel", "[Person_2]"),
        ("Dr. Annette Lehmkuhl", "[Person_3]"),
        ("Engel", "[Person_1]"),
        ("Moltkestraße 15", "[Adresse_1]"),
        ("45138 Essen", "[PLZ_ORT_1]"),
        ("E-CE 511", "[Kennzeichen_1]"),
        ("7.1-552318/26", "[AKTENZEICHEN_1]"),
        ("Chefärztin der Kinderklinik am Elisabeth-Krankenhaus", "[INDIREKT_1]"),
    ]
    originals = [o for o, _ in pairs]
    assert set(verify_pdf(data, originals)) == set(originals)  # alles drin vor der Schwärzung
    out = write_pdf(data, pairs)
    (OUT / "xobject_test_geschwaerzt.pdf").write_bytes(out)
    assert verify_pdf(out, originals) == []
    text = _full_text(out)
    flat = text.replace("\n", "").replace(" ", "")
    assert flat.count("[Person_1]") >= 3  # Seite 1, XObject auf Seite 2, direkte Zeile
    assert flat.count("[Person_2]") >= 2
    assert "[INDIREKT_1]" in flat
    assert re.search(r"\[Kenn[a-z]*_1\]", flat)  # Kennzeichen umbricht im Original: gekürzt, aber lesbar
    assert "Direkt:" in text and "Mandantin" in text
    assert verify_pdf(out, ["Versteckt", "Notiz", "anhang"]) == []  # versteckter Text, Annot, Anhang weg
    with pymupdf.open(stream=out, filetype="pdf") as d:
        assert d.page_count == 2
        assert d.get_toc() == []
        assert d.embfile_count() == 0
        assert not d.get_xml_metadata()
        assert all(not v for k, v in d.metadata.items() if k not in ("format", "encryption"))
        for p in d:
            assert p.first_annot is None
            assert p.first_widget is None
            assert p.get_links() == []


def test_long_placeholder_in_narrow_rect():
    """Platzhalter, der nie in das Rechteck passt: wird gekürzt, verschwindet aber nicht."""
    doc = pymupdf.open()
    p = doc.new_page()
    # Originale unter 3 Zeichen werden bewusst ignoriert (Leck-Test-Fehlalarme wie "Bl" = Blatt), daher "Fab"
    p.insert_text((50, 100), "Fab 12345", fontname="helv", fontsize=6)
    data = doc.tobytes()
    out = write_pdf(data, [("Fab", "[ORGANISATION_17]")])
    flat = _full_text(out).replace("\n", "").replace(" ", "")
    assert "[O17]" in flat or "[ORGANISATION_17]" in flat
    assert "12345" in flat


def test_multiline_hit():
    """Original über einen Zeilenumbruch hinweg: ein Platzhalter, beide Teile entfernt."""
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_textbox(pymupdf.Rect(50, 50, 180, 200),
                     "Unsere Mandantin Dr. Claudia Engel erhebt Einspruch.",
                     fontname="helv", fontsize=11)
    data = doc.tobytes()
    assert "Claudia\nEngel" in _full_text(data) or "Dr.\nClaudia" in _full_text(data)
    out = write_pdf(data, [("Dr. Claudia Engel", "[Person_1]")])
    flat = _full_text(out).replace("\n", "").replace(" ", "")
    assert flat.count("[Person_1]") == 1
    assert "Einspruch" in flat


def _positions(data: bytes, pno: int = 0):
    """(Zeichen, x0, y0) aller Zeichen einer Seite, gerundet."""
    from anonymizer.files import _pdf_page_chars

    with pymupdf.open(stream=data, filetype="pdf") as d:
        return [(c, round(b.x0, 1), round(b.y0, 1)) for c, b, _fs, _l in _pdf_page_chars(d[pno])[0] if b]


def _assert_rest_unmoved(before: bytes, after: bytes, removed: str):
    """Alle nicht entfernten Zeichen stehen nach der Schwärzung an derselben Stelle."""
    kept = [p for p in _positions(before) if p[0] not in removed]
    after_pos = set(_positions(after))
    moved = [p for p in kept if p not in after_pos]
    assert not moved, f"verschobene Zeichen: {moved[:5]}"


def test_tj_kerning_keeps_positions():
    """MuPDF-Workaround: Text in TJ-Arrays (Word/LibreOffice-typisch) darf nach der
    Schwärzung nicht verrutschen."""
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_font(fontname="helv")
    p.insert_text((50, 100), "x", fontname="helv")
    doc.update_stream(p.get_contents()[0],
                      b"BT /helv 11 Tf 50 742 Td [(Mandantin Dr. Cl) -30 (audia Engel wohnt) 15 ( in Essen)] TJ "
                      b"0 -14 Td [<4672617520456e67656c20626573747265697465742e>] TJ ET")
    data = doc.tobytes()
    out = write_pdf(data, [("Dr. Claudia Engel", "[Person_1]"), ("Engel", "[Person_1]")])
    assert verify_pdf(out, ["Dr. Claudia Engel", "Engel"]) == []
    flat = _full_text(out).replace("\n", "").replace(" ", "")
    assert len(re.findall(r"\[P(ers[a-z]*_)?1\]", flat)) == 2
    _assert_rest_unmoved(data, out, "Dr. ClaudiaEngel")


def test_type0_font_keeps_positions():
    """Type0/Identity-H (eingebettete Schrift, 2-Byte-Codes)."""
    doc = pymupdf.open()
    p = doc.new_page()
    tw = pymupdf.TextWriter(p.rect)
    tw.append((50, 100), "Mandantin Dr. Claudia Engel wohnt in Essen", font=pymupdf.Font("helv"), fontsize=11)
    tw.write_text(p)
    data = doc.tobytes()
    with pymupdf.open(stream=data, filetype="pdf") as d:
        assert d[0].get_fonts()[0][2] == "Type0"
    out = write_pdf(data, [("Dr. Claudia Engel", "[Person_1]")])
    assert verify_pdf(out, ["Dr. Claudia Engel"]) == []
    _assert_rest_unmoved(data, out, "Dr. ClaudiaEngel")


def test_word_boundaries():
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 100), "Engelmann traf Engel in Essen-Frohnhausen bei Essen.", fontname="helv", fontsize=11)
    data = doc.tobytes()
    out = write_pdf(data, [("Engel", "[Person_1]"), ("Essen", "[Ort_1]")])
    text = _full_text(out)
    # gleiche Semantik wie _replace_all: "Engelmann" bleibt, "Essen-Frohnhausen" wird zu "[Ort_1]-Frohnhausen"
    assert "Engelmann" in text and "-Frohnhausen" in text and "Essen" not in text
    assert verify_pdf(out, ["Engel", "Essen"]) == []
    assert verify_pdf(data, ["Engel", "Essen"]) == ["Engel", "Essen"]
    flat = text.replace("\n", "").replace(" ", "")
    assert len(re.findall(r"\[P(ers[a-z]*_)?1\]", flat)) == 1 and flat.count("[Ort_1]") == 2
    with pymupdf.open(stream=out, filetype="pdf") as d:
        assert d[0].get_images() == []  # nicht gerastert


def test_placeholder_font_on_xobject_page():
    """Seite ohne eigene Schriftressourcen: Platzhalter muss trotzdem in Helvetica stehen."""
    from make_xobject_pdf import build

    out = write_pdf(build().read_bytes(), [("Dr. Claudia Engel", "[Person_1]")])
    with pymupdf.open(stream=out, filetype="pdf") as d:
        fonts = {s["font"] for b in d[1].get_text("dict")["blocks"] for l in b.get("lines", [])
                 for s in l["spans"] if s["text"].startswith("[Person")}
    assert fonts == {"Helvetica"}, fonts


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            import traceback

            traceback.print_exc()
            print(f"FAIL {t.__name__}: {exc}")
    print(f"{len(tests) - failed}/{len(tests)} Tests bestanden")
    sys.exit(1 if failed else 0)
