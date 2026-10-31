"""Persönliche Einstellungen: %USERPROFILE%\\Lokanon\\einstellungen.yaml, erzeugt aus config.default.yaml.
Eine vorhandene config.yaml im Programmordner (Prototyp) wird einmalig übernommen."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

APP_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PATH = APP_DIR / "config.default.yaml"
ALT_PATH = APP_DIR / "config.yaml"


def daten_ordner() -> Path:
    p = Path(os.environ.get("LOKANON_HOME") or Path(os.environ.get("USERPROFILE", Path.home())) / "Lokanon")
    p.mkdir(parents=True, exist_ok=True)
    return p


def pfad() -> Path:
    return daten_ordner() / "einstellungen.yaml"


def _gruppen_auffuellen(cfg: dict) -> dict:
    """Erkennungstypen werden gruppenweise geschaltet: Ist ein Typ einer Gruppe aktiv, gelten alle Typen der
    Gruppe – so kommen neue Typen (z. B. Diktatzeichen) bei bestehenden Einstellungen automatisch dazu."""
    try:
        from anonymizer.engine import GRUPPEN
    except Exception:
        return cfg
    aktiv = set(cfg.get("entities") or [])
    neu: list[str] = []
    for ents in GRUPPEN.values():
        if any(e in aktiv for e in ents):
            neu += [e for e in ents if e not in neu]
    cfg["entities"] = neu
    # doppelte Allow-Einträge entfernen, Reihenfolge behalten
    gesehen, allow = set(), []
    for a in cfg.get("allow_list") or []:
        if a in ("Claude", "ChatGPT", "Copilot"):
            continue  # frühere Vorgabe, jetzt im Engine eingebaut
        if a and a not in gesehen:
            gesehen.add(a)
            allow.append(a)
    cfg["allow_list"] = allow
    return cfg


def laden() -> dict:
    default = yaml.safe_load(DEFAULT_PATH.read_text(encoding="utf-8")) if DEFAULT_PATH.exists() else {}
    p = pfad()
    if not p.exists() and ALT_PATH.exists():
        try:
            alt = yaml.safe_load(ALT_PATH.read_text(encoding="utf-8")) or {}
            cfg = _gruppen_auffuellen({**default, **alt})
            speichern(cfg)
            return cfg
        except Exception:
            pass
    if p.exists():
        try:
            cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            return _gruppen_auffuellen({**default, **cfg})
        except Exception:
            return dict(default)
    return _gruppen_auffuellen(dict(default))


def speichern(cfg: dict) -> Path:
    p = pfad()
    p.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p


def vorgaenge_ordner(cfg: dict) -> Path:
    from anonymizer.vorgang import standard_vorgaenge_ordner

    p = Path(cfg.get("vorgaenge_ordner") or standard_vorgaenge_ordner())
    p.mkdir(parents=True, exist_ok=True)
    return p


def schluessel_ordner(cfg: dict) -> Path:
    from anonymizer.vorgang import standard_schluessel_ordner

    p = Path(cfg.get("schluessel_ordner") or standard_schluessel_ordner())
    p.mkdir(parents=True, exist_ok=True)
    return p


def dokumente_ordner() -> Path:
    """Der Windows-Ordner „Dokumente“ (auch wenn er auf OneDrive umgeleitet ist), sonst das Benutzerprofil."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                            ("Data4", wintypes.BYTE * 8)]

            fid = GUID(0xFDD39AD0, 0x238F, 0x46AF, (wintypes.BYTE * 8)(0xAD, 0xB4, 0x6D, 0x80, 0xC2, 0x9F, 0x7B, 0x9A))
            out = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(fid), 0, None, ctypes.byref(out)) == 0:
                p = Path(out.value)
                ctypes.windll.ole32.CoTaskMemFree(out)
                if p.is_dir():
                    return p
        except Exception:
            pass
    for name in ("Dokumente", "Documents"):
        p = Path.home() / name
        if p.is_dir():
            return p
    return Path.home()


def ausgabe_ordner(cfg: dict) -> Path:
    """Ablage für Drag & Drop: Einstellung oder Dokumente\\Lokanon\\Anonymisiert."""
    p = Path(cfg.get("ausgabe_ordner") or dokumente_ordner() / "Lokanon" / "Anonymisiert")
    return p
