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
from server.gedaechtnis import Gedaechtnis

APP_DIR = Path(__file__).resolve().parents[1]
UI_DIR = APP_DIR / "ui"
VERSION = next((p.read_text(encoding="utf-8").strip() for p in (APP_DIR / "VERSION", APP_DIR / "build" / "VERSION")
                if p.exists()), "0.3.0-dev")

app = FastAPI(title="Lokanon", docs_url=None, redoc_url=None, openapi_url=None)
_cfg = est.laden()
modelle = Modelle(_cfg)
gedaechtnis = Gedaechtnis(est.daten_ordner)
sitzung = Sitzung(est.laden, est.speichern, modelle, gedaechtnis=gedaechtnis)
fenster = {"webview": None}  # wird vom Launcher gesetzt (pywebview-Fenster für native Dialoge)
uebung: dict = {}  # Einführung: eigene Sitzung mit Temp-Ordner, solange sie läuft
letzte_fehler: set[str] = set()  # Dateien, die beim letzten Löschen übrig blieben („Erneut versuchen“)


def aktiv() -> Sitzung:
    """Die Sitzung, mit der die Oberfläche gerade spricht: während der Einführung die Übungssitzung."""
    return uebung.get("sitzung") or sitzung


def _gelerntes_uebernehmen() -> None:
    """Gelernte Begriffe aus 0.3.0 (Klartext in einstellungen.yaml) verschlüsselt ins Gedächtnis übernehmen."""
    try:
        cfg = est.laden()
        if gedaechtnis.uebernehmen(cfg):
            est.speichern(cfg)
    except Exception as e:  # pragma: no cover
        sitzung.protokoll.ausnahme("Gelernte Begriffe übernehmen", e)


_gelerntes_uebernehmen()


@app.exception_handler(ValueError)
async def _value_error(_: Request, exc: ValueError):
    return JSONResponse({"fehler": str(exc)}, status_code=400)


@app.exception_handler(Exception)
async def _any_error(req: Request, exc: Exception):
    aktiv().protokoll.ausnahme(f"Anfrage {req.url.path}", exc)
    return JSONResponse({"fehler": f"Unerwarteter Fehler: {type(exc).__name__}: {exc}"}, status_code=500)


# ---------------------------------------------------------------- Status und Einstellungen

@app.get("/api/status")
def status():
    cfg = est.laden()
    try:  # abgelaufene Fälle löschen, einmal am Tag
        gedaechtnis.aufraeumen(cfg)
    except Exception as e:
        sitzung.protokoll.ausnahme("Aufräumen nach Frist", e)
    return {"version": VERSION, "modelle_bereit": modelle.bereit, "modelle_fehler": modelle.fehler,
            "eingerichtet": bool(cfg.get("eingerichtet")), "daten_ordner": str(est.daten_ordner()),
            "erweitert": cfg.get("erweitert", {}), "fenster": fenster["webview"] is not None,
            "einfuehrung": cfg.get("einfuehrung") or {}, "uebung": bool(uebung)}


@app.get("/api/einstellungen")
def einstellungen_lesen():
    cfg = aktiv().cfg_laden()
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
           "schluessel_passwort", "entities", "threshold", "propagate_repeats", "include_name_parts", "zuletzt_ordner",
           "aufbewahrung", "einfuehrung"}


@app.put("/api/einstellungen")
def einstellungen_schreiben(body: EinstellungenBody):
    cfg = aktiv().cfg_laden()
    for k, v in body.werte.items():
        if k == "erweitert" and isinstance(v, dict):
            cfg["erweitert"] = {**cfg.get("erweitert", {}), **{kk: bool(vv) for kk, vv in v.items()}}
        elif k == "suffix":
            s = str(v).strip()
            cfg["suffix"] = s if s and "/" not in s and "\\" not in s else "_anonymisiert"
        elif k == "aufbewahrung" and isinstance(v, dict):
            cfg["aufbewahrung"] = {**(cfg.get("aufbewahrung") or {}), **v}
        elif k in ERLAUBT:
            cfg[k] = v
    aktiv().cfg_speichern(cfg)
    return {"ok": True}


# ---------------------------------------------------------------- Sitzung: Dateien, Analyse, Prüfen, Anonymisieren

@app.get("/api/zustand")
def zustand():
    return aktiv().zustand()


@app.post("/api/leeren")
def leeren():
    return aktiv().leeren()


@app.post("/api/dateien")
async def dateien(datei: list[UploadFile] = File(...)):
    out = []
    for f in datei:
        data = await f.read()
        if len(data) > 60 * 1024 * 1024:
            raise ValueError(f"{f.filename}: Datei ist größer als 60 MB.")
        out.append(aktiv().datei_hinzufuegen(f.filename or "datei", data))
    return {"dateien": out}


class PfadBody(BaseModel):
    pfad: str


@app.post("/api/ordner")
def ordner(body: PfadBody):
    return aktiv().ordner_setzen(body.pfad)


class TextBody(BaseModel):
    text: str


@app.post("/api/text")
def text(body: TextBody):
    return aktiv().text_setzen(body.text)


class NameBody(BaseModel):
    name: str


@app.post("/api/datei-entfernen")
def datei_entfernen(body: NameBody):
    return aktiv().datei_entfernen(body.name)


class BegriffeBody(BaseModel):
    begriffe: list[str] = []


@app.post("/api/analyse")
def analyse(body: BegriffeBody):
    if not modelle.bereit and not modelle.fehler:
        modelle.starten()
    aktiv().analysieren(body.begriffe)
    return aktiv().fortschritt.__dict__


@app.get("/api/fortschritt")
def fortschritt():
    return aktiv().fortschritt.__dict__


class IdentitaetBody(BaseModel):
    ph: str
    aktiv: bool | None = None
    bezeichnung: str | None = None
    gehoert_zu: str | None = None
    trennen: str | None = None
    zuordnen: dict | None = None


@app.post("/api/identitaet")
def identitaet(body: IdentitaetBody):
    return aktiv().identitaet(body.ph, body.aktiv, body.bezeichnung, body.gehoert_zu, body.trennen, body.zuordnen)


class LernenBody(BaseModel):
    art: str
    begriffe: list[str]


@app.post("/api/lernen")
def lernen(body: LernenBody):
    return aktiv().lernen(body.art, body.begriffe)


@app.post("/api/nachtragen")
def nachtragen(body: BegriffeBody):
    aktiv().nachtragen(body.begriffe)
    return aktiv().fortschritt.__dict__


@app.post("/api/anonymisieren")
def anonymisieren():
    aktiv().anonymisieren()
    return aktiv().fortschritt.__dict__


class AuswahlBody(BaseModel):
    dok: int
    s: int
    e: int
    art: str | None = None


@app.post("/api/auswahl")
def auswahl(body: AuswahlBody):
    """Markierte Stelle: ausgerichtet, Art-Vorschlag und alle Fundstellen im Vorgang (noch nichts angewendet)."""
    return aktiv().auswahl(body.dok, body.s, body.e, body.art)


class MarkierenBody(BaseModel):
    begriff: str
    art: str
    stellen: list[dict]
    ursprung: dict | None = None
    gehoert_zu: str = ""
    lernen: bool = False


@app.post("/api/markieren")
def markieren(body: MarkierenBody):
    return aktiv().markieren(body.begriff, body.art, body.stellen, body.ursprung, body.gehoert_zu, body.lernen)


class StelleBody(BaseModel):
    dok: int
    s: int
    e: int
    aktion: str


@app.post("/api/stelle")
def stelle(body: StelleBody):
    return aktiv().stelle(body.dok, body.s, body.e, body.aktion)


@app.post("/api/rueckgaengig")
def rueckgaengig():
    return aktiv().rueckgaengig()


@app.post("/api/zurueck-zum-pruefen")
def zurueck_zum_pruefen():
    return aktiv().zurueck_zum_pruefen()


@app.get("/api/testfaelle")
def testfaelle_uebersicht():
    from server import testfaelle as tf

    return tf.uebersicht(est.daten_ordner())


@app.delete("/api/testfaelle")
def testfaelle_loeschen():
    from server import testfaelle as tf

    return {"geloescht": tf.alle_loeschen(est.daten_ordner())}


@app.get("/api/protokoll")
def protokoll():
    """Einträge des letzten Durchlaufs (ohne Klartext) und der Ordner mit den Protokolldateien."""
    return {"eintraege": aktiv().protokoll.eintraege, "ordner": str(aktiv().protokoll.ordner)}


# ---------------------------------------------------------------- Fälle, gelernte Angaben, Löschen

class FallBody(BaseModel):
    name: str


@app.post("/api/fall-setzen")
def fall_setzen(body: FallBody):
    """Fall des laufenden Vorgangs bestätigen oder ändern."""
    return aktiv().fall_setzen(body.name)


class MerkenBody(BaseModel):
    fall: str
    eintraege: list[dict]


@app.post("/api/merken")
def merken(body: MerkenBody):
    """Abschlussfenster: bestätigte Angaben und Regeln für künftige Dokumente speichern."""
    s = aktiv()
    r = s.gd.merken(body.fall, body.eintraege, s.vorgang_id)
    s.fall = body.fall
    if s.ergebnis is not None:
        s.ergebnis["gemerkt"] = True
    return r


@app.get("/api/faelle")
def faelle():
    s = aktiv()
    return s.gd.uebersicht(s.cfg_laden())


class FallAktionBody(BaseModel):
    id: str
    aktion: str
    monate: int = 0
    name: str = ""


@app.post("/api/fall")
def fall_aktion(body: FallAktionBody):
    s = aktiv()
    return s.gd.fall_aktion(body.id, body.aktion, s.cfg_laden(), body.monate, body.name)


@app.get("/api/gedaechtnis/suche")
def gedaechtnis_suche(q: str = ""):
    return aktiv().gd.suche(q)


@app.delete("/api/angabe/{aid}")
def angabe_entfernen(aid: str):
    s = aktiv()
    s.gd.angabe_entfernen(aid)
    return s.gd.uebersicht(s.cfg_laden())


class LoeschenBody(BaseModel):
    faelle: list[str] = []
    vorgaenge: list[str] = []
    name: str = ""
    grund: str = "hand"
    kopien: bool = False
    auswahl: dict = {}


@app.post("/api/loeschen/vorschau")
def loeschen_vorschau(body: LoeschenBody):
    s = aktiv()
    return s.gd.vorschau(s.cfg_laden(), body.faelle, body.vorgaenge, body.name,
                         [s.vorgang_id] if s.vorgang_id else [])


@app.post("/api/loeschen")
def loeschen(body: LoeschenBody):
    """Fall, Vorgang oder alles zu einem Namen löschen. Ein gerade offener Vorgang wird dabei geschlossen; zuletzt
    benutzte Ordner der gelöschten Vorgänge verschwinden aus den Einstellungen."""
    s = aktiv()
    cfg = s.cfg_laden()
    ordner = {v.get("ordner") for v in s.gd.laden()["vorgaenge"]
              if v["fall"] in body.faelle or v["id"] in body.vorgaenge}
    r = s.gd.loeschen(cfg, body.faelle, body.vorgaenge, body.name, body.grund, body.kopien, body.auswahl)
    letzte_fehler.clear()
    letzte_fehler.update(f["pfad"] for f in r["fehler"])
    if s.vorgang_id and s.vorgang_id in r["vorgaenge"]:
        s.leeren()
    ordner.discard(None)
    ordner.discard("")
    if ordner and any(z in ordner for z in cfg.get("zuletzt_ordner", [])):
        cfg["zuletzt_ordner"] = [z for z in cfg.get("zuletzt_ordner", []) if z not in ordner]
        s.cfg_speichern(cfg)
    return {**r, "uebersicht": s.gd.uebersicht(cfg)}


class PfadeBody(BaseModel):
    pfade: list[str]


@app.post("/api/loeschen/nochmal")
def loeschen_nochmal(body: PfadeBody):
    """„Erneut versuchen“ nach dem Löschen: nur Dateien, die beim letzten Löschen übrig blieben."""
    import shutil

    fehler = []
    for p in body.pfade:
        if p not in letzte_fehler:
            continue
        try:
            q = Path(p)
            shutil.rmtree(q) if q.is_dir() else q.unlink(missing_ok=True)
            letzte_fehler.discard(p)
        except OSError as e:
            fehler.append({"art": "", "pfad": p, "grund": str(e)})
    return {"fehler": fehler}


@app.get("/api/loeschnachweis/{nr}", response_class=HTMLResponse)
def loeschnachweis(nr: str):
    return HTMLResponse(aktiv().gd.nachweis_html(nr))


# ---------------------------------------------------------------- Einführung (Übungssitzung)

@app.post("/api/einfuehrung/start")
def einfuehrung_start():
    """Übungssitzung mit eigenem Temp-Ordner und flüchtigen Einstellungen: Gelerntes, Testfälle, Protokoll und
    Schlüssel der Übung landen nicht in den echten Daten. Eine offene echte Arbeit bleibt unberührt."""
    import tempfile

    from server import einfuehrung as ef

    einfuehrung_ende()
    home = Path(tempfile.mkdtemp(prefix="lokanon-uebung-"))
    cfg = {**est.laden(), "allow_list": ef.ALLOW, "ausgabe_ordner": str(home / "Anonymisiert"),
           "schluessel_ordner": str(home / "schluessel"), "vorgaenge_ordner": str(home / "Vorgaenge"),
           "schluessel_passwort": "uebung", "zuletzt_ordner": [],
           "erweitert": {"rueckuebersetzung": True, "ki_anweisung": True, "vorgaenge": False, "testfaelle": False}}
    cfg["aufbewahrung"] = {**(cfg.get("aufbewahrung") or {}), "lernen_fragen": True}
    zustand = {"cfg": cfg}
    s = Sitzung(lambda: dict(zustand["cfg"]), lambda c: zustand.update(cfg=c), modelle, home_fn=lambda: home,
                uebung=True)
    ef.beispielfaelle(s.gd, cfg)
    uebung.update(sitzung=s, home=home)
    return s.zustand()


@app.post("/api/einfuehrung/beispiel")
def einfuehrung_beispiel():
    from server import einfuehrung as ef

    if not uebung:
        einfuehrung_start()
    return uebung["sitzung"].uebung_laden(ef.BEISPIEL)


@app.post("/api/einfuehrung/ende")
def einfuehrung_ende():
    import shutil

    home = uebung.get("home")
    uebung.clear()
    if home:
        shutil.rmtree(home, ignore_errors=True)
    return sitzung.zustand()


# ---------------------------------------------------------------- Erweitert: Rückübersetzung, KI-Anweisung

class ZurueckBody(BaseModel):
    text: str
    schluessel_pfad: str = ""
    passwort: str = ""


@app.post("/api/zurueck")
def zurueck(body: ZurueckBody):
    return aktiv().zurueck(body.text, body.schluessel_pfad, body.passwort)


@app.get("/api/schluessel")
def schluessel_liste():
    cfg = aktiv().cfg_laden()
    ordner = est.schluessel_ordner(cfg)
    out = [{"name": p.name[:-len(".anon.json")], "pfad": str(p), "geaendert": p.stat().st_mtime}
           for p in sorted(ordner.glob("*.anon.json"), key=lambda p: p.stat().st_mtime, reverse=True)]
    return {"schluessel": out, "ordner": str(ordner), "aktuell": aktiv().schluessel_pfad}


@app.get("/api/anweisung")
def anweisung():
    return {"text": aktiv().anweisung()}


@app.get("/api/skill.zip")
def skill_zip():
    return Response(aktiv().skill_zip(), media_type="application/zip",
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


class DateiNrBody(BaseModel):
    i: int


@app.post("/api/ergebnis/oeffnen")
def ergebnis_oeffnen(body: DateiNrBody):
    """Eine gerade erzeugte Kopie mit dem Standardprogramm öffnen. Nur Dateien aus dem aktuellen Ergebnis,
    keine beliebigen Pfade."""
    e = aktiv().ergebnis or {}
    dateien = e.get("dateien", [])
    if not (0 <= body.i < len(dateien)) or dateien[body.i].get("status") != "ok":
        raise ValueError("Diese Kopie gibt es im Ergebnis nicht.")
    p = Path(dateien[body.i]["pfad"])
    if not p.is_file():
        raise ValueError("Die Kopie ist nicht mehr da. Wurde sie verschoben oder gelöscht?")
    return oeffnen(PfadBody(pfad=str(p)))


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
