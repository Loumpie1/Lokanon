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
