"""Geprüfte Vorgänge als eigene Testfälle (Einstellungen → Erweitert, standardmäßig aus).

Nach dem Anonymisieren speichert Lokanon je Datei den gelesenen Text und Ihre Entscheidung: welche Stellen ersetzt
wurden (Ihre Korrekturen eingeschlossen) und was Lokanon vorgeschlagen hatte. evaluate.py --eigene misst neue
Versionen daran. So zeigt sich, ob eine Änderung bei Ihren echten Dokumenten hilft, nicht nur bei erfundenen.

Die Dateien enthalten Klartext und sind deshalb mit Windows-DPAPI verschlüsselt: lesbar nur unter Ihrem
Windows-Konto auf diesem PC. Sie verlassen den Rechner nicht und kommen nie ins Projekt. Ohne Windows (Entwicklung)
dient ein Schlüssel in der Datei testfaelle.key im Datenordner.
"""
from __future__ import annotations

import ctypes
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ENDUNG = ".lokanon-test"


def ordner(home: Path) -> Path:
    return home / "testfaelle"


# ------------------------------------------------------------------------------------------- Verschlüsselung
class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(daten: bytes, schuetzen: bool) -> bytes:
    from ctypes import POINTER, byref, c_char, c_uint32, c_void_p, c_wchar_p

    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    fn = crypt32.CryptProtectData if schuetzen else crypt32.CryptUnprotectData
    fn.argtypes = [POINTER(_Blob), c_wchar_p if schuetzen else c_void_p, POINTER(_Blob), c_void_p, c_void_p,
                   c_uint32, POINTER(_Blob)]
    kernel32.LocalFree.argtypes = [c_void_p]
    puffer = ctypes.create_string_buffer(daten, len(daten))
    zusatz_puffer = ctypes.create_string_buffer(b"Lokanon", 7)
    ein = _Blob(len(daten), ctypes.cast(puffer, POINTER(c_char)))
    zusatz = _Blob(7, ctypes.cast(zusatz_puffer, POINTER(c_char)))
    aus = _Blob()
    # 0x01 = CRYPTPROTECT_UI_FORBIDDEN: nie ein Dialogfenster
    if not fn(byref(ein), "Lokanon Testfall" if schuetzen else None, byref(zusatz), None, None, 0x01, byref(aus)):
        raise OSError("Der Testfall ließ sich unter diesem Windows-Konto nicht "
                      + ("verschlüsseln." if schuetzen else "entschlüsseln."))
    try:
        return ctypes.string_at(aus.pbData, aus.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(aus.pbData, c_void_p))


def _fernet(home: Path):
    from cryptography.fernet import Fernet

    k = home / "testfaelle.key"
    if not k.exists():
        k.write_bytes(Fernet.generate_key())
    return Fernet(k.read_bytes())


def verschluesseln(home: Path, daten: bytes) -> bytes:
    if sys.platform == "win32" and not os.environ.get("LOKANON_TESTFALL_FERNET"):
        return b"DPAPI1" + _dpapi(daten, True)
    return b"FERNET" + _fernet(home).encrypt(daten)


def entschluesseln(home: Path, roh: bytes) -> bytes:
    art, rest = roh[:6], roh[6:]
    if art == b"DPAPI1":
        return _dpapi(rest, False)
    if art == b"FERNET":
        return _fernet(home).decrypt(rest)
    raise ValueError("Unbekanntes Testfall-Format.")


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
