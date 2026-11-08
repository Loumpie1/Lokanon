"""Verschlüsselung für alles, was Lokanon mit Klartext auf der Platte ablegt (eigene Testfälle, gelernte Angaben,
Fälle, Vorgangsverzeichnis).

Unter Windows mit DPAPI: lesbar nur unter dem Windows-Konto, das die Datei geschrieben hat, auf diesem PC. Ohne
Windows (Entwicklung) oder mit LOKANON_TESTFALL_FERNET dient ein Schlüssel in testfaelle.key im Datenordner.
Das Format beginnt mit sechs Bytes Kennung (DPAPI1 oder FERNET), damit beide Arten lesbar bleiben.
"""
from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path


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
    if not fn(byref(ein), "Lokanon" if schuetzen else None, byref(zusatz), None, None, 0x01, byref(aus)):
        raise OSError("Die Datei ließ sich unter diesem Windows-Konto nicht "
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
    raise ValueError("Unbekanntes Dateiformat.")


def papierkorb(pfad: Path) -> None:
    """Datei in den Papierkorb legen (Windows), sonst löschen. Für anonymisierte Kopien, die keine Personendaten
    enthalten: ein Fehlgriff lässt sich so noch rückgängig machen."""
    pfad = Path(pfad)
    if sys.platform != "win32":
        pfad.unlink()
        return
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_uint16), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]

    # FO_DELETE = 3; FOF_ALLOWUNDO 0x40 | FOF_NOCONFIRMATION 0x10 | FOF_SILENT 0x04 | FOF_NOERRORUI 0x400
    op = SHFILEOPSTRUCTW(None, 3, str(pfad.resolve()) + "\0", None, 0x40 | 0x10 | 0x04 | 0x400, False, None, None)
    if ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) != 0 or pfad.exists():
        raise OSError("Die Datei ließ sich nicht in den Papierkorb legen (vielleicht in einem anderen Programm geöffnet).")
