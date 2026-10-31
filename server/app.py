"""HTTP-Schnittstelle der Oberfläche. Läuft nur auf 127.0.0.1; es gibt keine Netzwerkfreigabe.

Alle Antworten sind JSON; Fehler kommen als {"fehler": "…"} mit Status 400/500 und einem Satz, den ein
Nutzer versteht. Die eigentliche Arbeit macht server/dienst.py (Sitzung).
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server import einstellungen as est
from server.dienst import GRUPPEN_ANZEIGE, Modelle, Sitzung

APP_DIR = Path(__file__).resolve().parents[1]
UI_DIR = APP_DIR / "ui"
VERSION = next((p.read_text(encoding="utf-8").strip() for p in (APP_DIR / "VERSION", APP_DIR / "build" / "VERSION")
                if p.exists()), "0.2.0-dev")

app = FastAPI(title="Lokanon", docs_url=None, redoc_url=None, openapi_url=None)
_cfg = est.laden()
modelle = Modelle(_cfg)
sitzung = Sitzung(est.laden, est.speichern, modelle)
fenster = {"webview": None}  # wird vom Launcher gesetzt (pywebview-Fenster für native Dialoge)


@app.exception_handler(ValueError)
async def _value_error(_: Request, exc: ValueError):
    return JSONResponse({"fehler": str(exc)}, status_code=400)


@app.exception_handler(Exception)
async def _any_error(_: Request, exc: Exception):
    return JSONResponse({"fehler": f"Unerwarteter Fehler: {type(exc).__name__}: {exc}"}, status_code=500)


# ---------------------------------------------------------------- Status und Einstellungen

@app.get("/api/status")
def status():
    cfg = est.laden()
    return {"version": VERSION, "modelle_bereit": modelle.bereit, "modelle_fehler": modelle.fehler,
            "eingerichtet": bool(cfg.get("eingerichtet")), "daten_ordner": str(est.daten_ordner()),
            "erweitert": cfg.get("erweitert", {}), "fenster": fenster["webview"] is not None}


@app.get("/api/einstellungen")
def einstellungen_lesen():
    cfg = est.laden()
    cfg["_ausgabe_ordner_effektiv"] = str(est.ausgabe_ordner(cfg))
    cfg["_schluessel_ordner_effektiv"] = str(est.schluessel_ordner(cfg))
    cfg["_vorgaenge_ordner_effektiv"] = str(est.vorgaenge_ordner(cfg))
    from anonymizer.engine import GRUPPEN

    cfg["_gruppen"] = {g: list(ents) for g, ents in GRUPPEN.items()}
    return cfg


class EinstellungenBody(BaseModel):
    werte: dict


ERLAUBT = {"profil", "eingerichtet", "allow_list", "deny_list", "keep_institutions", "mask_locations", "datum_modus",
           "vorgaenge_ordner", "schluessel_ordner", "ausgabe_ordner", "suffix", "ki_textfassung", "erweitert",
           "schluessel_passwort", "entities", "threshold", "propagate_repeats", "include_name_parts", "zuletzt_ordner"}


@app.put("/api/einstellungen")
def einstellungen_schreiben(body: EinstellungenBody):
    cfg = est.laden()
    for k, v in body.werte.items():
        if k == "erweitert" and isinstance(v, dict):
            cfg["erweitert"] = {**cfg.get("erweitert", {}), **{kk: bool(vv) for kk, vv in v.items()}}
        elif k == "suffix":
            s = str(v).strip()
            cfg["suffix"] = s if s and "/" not in s and "\\" not in s else "_anonymisiert"
        elif k in ERLAUBT:
            cfg[k] = v
    est.speichern(cfg)
    return {"ok": True}


# ---------------------------------------------------------------- Sitzung: Dateien, Analyse, Prüfen, Anonymisieren

@app.get("/api/zustand")
def zustand():
    return sitzung.zustand()


@app.post("/api/leeren")
def leeren():
    return sitzung.leeren()


@app.post("/api/dateien")
async def dateien(datei: list[UploadFile] = File(...)):
    out = []
    for f in datei:
        data = await f.read()
        if len(data) > 60 * 1024 * 1024:
            raise ValueError(f"{f.filename}: Datei ist größer als 60 MB.")
        out.append(sitzung.datei_hinzufuegen(f.filename or "datei", data))
    return {"dateien": out}


class PfadBody(BaseModel):
    pfad: str


@app.post("/api/ordner")
def ordner(body: PfadBody):
    return sitzung.ordner_setzen(body.pfad)


class TextBody(BaseModel):
    text: str


@app.post("/api/text")
def text(body: TextBody):
    return sitzung.text_setzen(body.text)


class NameBody(BaseModel):
    name: str


@app.post("/api/datei-entfernen")
def datei_entfernen(body: NameBody):
    return sitzung.datei_entfernen(body.name)


class BegriffeBody(BaseModel):
    begriffe: list[str] = []


@app.post("/api/analyse")
def analyse(body: BegriffeBody):
    if not modelle.bereit and not modelle.fehler:
        modelle.starten()
    sitzung.analysieren(body.begriffe)
    return sitzung.fortschritt.__dict__


@app.get("/api/fortschritt")
def fortschritt():
    return sitzung.fortschritt.__dict__


class IdentitaetBody(BaseModel):
    ph: str
    aktiv: bool | None = None
    bezeichnung: str | None = None
    gehoert_zu: str | None = None
    trennen: str | None = None
    zuordnen: dict | None = None


@app.post("/api/identitaet")
def identitaet(body: IdentitaetBody):
    return sitzung.identitaet(body.ph, body.aktiv, body.bezeichnung, body.gehoert_zu, body.trennen, body.zuordnen)


@app.post("/api/nachtragen")
def nachtragen(body: BegriffeBody):
    sitzung.nachtragen(body.begriffe)
    return sitzung.fortschritt.__dict__


@app.post("/api/anonymisieren")
def anonymisieren():
    sitzung.anonymisieren()
    return sitzung.fortschritt.__dict__


# ---------------------------------------------------------------- Erweitert: Rückübersetzung, KI-Anweisung

class ZurueckBody(BaseModel):
    text: str
    schluessel_pfad: str = ""
    passwort: str = ""


@app.post("/api/zurueck")
def zurueck(body: ZurueckBody):
    return sitzung.zurueck(body.text, body.schluessel_pfad, body.passwort)


@app.get("/api/schluessel")
def schluessel_liste():
    cfg = est.laden()
    ordner = est.schluessel_ordner(cfg)
    out = [{"name": p.name[:-len(".anon.json")], "pfad": str(p), "geaendert": p.stat().st_mtime}
           for p in sorted(ordner.glob("*.anon.json"), key=lambda p: p.stat().st_mtime, reverse=True)]
    return {"schluessel": out, "ordner": str(ordner), "aktuell": sitzung.schluessel_pfad}


@app.get("/api/anweisung")
def anweisung():
    return {"text": sitzung.anweisung()}


@app.get("/api/skill.zip")
def skill_zip():
    return Response(sitzung.skill_zip(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="lokanon-pseudonyme.zip"'})


# ---------------------------------------------------------------- System: Ordner öffnen, Dialoge

@app.post("/api/system/oeffnen")
def oeffnen(body: PfadBody):
    p = Path(body.pfad)
    if not p.exists():
        raise ValueError("Der Ordner existiert noch nicht.")
    if sys.platform == "win32":
        os.startfile(str(p))  # noqa: S606 – lokaler Explorer
    else:
        subprocess.Popen(["xdg-open", str(p)])
    return {"ok": True}


@app.post("/api/system/ordner-waehlen")
def ordner_waehlen():
    """Nativer Ordnerdialog. Im Programmfenster über pywebview, sonst über tkinter."""
    w = fenster["webview"]
    if w is not None:
        import webview

        res = w.create_file_dialog(webview.FOLDER_DIALOG)
        return {"pfad": (res[0] if res else "")}
    ergebnis = {"pfad": ""}

    def _dlg():
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            ergebnis["pfad"] = filedialog.askdirectory(title="Ordner wählen") or ""
            root.destroy()
        except Exception as e:  # pragma: no cover
            ergebnis["fehler"] = str(e)

    t = threading.Thread(target=_dlg)
    t.start()
    t.join()
    if "fehler" in ergebnis:
        raise ValueError("Der Ordnerdialog konnte nicht geöffnet werden. Bitte Pfad eintippen.")
    return {"pfad": ergebnis["pfad"].replace("/", "\\") if sys.platform == "win32" else ergebnis["pfad"]}


# ---------------------------------------------------------------- Produktvorstellung (Deck und Filme)

MARKETING_DIR = APP_DIR / "docs" / "marketing"
# Im Installer liegen die Filme unter docs/marketing/filme, im Entwicklungsstand unter video/out
FILM_ORDNER = [MARKETING_DIR / "filme", APP_DIR / "video" / "out"]
FILME = [
    ("lokanon-visitenkarte.mp4", "Lokanon in zwei Minuten", "2 Min. · ohne Ton"),
    ("lokanon-motion.mp4", "Lokanon in Bewegung", "1 Min. · mit Ton"),
    ("lokanon-teaser.mp4", "Kurzvorstellung", "30 Sek. · ohne Ton"),
]


def _film_pfad(datei: str) -> Path | None:
    if datei not in {f for f, _, _ in FILME}:
        return None
    for ordner in FILM_ORDNER:
        p = ordner / datei
        if p.is_file():
            return p
    return None


@app.get("/api/marketing")
def marketing():
    deck = MARKETING_DIR / "lokanon-visitenkarte.html"
    filme = []
    for datei, titel, dauer in FILME:
        p = _film_pfad(datei)
        if p:
            filme.append({"datei": datei, "titel": titel, "dauer": dauer, "url": f"/marketing-film/{datei}",
                          "pfad": str(p)})
    return {"deck": deck.is_file(), "deck_url": "/marketing/lokanon-visitenkarte.html", "deck_pfad": str(deck),
            "filme": filme, "ordner": str(MARKETING_DIR) if MARKETING_DIR.is_dir() else ""}


@app.get("/marketing-film/{datei}")
def marketing_film(datei: str):
    p = _film_pfad(datei)
    if not p:
        return JSONResponse({"fehler": "Film nicht gefunden."}, status_code=404)
    return FileResponse(p, media_type="video/mp4")


# ---------------------------------------------------------------- Oberfläche und Anleitung

app.mount("/marketing", StaticFiles(directory=str(MARKETING_DIR), html=True, check_dir=False), name="marketing")
app.mount("/anleitung", StaticFiles(directory=str(APP_DIR / "static" / "anleitung"), html=True), name="anleitung")
app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(UI_DIR / "index.html")


@app.get("/favicon.ico")
def favicon():
    return FileResponse(APP_DIR / "assets" / "lokanon.ico")


__all__ = ["app", "modelle", "sitzung", "fenster", "GRUPPEN_ANZEIGE"]
