"""Geprüfte Vorgänge als eigene Testfälle (Einstellungen → Erweitert, standardmäßig aus).

Nach dem Anonymisieren speichert Lokanon je Datei den gelesenen Text und Ihre Entscheidung: welche Stellen ersetzt
wurden (Ihre Korrekturen eingeschlossen) und was Lokanon vorgeschlagen hatte. evaluate.py --eigene misst neue
Versionen daran. So zeigt sich, ob eine Änderung bei Ihren echten Dokumenten hilft, nicht nur bei erfundenen.

Die Dateien enthalten Klartext und sind deshalb mit Windows-DPAPI verschlüsselt: lesbar nur unter Ihrem
Windows-Konto auf diesem PC. Sie verlassen den Rechner nicht und kommen nie ins Projekt. Ohne Windows (Entwicklung)
dient ein Schlüssel in der Datei testfaelle.key im Datenordner.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from server import tresor

ENDUNG = ".lokanon-test"


def ordner(home: Path) -> Path:
    return home / "testfaelle"


# Verschlüsselung: server/tresor.py (DPAPI, sonst Fernet)
verschluesseln, entschluesseln = tresor.verschluesseln, tresor.entschluesseln


# ------------------------------------------------------------------------------------------- Speichern, Laden
def faelle_aus(docs) -> list[dict]:
    """Je Datei: Text, Goldspannen (Ihre Entscheidung) und die ursprünglichen Vorschläge mit Ergebnis."""
    out = []
    for i, d in enumerate(docs):
        gold = sorted([f.start, f.end, f.entity] for f in d.findings if f.active)
        vorschlaege = sorted([f.start, f.end, f.entity, f.quelle, bool(f.active)]
                             for f in d.findings if f.quelle != "manuell")
        nachgetragen = sum(1 for f in d.findings if f.quelle == "manuell" and f.active)
        out.append({"datei": f"Datei {i + 1} (.{d.name.rsplit('.', 1)[-1].lower()})", "familie": "eigene",
                    "seiten": max(1, len(d.text) // 3000), "text": d.text, "spans": gold,
                    "vorschlaege": vorschlaege, "nachgetragen": nachgetragen})
    return out


def speichern(home: Path, docs) -> Path | None:
    faelle = [f for f in faelle_aus(docs) if f["text"].strip()]
    if not faelle:
        return None
    o = ordner(home)
    o.mkdir(parents=True, exist_ok=True)
    pfad = o / (datetime.now().strftime("%Y-%m-%d_%H%M%S") + ENDUNG)
    roh = "\n".join(json.dumps(f, ensure_ascii=False) for f in faelle).encode("utf-8")
    pfad.write_bytes(verschluesseln(home, roh))
    return pfad


def laden(home: Path) -> list[dict]:
    faelle = []
    for p in sorted(ordner(home).glob("*" + ENDUNG)):
        for z in entschluesseln(home, p.read_bytes()).decode("utf-8").splitlines():
            if z.strip():
                f = json.loads(z)
                f["datei"] = f"{p.stem} / {f['datei']}"
                faelle.append(f)
    return faelle


def uebersicht(home: Path) -> dict:
    dateien = sorted(ordner(home).glob("*" + ENDUNG))
    return {"vorgaenge": len(dateien), "bytes": sum(p.stat().st_size for p in dateien), "ordner": str(ordner(home))}


def alle_loeschen(home: Path) -> int:
    n = 0
    for p in ordner(home).glob("*" + ENDUNG):
        p.unlink()
        n += 1
    return n
