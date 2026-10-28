"""HTTP-Schnittstelle der Oberfläche. Läuft nur auf 127.0.0.1; es gibt keine Netzwerkfreigabe.

Alle Antworten sind JSON; Fehler kommen als {"fehler": "…"} mit Status 400/500 und einem Satz, den ein
Nutzer versteht. Die eigentliche Arbeit macht server/dienst.py.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server import einstellungen as est
from server.dienst import KARTEN_GRUPPEN, Modelle, VorgangDienst, vorgaenge_liste

APP_DIR = Path(__file__).resolve().parents[1]
UI_DIR = APP_DIR / "ui"
VERSION = (APP_DIR / "VERSION").read_text(encoding="utf-8").strip() if (APP_DIR / "VERSION").exists() else "2.0-pilot"

app = FastAPI(title="Lokanon", docs_url=None, redoc_url=None, openapi_url=None)
_cfg = est.laden()
modelle = Modelle(_cfg)
dienst = VorgangDienst(est.laden, est.speichern, modelle)
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
    return {"version": VERSION, "modelle_bereit": modelle.bereit, "modelle_fehler": modelle.fehler,
            "eingerichtet": bool(est.laden().get("eingerichtet")), "daten_ordner": str(est.daten_ordner()),
            "fenster": fenster["webview"] is not None}


@app.get("/api/einstellungen")
def einstellungen_lesen():
    cfg = est.laden()
    cfg["_vorgaenge_ordner_effektiv"] = str(est.vorgaenge_ordner(cfg))
    cfg["_schluessel_ordner_effektiv"] = str(est.schluessel_ordner(cfg))
    cfg["_gruppen"] = {g: [e for e in ents] for g, ents in _erkennungsgruppen().items()}
    return cfg


class EinstellungenBody(BaseModel):
    werte: dict


@app.put("/api/einstellungen")
def einstellungen_schreiben(body: EinstellungenBody):
    cfg = est.laden()
    erlaubt = {"profil", "eingerichtet", "allow_list", "deny_list", "keep_institutions", "mask_locations", "datum_modus",
               "vorgaenge_ordner", "schluessel_ordner", "entities", "threshold", "gliner_model", "propagate_repeats",
               "include_name_parts", "zuletzt_ordner"}
    for k, v in body.werte.items():
        if k in erlaubt:
            cfg[k] = v
    est.speichern(cfg)
    return {"ok": True}


def _erkennungsgruppen():
    from anonymizer.engine import GRUPPEN

    return GRUPPEN


# ---------------------------------------------------------------- Vorgänge

@app.get("/api/vorgaenge")
def vorgaenge():
    cfg = est.laden()
    return {"vorgaenge": vorgaenge_liste(est.vorgaenge_ordner(cfg)), "zuletzt_ordner": cfg.get("zuletzt_ordner", [])}


class NeuBody(BaseModel):
    name: str
    ordner: str = ""


@app.post("/api/vorgang")
def vorgang_neu(body: NeuBody):
    if body.ordner.strip() and not Path(body.ordner.strip()).is_dir():
        raise ValueError("Der angegebene Ordner wurde nicht gefunden.")
    z = dienst.neu(body.name, body.ordner)
    if body.ordner.strip():
        z["dateien"] = dienst.ordner_dateien()
    return z


@app.get("/api/vorgang")
def vorgang_zustand(kurz: bool = False):
    if dienst.vorgang is None:
        return {"id": ""}
    return dienst.zustand_kurz() if kurz else dienst.zustand()


@app.post("/api/vorgang/datei")
async def datei_hochladen(datei: UploadFile = File(...)):
    data = await datei.read()
    if len(data) > 60 * 1024 * 1024:
        raise ValueError(f"{datei.filename}: Datei ist größer als 60 MB.")
    return dienst.datei_hinzufuegen(datei.filename or "datei", data)


class TextBody(BaseModel):
    text: str


@app.post("/api/vorgang/text")
def text_setzen(body: TextBody):
    if not body.text.strip():
        raise ValueError("Der Text ist leer.")
    return dienst.text_setzen(body.text)


class NameBody(BaseModel):
    name: str


@app.post("/api/vorgang/datei-entfernen")
def datei_entfernen(body: NameBody):
    dienst.datei_entfernen(body.name)
    return {"ok": True}


class AnalyseBody(BaseModel):
    begriffe: list[str] = []


@app.post("/api/vorgang/analysieren")
def analysieren(body: AnalyseBody):
    if not modelle.bereit and not modelle.fehler:
        modelle.starten()
    dienst.analysieren(body.begriffe)
    return dienst.fortschritt.__dict__


@app.get("/api/vorgang/fortschritt")
def fortschritt():
    return dienst.fortschritt.__dict__


class SchaltBody(BaseModel):
    key: str
    aktiv: bool


@app.post("/api/vorgang/begriff")
def begriff(body: SchaltBody):
    return dienst.begriff_schalten(body.key, body.aktiv)


class BezeichnungBody(BaseModel):
    platzhalter: str
    bezeichnung: str


@app.post("/api/vorgang/bezeichnung")
def bezeichnung(body: BezeichnungBody):
    return dienst.bezeichnung_setzen(body.platzhalter, body.bezeichnung)


@app.post("/api/vorgang/nachtragen")
def nachtragen(body: AnalyseBody):
    dienst.nachtragen(body.begriffe)
    return dienst.fortschritt.__dict__


class AusgabeBody(BaseModel):
    formate: list[str] = ["pdf", "docx", "xlsx"]
    anbieter: str = ""


@app.post("/api/vorgang/ausgabe")
def ausgabe(body: AusgabeBody):
    return dienst.ausgabe(body.formate, body.anbieter)


@app.get("/api/vorgang/ki.zip")
def ki_zip():
    v = dienst.vorgang
    name = (v.name if v else "lokanon").replace('"', "")
    return Response(dienst.ki_zip(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{name} - fuer die KI.zip"'})


class AbschlussBody(BaseModel):
    passwort: str
    ordner: str = ""


@app.post("/api/vorgang/abschliessen")
def abschliessen(body: AbschlussBody):
    return dienst.abschliessen(body.passwort, body.ordner or None)


@app.get("/api/vorgang/schluessel")
def schluessel_download(passwort: str):
    v = dienst.vorgang
    if v is None:
        raise ValueError("Kein Vorgang geöffnet.")
    if not passwort:
        raise ValueError("Bitte ein Passwort eingeben.")
    from anonymizer.vorgang import sicherer_name

    return Response(v.schluessel_bytes(passwort), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{sicherer_name(v.name)}.anon.json"'})


class ZurueckBody(BaseModel):
    text: str
    schluessel_pfad: str = ""
    passwort: str = ""


@app.post("/api/zurueck")
def zurueck(body: ZurueckBody):
    if body.schluessel_pfad:
        p = Path(body.schluessel_pfad)
        if not p.exists():
            raise ValueError("Schlüsseldatei nicht gefunden.")
        mapping, bez, name = dienst.schluessel_laden(p.read_bytes(), body.passwort)
        return {"text": dienst.zurueck(body.text, mapping, bez), "vorgang": name, "platzhalter": len(mapping)}
    if dienst.vorgang is None or not dienst.vorgang.mapping:
        raise ValueError("Kein offener Vorgang mit Schlüssel. Bitte Schlüsseldatei wählen.")
    return {"text": dienst.zurueck(body.text), "vorgang": dienst.vorgang.name, "platzhalter": len(dienst.vorgang.mapping)}


@app.post("/api/zurueck/datei")
async def zurueck_datei(text: str, passwort: str, datei: UploadFile = File(...)):
    mapping, bez, name = dienst.schluessel_laden(await datei.read(), passwort)
    return {"text": dienst.zurueck(text, mapping, bez), "vorgang": name, "platzhalter": len(mapping)}


@app.get("/api/schluessel")
def schluessel_liste():
    cfg = est.laden()
    ordner = est.schluessel_ordner(cfg)
    out = []
    for p in sorted(ordner.glob("*.anon.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        out.append({"name": p.name[:-len(".anon.json")], "pfad": str(p),
                    "geaendert": p.stat().st_mtime})
    return {"schluessel": out, "ordner": str(ordner)}


# ---------------------------------------------------------------- KI-Anweisung

@app.get("/api/anweisung")
def anweisung():
    return {"text": dienst.anweisung()}


@app.get("/api/skill.zip")
def skill_zip():
    return Response(dienst.skill_zip(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="lokanon-pseudonyme.zip"'})


# ---------------------------------------------------------------- System: Ordner öffnen, Dialoge

class PfadBody(BaseModel):
    pfad: str


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
            ergebnis["pfad"] = filedialog.askdirectory(title="Aktenordner wählen") or ""
            root.destroy()
        except Exception as e:  # pragma: no cover
            ergebnis["fehler"] = str(e)

    t = threading.Thread(target=_dlg)
    t.start()
    t.join()
    if "fehler" in ergebnis:
        raise ValueError("Der Ordnerdialog konnte nicht geöffnet werden. Bitte Pfad eintippen.")
    return {"pfad": ergebnis["pfad"].replace("/", "\\") if sys.platform == "win32" else ergebnis["pfad"]}


# ---------------------------------------------------------------- Oberfläche und Anleitung

app.mount("/anleitung", StaticFiles(directory=str(APP_DIR / "static" / "anleitung"), html=True), name="anleitung")
app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(UI_DIR / "index.html")


@app.get("/favicon.ico")
def favicon():
    return FileResponse(APP_DIR / "assets" / "lokanon.ico")
