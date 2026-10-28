r"""Vorgang = eine Akte, ein Mandat, ein Patient.

Ein Vorgang bündelt:
- die Eingabedateien,
- EINEN Schlüssel (Platzhalter -> Original), der über alle Dateien des Vorgangs gilt
  (gleiche Person = gleicher Platzhalter innerhalb des Vorgangs, zwischen Vorgängen beginnt die Zählung neu),
- einen Vorgangsordner mit verständlicher Struktur:

    <Vorgangsordner>\
        Originale\          Kopien der hochgeladenen Dateien bzw. text.txt (nur bei Upload/Text; bei
                            "Ordner angeben" liegen die Originale schon im Aktenordner)
        Anonymisiert\       anonymisierte Kopien unter Originalnamen (für die eigene Ablage)
        Fuer die KI\        dieselben Dateien mit bereinigten Dateinamen – diese werden hochgeladen
        Pruefbericht.html   Original mit farbigen Markierungen und Platzhaltern (enthält Klartext!)
        Uebersicht.csv      Original <-> KI-Datei <-> Anzahl Platzhalter
        Protokoll.md/.json  was wann womit maskiert wurde – ohne Klartext

  Bei "Ordner angeben" ist der Vorgangsordner <Akte>\Lokanon\, bei Upload/Text <Vorgaenge-Ordner>\<Vorgangsname>\.
- die verschlüsselte Schlüsseldatei außerhalb von Cloud-Ordnern (`schluessel_ordner`).

Originale werden nie verändert.
"""
from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .engine import LABELS, Finding
from .vault import encrypt_mapping

CLOUD_MARKER = ("onedrive", "dropbox", "google drive", "googledrive", "icloud", "nextcloud", "box sync")
LESBARE_TYPEN = ("txt", "md", "docx", "pdf", "xlsx", "csv")
UNTERORDNER = "Lokanon"            # Vorgangsordner innerhalb eines Aktenordners
ORIGINALE, ANONYMISIERT, FUER_KI = "Originale", "Anonymisiert", "Fuer die KI"


def ist_cloud_pfad(p: str | Path) -> bool:
    s = str(p).lower()
    return any(m in s for m in CLOUD_MARKER)


def _home() -> Path:
    return Path(os.environ.get("USERPROFILE", Path.home()))


def standard_schluessel_ordner() -> Path:
    return _home() / "Lokanon" / "schluessel"


def standard_vorgaenge_ordner() -> Path:
    return _home() / "Lokanon" / "Vorgaenge"


def dateien_im_ordner(ordner: str | Path) -> list[Path]:
    """Unterstützte Dateien im Ordner (nicht rekursiv, ohne Ausgabeordner und temporäre Office-Dateien)."""
    p = Path(ordner)
    if not p.is_dir():
        raise ValueError(f"Ordner nicht gefunden: {p}")
    out = []
    for f in sorted(p.iterdir()):
        if f.is_file() and f.suffix.lower().lstrip(".") in LESBARE_TYPEN and not f.name.startswith("~$"):
            out.append(f)
    return out


@dataclass
class DateiEintrag:
    original: str                      # Dateiname im Eingabeordner
    ausgaben: list[str] = field(default_factory=list)   # erzeugte Dateien (relativ zum Vorgangsordner)
    ki_name: str = ""                  # Basisname der KI-Version (ohne Endung)
    treffer: dict[str, int] = field(default_factory=dict)  # Label -> Anzahl maskierter Stellen
    zeichen: int = 0
    geprueft: bool = False             # Nutzer hat die Treffer bestätigt
    zeit: str = ""


@dataclass
class Vorgang:
    name: str
    ordner: str = ""                   # Eingabeordner (Akte) bei "Ordner angeben", sonst ""
    basis: str = ""                    # Vorgangsordner (siehe Modul-Doku); leer = noch nicht festgelegt
    profil: str = "kanzlei"
    mapping: dict[str, str] = field(default_factory=dict)   # Platzhalter -> Original (der Schlüssel)
    bezeichnungen: dict[str, str] = field(default_factory=dict)  # Platzhalter -> eigene Bezeichnung ("Mandant")
    dateien: list[DateiEintrag] = field(default_factory=list)
    anbieter: str = ""
    erstellt: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    abgeschlossen: str = ""            # Zeitpunkt des Abschlusses
    hinweise: list[str] = field(default_factory=list)

    # ----- Pfade -----
    def lege_basis_fest(self, vorgaenge_ordner: str | Path | None = None) -> Path:
        """Vorgangsordner bestimmen: <Akte>\\Lokanon bei Ordner-Eingabe, sonst <Vorgaenge>\\<Name>."""
        if self.ordner:
            self.basis = str(Path(self.ordner) / UNTERORDNER)
        else:
            root = Path(vorgaenge_ordner) if vorgaenge_ordner else standard_vorgaenge_ordner()
            self.basis = str(root / sicherer_name(self.name))
        return Path(self.basis)

    @property
    def basis_pfad(self) -> Path:
        if not self.basis:
            self.lege_basis_fest()
        return Path(self.basis)

    @property
    def originale(self) -> Path:
        return self.basis_pfad / ORIGINALE

    @property
    def ausgabe(self) -> Path:
        return self.basis_pfad / ANONYMISIERT

    @property
    def ki_ordner(self) -> Path:
        return self.basis_pfad / FUER_KI

    def eintrag(self, original: str) -> DateiEintrag:
        for d in self.dateien:
            if d.original == original:
                return d
        d = DateiEintrag(original=original)
        self.dateien.append(d)
        return d

    # ----- Schreiben -----
    def sichere_original(self, name: str, inhalt: bytes) -> Path:
        """Hochgeladene Datei / eingefügten Text unverändert im Vorgangsordner ablegen."""
        self.originale.mkdir(parents=True, exist_ok=True)
        p = self.originale / Path(name).name
        p.write_bytes(inhalt)
        return p

    def leere_ausgabe(self) -> None:
        """Alte Ausgaben dieses Vorgangs entfernen (Dateien in Anonymisiert\\ und Fuer die KI\\; Originale bleiben)."""
        for d in (self.ki_ordner, self.ausgabe):
            if d.is_dir():
                for p in d.iterdir():
                    if p.is_file():
                        p.unlink()

    def schreibe(self, original: str, inhalt: bytes, endung: str, ki_name: str) -> tuple[Path, Path]:
        """Legt eine Ausgabedatei unter Originalnamen und eine KI-Kopie mit bereinigtem Namen an.
        endung z. B. "md", "pdf", "docx". Gibt (Pfad Original-Kopie, Pfad KI-Kopie) zurück."""
        self.ausgabe.mkdir(parents=True, exist_ok=True)
        self.ki_ordner.mkdir(parents=True, exist_ok=True)
        stamm = Path(original).stem
        lokal = self.ausgabe / f"{stamm}.{endung}"
        ki = self.ki_ordner / f"{ki_name}.{endung}"
        lokal.write_bytes(inhalt)
        ki.write_bytes(inhalt)
        e = self.eintrag(original)
        e.ki_name = ki_name
        for p in (lokal, ki):
            rel = str(p.relative_to(self.basis_pfad)).replace("\\", "/")
            if rel not in e.ausgaben:
                e.ausgaben.append(rel)
        e.zeit = datetime.now().isoformat(timespec="seconds")
        return lokal, ki

    def schreibe_pruefbericht(self, html: str) -> Path:
        self.basis_pfad.mkdir(parents=True, exist_ok=True)
        p = self.basis_pfad / "Pruefbericht.html"
        p.write_text(html, encoding="utf-8")
        return p

    def notiere_treffer(self, original: str, findings: list[Finding], zeichen: int, geprueft: bool) -> None:
        e = self.eintrag(original)
        e.treffer = {}
        for f in findings:
            if f.active:
                lab = LABELS.get(f.entity, f.entity)
                e.treffer[lab] = e.treffer.get(lab, 0) + 1
        e.zeichen = zeichen
        e.geprueft = geprueft

    # ----- Übersicht und Protokoll -----
    def schreibe_uebersicht(self) -> Path:
        self.basis_pfad.mkdir(parents=True, exist_ok=True)
        p = self.basis_pfad / "Uebersicht.csv"
        with open(p, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["Originaldatei", "Anonymisierte Kopie (eigene Ablage)", "Datei für die KI", "Maskierte Stellen", "Geprüft"])
            for d in self.dateien:
                lokal = ", ".join(a for a in d.ausgaben if a.startswith(ANONYMISIERT + "/"))
                ki = ", ".join(a for a in d.ausgaben if a.startswith(FUER_KI + "/"))
                w.writerow([d.original, lokal, ki, sum(d.treffer.values()), "ja" if d.geprueft else "nein"])
        return p

    def protokoll_dict(self) -> dict:
        return {
            "vorgang": self.name,
            "profil": self.profil,
            "erstellt": self.erstellt,
            "abgeschlossen": self.abgeschlossen,
            "anbieter": self.anbieter,
            "eingabeordner": self.ordner,
            "vorgangsordner": self.basis,
            "platzhalter_gesamt": len(self.mapping),
            "platzhalter_je_typ": _zaehle_labels(self.mapping),
            "eigene_bezeichnungen": {k: v for k, v in self.bezeichnungen.items()},
            "dateien": [
                {"original": d.original, "ausgaben": d.ausgaben, "treffer": d.treffer, "zeichen": d.zeichen,
                 "geprueft": d.geprueft, "zeit": d.zeit}
                for d in self.dateien
            ],
            "hinweise": self.hinweise,
        }

    def protokoll_markdown(self) -> str:
        d = self.protokoll_dict()
        zeilen = [
            f"# Protokoll Vorgang „{self.name}“",
            "",
            f"- Profil: {self.profil}",
            f"- Angelegt: {self.erstellt}",
            f"- Abgeschlossen: {self.abgeschlossen or '– (offen)'}",
            f"- Ziel-KI: {self.anbieter or '– (nicht angegeben)'}",
            f"- Eingabeordner: {self.ordner or '– (Upload/Text, Originale unter Originale\\)'}",
            f"- Vorgangsordner: {self.basis}",
            f"- Platzhalter insgesamt: {len(self.mapping)}",
            "",
            "## Platzhalter je Typ",
            "",
        ]
        for lab, n in sorted(d["platzhalter_je_typ"].items()):
            zeilen.append(f"- {lab}: {n}")
        zeilen += ["", "## Dateien", "", "| Datei | Zeichen | Maskiert | Geprüft | Ausgaben |", "|---|---|---|---|---|"]
        for e in self.dateien:
            treff = ", ".join(f"{k} {v}" for k, v in sorted(e.treffer.items())) or "–"
            zeilen.append(f"| {e.original} | {e.zeichen:,} | {treff} | {'ja' if e.geprueft else 'nein'} | "
                          f"{', '.join(e.ausgaben) or '–'} |")
        if self.hinweise:
            zeilen += ["", "## Hinweise", ""] + [f"- {h}" for h in self.hinweise]
        zeilen += ["", "_Dieses Protokoll enthält keine Originaldaten. Der Schlüssel liegt getrennt und verschlüsselt._"]
        return "\n".join(zeilen) + "\n"

    def schreibe_protokoll(self) -> tuple[Path, Path]:
        self.basis_pfad.mkdir(parents=True, exist_ok=True)
        pj = self.basis_pfad / "Protokoll.json"
        pm = self.basis_pfad / "Protokoll.md"
        pj.write_text(json.dumps(self.protokoll_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        pm.write_text(self.protokoll_markdown(), encoding="utf-8")
        return pj, pm

    # ----- Schlüssel -----
    def schluessel_bytes(self, passwort: str) -> bytes:
        return encrypt_mapping({"vorgang": self.name, "erstellt": self.erstellt, "mapping": self.mapping,
                                "bezeichnungen": self.bezeichnungen}, passwort)

    def speichere_schluessel(self, passwort: str, ordner: str | Path | None = None) -> Path:
        ziel = Path(ordner) if ordner else standard_schluessel_ordner()
        ziel.mkdir(parents=True, exist_ok=True)
        p = ziel / f"{sicherer_name(self.name)}.anon.json"
        p.write_bytes(self.schluessel_bytes(passwort))
        return p

    def abschliessen(self) -> None:
        self.abgeschlossen = datetime.now().isoformat(timespec="seconds")


def mapping_aus_schluessel(obj: dict) -> dict[str, str]:
    """Schlüsseldateien alter Form (nur mapping) und neuer Form ({vorgang, mapping}) lesen."""
    return obj.get("mapping", obj) if isinstance(obj, dict) and "mapping" in obj else obj


def _zaehle_labels(mapping: dict[str, str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for ph in mapping:
        lab = ph.rsplit("_", 1)[0]
        out[lab] = out.get(lab, 0) + 1
    return out


def sicherer_name(s: str) -> str:
    s = re.sub(r"[^\w\-. ]+", "_", s.strip())
    return s[:80] or "vorgang"


def ki_dateiname(original: str, pairs: list[tuple[str, str]]) -> str:
    """Dateiname für die KI: erkannte Begriffe im Namen durch Platzhalter ersetzen.
    "Fall1_Erbrecht_Brinkhoff.docx" + [("Brinkhoff", "[PERSON_2]")] -> "Fall1_Erbrecht_PERSON_2".
    Eckige Klammern lassen wir im Dateinamen weg (Upload-Masken mögen sie nicht)."""
    stamm = Path(original).stem
    neu = stamm
    labels = {v for v in LABELS.values()}
    for orig, ph in pairs:  # pairs sind längste zuerst
        if len(orig) < 3 or orig.upper() in labels:  # "Person" als Treffer darf PERSON_2 nicht zerlegen
            continue
        # Wortgrenze ohne "_" (in Dateinamen trennt der Unterstrich Wörter)
        neu = re.sub(rf"(?<![A-Za-zÄÖÜäöüß0-9]){re.escape(orig)}(?![A-Za-zÄÖÜäöüß0-9])", ph.strip("[]"), neu,
                     flags=re.IGNORECASE)
        # auch Schreibweisen ohne Leerzeichen/mit Unterstrich ("HansMueller", "Hans_Mueller")
        for variante in (orig.replace(" ", ""), orig.replace(" ", "_"), orig.replace(" ", "-")):
            if variante != orig and len(variante) >= 4:
                neu = re.sub(re.escape(variante), ph.strip("[]"), neu, flags=re.IGNORECASE)
    return sicherer_name(neu)


# ---------------------------------------------------------------------------
# Prüfbericht (HTML mit Klartext – bleibt lokal im Vorgangsordner)
# ---------------------------------------------------------------------------

FARBEN = {"PERSON": "#ffd6d6", "ORGANIZATION": "#d6e4ff", "LOCATION": "#d9f2e3", "PLZ_ORT": "#d9f2e3",
          "ADRESSE": "#d9f2e3", "EIGENE_BEGRIFFE": "#f3d9ff", "MANUELL": "#f3d9ff", "DATUM": "#ffe9c4"}


def markiert_html(text: str, findings: list[Finding], platzhalter: dict[tuple[int, int], str] | None = None) -> str:
    """Original mit farbigen Markierungen. Aktive Treffer zeigen den Platzhalter als kleines Etikett,
    abgewählte Treffer bekommen einen gestrichelten Rahmen („bleibt stehen“)."""
    import html as _h

    parts, pos = [], 0
    for f in sorted(findings, key=lambda f: f.start):
        if f.start < pos:
            continue
        parts.append(_h.escape(text[pos:f.start]))
        lab = LABELS.get(f.entity, f.entity)
        c = FARBEN.get(f.entity, "#fff3c4")
        ph = (platzhalter or {}).get((f.start, f.end), "")
        if f.active:
            parts.append(f'<mark style="background:{c};padding:0 3px;border-radius:3px" title="{lab}">'
                         f"{_h.escape(text[f.start:f.end])}"
                         f'<sup style="font-size:.7em;color:#1f5fa8;margin-left:2px">{_h.escape(ph or lab)}</sup></mark>')
        else:
            parts.append(f'<span style="border:1px dashed #94a3b8;padding:0 3px;border-radius:3px;color:#475569" '
                         f'title="bleibt stehen ({lab})">{_h.escape(text[f.start:f.end])}</span>')
        pos = f.end
    parts.append(_h.escape(text[pos:]))
    return "".join(parts)


def pruefbericht_html(vorgang: "Vorgang", docs: list[dict]) -> str:
    """Kompletter Prüfbericht: Legende, Begriffsliste (maskiert / bleibt stehen), je Datei das markierte Original.
    docs: [{"name", "text", "findings", "platzhalter": {(start,end): "[PERSON_1]"}}]"""
    import html as _h

    reverse = {v.lower(): k for k, v in vorgang.mapping.items()}
    maskiert: dict[str, tuple[str, str, int]] = {}
    bleibt: dict[str, tuple[str, int]] = {}
    for d in docs:
        for f in d["findings"]:
            lab = LABELS.get(f.entity, f.entity)
            if f.active:
                ph = d.get("platzhalter", {}).get((f.start, f.end)) or reverse.get(f.text.lower(), "")
                k = f.text.lower()
                maskiert[k] = (f.text, ph or lab, maskiert.get(k, ("", "", 0))[2] + 1)
            else:
                k = f.text.lower()
                bleibt[k] = (f.text, bleibt.get(k, ("", 0))[1] + 1)
    rows_m = "".join(f"<tr><td>{_h.escape(t)}</td><td><code>{_h.escape(ph)}</code></td><td>{n}</td></tr>"
                     for t, ph, n in sorted(maskiert.values(), key=lambda x: x[1]))
    rows_b = "".join(f"<tr><td>{_h.escape(t)}</td><td>{n}</td></tr>" for t, n in sorted(bleibt.values()))
    legende = " ".join(f'<span style="background:{c};padding:1px 6px;border-radius:3px">{k}</span>'
                       for k, c in (("Person", FARBEN["PERSON"]), ("Firma", FARBEN["ORGANIZATION"]),
                                    ("Adresse/Ort", FARBEN["ADRESSE"]), ("Datum", FARBEN["DATUM"]),
                                    ("Nummern u. a.", "#fff3c4"), ("eigene Begriffe", FARBEN["MANUELL"])))
    teile = []
    for d in docs:
        teile.append(f"<h2>{_h.escape(d['name'])}</h2><div class='doc'>"
                     f"{markiert_html(d['text'], d['findings'], d.get('platzhalter'))}</div>")
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Prüfbericht – {_h.escape(vorgang.name)}</title>
<style>body{{font-family:Segoe UI,system-ui,sans-serif;max-width:960px;margin:24px auto;padding:0 20px;color:#1e293b;line-height:1.5}}
h1{{font-size:1.6rem}} h2{{font-size:1.1rem;margin-top:28px;border-top:2px solid #1f5fa8;padding-top:8px}}
.doc{{white-space:pre-wrap;background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:14px;font-size:.95rem}}
table{{border-collapse:collapse;font-size:.9rem;margin:8px 0 18px}} th,td{{border:1px solid #e2e8f0;padding:4px 10px;text-align:left}} th{{background:#f1f5f9}}
.warn{{background:#fef3c7;border-left:4px solid #b45309;padding:8px 12px;border-radius:0 6px 6px 0}}
@media print{{.doc{{break-inside:avoid}}}}</style></head><body>
<h1>Prüfbericht – {_h.escape(vorgang.name)}</h1>
<p class="warn"><strong>Enthält Klartext.</strong> Dieser Bericht bleibt in Ihrer Ablage und ist nicht für die KI bestimmt.
Erzeugt am {datetime.now():%d.%m.%Y %H:%M} · Platzhalter im Vorgang: {len(vorgang.mapping)}</p>
<p>Legende: {legende}. Gestrichelt umrandete Begriffe wurden erkannt, bleiben aber auf Ihre Entscheidung hin stehen.</p>
<h2>Maskierte Begriffe ({len(maskiert)})</h2><table><tr><th>Begriff</th><th>Platzhalter</th><th>Vorkommen</th></tr>{rows_m}</table>
<h2>Bleibt stehen ({len(bleibt)})</h2><table><tr><th>Begriff</th><th>Vorkommen</th></tr>{rows_b or '<tr><td colspan=2>–</td></tr>'}</table>
{''.join(teile)}
</body></html>"""
