"""API-Tests: kompletter Weg über den lokalen Server (Vorgang anlegen, Text, Analyse, Prüfen, Ausgabe, Schlüssel,
Rückübersetzung). Läuft gegen einen eigenen Daten-Ordner (LOKANON_HOME), nicht gegen die persönlichen Einstellungen."""
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LOKANON_HOME"] = tempfile.mkdtemp(prefix="lokanon-test-")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from fastapi.testclient import TestClient  # noqa: E402

from server import einstellungen as est  # noqa: E402
from server.app import app, modelle  # noqa: E402

TEXT = ("Mandant: Thomas Weber, geb. 03.04.1978, Goethestraße 12, 45127 Essen, Tel. 0201 5551234.\n"
        "Aktenzeichen: 3 O 123/26. Gegner: Autohaus Krause GmbH, Kennzeichen E-TW 412. Unser Zeichen: mü/ka\n"
        "Herr Weber arbeitet als Prokurist bei der Spedition Nolte. Sein Sohn Jonas Weber war Zeuge.\n"
        "Mit freundlichen Grüßen\nThomas Weber")


@pytest.fixture(scope="module")
def client():
    cfg = est.laden()
    home = Path(os.environ["LOKANON_HOME"])
    cfg.update(eingerichtet=True, allow_list=["Legalizer"], datum_modus="kontext", gliner_model="",  # ohne GLiNER: schneller
               vorgaenge_ordner=str(home / "Vorgaenge"), schluessel_ordner=str(home / "schluessel"))
    est.speichern(cfg)
    modelle.cfg = est.laden()
    modelle.starten()
    with TestClient(app) as c:
        yield c


def warte(client, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        f = client.get("/api/vorgang/fortschritt").json()
        if not f["laeuft"]:
            assert not f["fehler"], f["fehler"]
            return f
        time.sleep(0.3)
    raise AssertionError("Analyse hängt")


def test_status_und_einstellungen(client):
    st = client.get("/api/status").json()
    assert st["eingerichtet"] and st["version"]
    cfg = client.get("/api/einstellungen").json()
    assert "DIKTATZEICHEN" in cfg["entities"] and "_gruppen" in cfg
    r = client.put("/api/einstellungen", json={"werte": {"deny_list": ["Projekt Phoenix"], "unbekannt": 1}})
    assert r.status_code == 200
    assert client.get("/api/einstellungen").json()["deny_list"] == ["Projekt Phoenix"]
    client.put("/api/einstellungen", json={"werte": {"deny_list": []}})


def test_kompletter_weg(client):
    z = client.post("/api/vorgang", json={"name": "Weber ./. Krause", "ordner": ""}).json()
    assert z["id"] and z["basis"].endswith("Weber ._. Krause") or z["basis"]
    assert client.post("/api/vorgang/text", json={"text": TEXT}).status_code == 200
    assert (Path(z["basis"]) / "Originale" / "text.txt").read_text(encoding="utf-8") == TEXT
    client.post("/api/vorgang/analysieren", json={"begriffe": []})
    warte(client)
    v = client.get("/api/vorgang").json()
    begriffe = {b["begriff"]: b for b in v["begriffe"]}
    for muss in ("Thomas Weber", "Goethestraße 12", "0201 5551234", "3 O 123/26", "E-TW 412", "mü/ka"):
        assert any(muss in k for k in begriffe), muss
    assert "Prokurist" not in begriffe  # BERUF ist im Kanzlei-Profil aus
    # Schalter: Spedition Nolte bleibt stehen
    key = next(b["key"] for b in v["begriffe"] if b["begriff"] == "Spedition Nolte")
    v = client.post("/api/vorgang/begriff", json={"key": key, "aktiv": False}).json()
    assert "Spedition Nolte" in v["dokumente"][0]["anonym"]
    # Eigene Bezeichnung
    ph = begriffe["Thomas Weber"]["ph_basis"]
    v = client.post("/api/vorgang/bezeichnung", json={"platzhalter": ph, "bezeichnung": "Mandant"}).json()
    assert "[MANDANT]" in v["dokumente"][0]["anonym"] and "Thomas Weber" not in v["dokumente"][0]["anonym"]
    assert v["dokumente"][0]["anonym"].count("[MANDANT]") == 3  # inkl. Namensteil "Weber" und Unterschrift
    # Ausgabe
    r = client.post("/api/vorgang/ausgabe", json={"formate": ["pdf", "docx", "xlsx"], "anbieter": "Claude Team / Enterprise"}).json()
    assert r["ausgaben"][0]["status"] == "ok" and r["hinweise"] == []
    ki = Path(r["ki_ordner"])
    assert (ki / "text.md").read_text(encoding="utf-8").count("[MANDANT]") == 3
    assert (Path(r["basis"]) / "Pruefbericht.html").exists() and (Path(r["basis"]) / "Protokoll.md").exists()
    zip_bytes = client.get("/api/vorgang/ki.zip").content
    assert zip_bytes[:2] == b"PK"
    # Abschluss und Rückübersetzung
    r = client.post("/api/vorgang/abschliessen", json={"passwort": "geheim"}).json()
    assert Path(r["schluessel_pfad"]).exists()
    antwort = "Sehr geehrter [MANDANT], Ihr Sohn [Person 2] ist Zeuge im Verfahren AZ_1 gegen [FIRMA_1]."
    r = client.post("/api/zurueck", json={"text": antwort}).json()
    assert r["text"] == "Sehr geehrter Thomas Weber, Ihr Sohn Jonas Weber ist Zeuge im Verfahren 3 O 123/26 gegen Autohaus Krause GmbH."
    # mit Schlüsseldatei (wie bei einem späteren Vorgang)
    keys = client.get("/api/schluessel").json()["schluessel"]
    r = client.post("/api/zurueck", json={"text": antwort, "schluessel_pfad": keys[0]["pfad"], "passwort": "geheim"}).json()
    assert r["text"].startswith("Sehr geehrter Thomas Weber") and r["vorgang"] == "Weber ./. Krause"
    r = client.post("/api/zurueck", json={"text": antwort, "schluessel_pfad": keys[0]["pfad"], "passwort": "falsch"})
    assert r.status_code == 400 and "Passwort" in r.json()["fehler"]


def test_fehler_sind_verstaendlich(client):
    r = client.post("/api/vorgang", json={"name": "x", "ordner": r"C:\gibt\es\nicht"})
    assert r.status_code == 400 and "nicht gefunden" in r.json()["fehler"]
    r = client.post("/api/system/oeffnen", json={"pfad": r"C:\gibt\es\nicht"})
    assert r.status_code == 400
