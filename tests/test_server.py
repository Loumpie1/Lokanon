"""API-Tests: kompletter Weg über den lokalen Server (Dateien ablegen, Analyse, Prüfen mit Identitäten, Anonymisieren
im gleichen Format, erweiterte Funktionen). Läuft gegen einen eigenen Daten-Ordner (LOKANON_HOME), nicht gegen die
persönlichen Einstellungen."""
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
HOME = Path(os.environ["LOKANON_HOME"])


@pytest.fixture(scope="module")
def client():
    cfg = est.laden()
    cfg.update(eingerichtet=True, allow_list=["Legalizer"], datum_modus="kontext", gliner_model="",  # ohne GLiNER: schneller
               vorgaenge_ordner=str(HOME / "Vorgaenge"), schluessel_ordner=str(HOME / "schluessel"),
               ausgabe_ordner=str(HOME / "Anonymisiert"))
    est.speichern(cfg)
    modelle.cfg = est.laden()
    modelle.starten()
    with TestClient(app) as c:
        yield c


def warte(client, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        f = client.get("/api/fortschritt").json()
        if not f["laeuft"]:
            assert not f["fehler"], f["fehler"]
            return f
        time.sleep(0.3)
    raise AssertionError("Analyse hängt")


def test_status_und_einstellungen(client):
    st = client.get("/api/status").json()
    assert st["eingerichtet"] and st["version"] and "erweitert" in st
    cfg = client.get("/api/einstellungen").json()
    assert "DIKTATZEICHEN" in cfg["entities"] and "_gruppen" in cfg and cfg["suffix"] == "_anonymisiert"
    r = client.put("/api/einstellungen", json={"werte": {"deny_list": ["Projekt Phoenix"], "unbekannt": 1, "suffix": "x/y",
                                                         "erweitert": {"ki_anweisung": True}}})
    assert r.status_code == 200
    cfg = client.get("/api/einstellungen").json()
    assert cfg["deny_list"] == ["Projekt Phoenix"] and cfg["suffix"] == "_anonymisiert" and cfg["erweitert"]["ki_anweisung"]
    client.put("/api/einstellungen", json={"werte": {"deny_list": [], "erweitert": {"ki_anweisung": False}}})


def test_produktvorstellung(client):
    mk = client.get("/api/marketing").json()
    assert mk["deck"] is True
    r = client.get(mk["deck_url"])
    assert r.status_code == 200 and "Lokanon" in r.text
    assert client.get("/marketing/shots/pruefen.jpg").status_code == 200
    for f in mk["filme"]:  # Filme gibt es nur, wenn sie gerendert wurden (video/out) bzw. im Installer
        r = client.get(f["url"], headers={"Range": "bytes=0-99"})
        assert r.status_code in (200, 206) and r.headers["content-type"] == "video/mp4"
    assert client.get("/marketing-film/..%2Fconfig.yaml").status_code == 404
    assert client.get("/marketing-film/geheim.mp4").status_code == 404


def test_kompletter_weg(client):
    client.post("/api/leeren")
    r = client.post("/api/dateien", files=[("datei", ("Schreiben Weber.txt", TEXT.encode("utf-8"), "text/plain"))])
    assert r.status_code == 200 and r.json()["dateien"][0]["name"] == "Schreiben Weber.txt"
    client.post("/api/analyse", json={"begriffe": []})
    warte(client)
    z = client.get("/api/zustand").json()
    ids = {i["name"]: i for i in z["identitaeten"]}
    for muss in ("Thomas Weber", "Goethestraße 12", "0201 5551234", "3 O 123/26", "E-TW 412", "mü/ka"):
        assert any(muss in k for k in ids), muss
    assert "Prokurist" not in ids
    # Identität: Thomas Weber fasst "Weber" und die Unterschrift zusammen
    tw = ids["Thomas Weber"]
    assert "Weber" in tw["varianten"] and tw["anzahl"] >= 3 and tw["anzeige"] == "[Person_1]"
    # Nackter Nachname "Weber" passt zu Thomas und Jonas -> Frage
    assert tw["fragen"] and {k["name"] for k in tw["fragen"][0]["kandidaten"]} == {"Thomas Weber", "Jonas Weber"}
    # Schalter: Spedition Nolte bleibt stehen
    nolte = ids["Spedition Nolte"]
    z = client.post("/api/identitaet", json={"ph": nolte["ph"], "aktiv": False}).json()
    assert "Spedition Nolte" in z["dokumente"][0]["anonym"]
    # Eigene Bezeichnung gilt für alle Schreibweisen
    z = client.post("/api/identitaet", json={"ph": tw["ph"], "bezeichnung": "Mandant"}).json()
    anonym = z["dokumente"][0]["anonym"]
    assert "[Mandant]" in anonym and "Thomas Weber" not in anonym and anonym.count("[Mandant]") == 3
    # Frage beantworten: "Weber" gehört zu Jonas -> jetzt nur noch zwei [Mandant]
    z = client.post("/api/identitaet", json={"ph": tw["ph"], "zuordnen": {"text": "Weber", "ph": ids["Jonas Weber"]["ph"]}}).json()
    assert z["dokumente"][0]["anonym"].count("[Mandant]") == 2
    ids2 = {i["name"]: i for i in z["identitaeten"]}
    assert "Weber" in ids2["Jonas Weber"]["varianten"]
    # Anonymisieren: gleiche Datei, Zusatz im Namen, im Ausgabeordner
    client.post("/api/anonymisieren")
    warte(client)
    z = client.get("/api/zustand").json()
    e = z["ergebnis"]
    assert e["dateien"][0]["status"] == "ok" and e["dateien"][0]["ausgabe"] == "Schreiben Weber_anonymisiert.txt"
    out = Path(e["ordner"]) / "Schreiben Weber_anonymisiert.txt"
    assert out.exists() and e["ordner"] == str(HOME / "Anonymisiert")
    inhalt = out.read_text(encoding="utf-8")
    assert "[Mandant]" in inhalt and "Thomas" not in inhalt and "Spedition Nolte" in inhalt and "Goethestraße" not in inhalt
    assert e["schluessel_pfad"] == ""  # Rückübersetzung ist aus


def test_erweitert_rueckuebersetzung(client):
    client.put("/api/einstellungen", json={"werte": {"erweitert": {"rueckuebersetzung": True}, "schluessel_passwort": "geheim"}})
    client.post("/api/leeren")
    client.post("/api/text", json={"text": "Herr Thomas Weber aus Essen, Az. 3 O 123/26, gegen Autohaus Krause GmbH."})
    client.post("/api/analyse", json={"begriffe": []})
    warte(client)
    client.post("/api/anonymisieren")
    warte(client)
    z = client.get("/api/zustand").json()
    assert z["ergebnis"]["schluessel_pfad"].endswith(".anon.json") and Path(z["ergebnis"]["schluessel_pfad"]).exists()
    antwort = "Sehr geehrter [Person_1], im Verfahren Aktenzeichen 1 gegen [FIRMA_1] gilt Folgendes."
    r = client.post("/api/zurueck", json={"text": antwort}).json()
    assert r["text"] == "Sehr geehrter Thomas Weber, im Verfahren 3 O 123/26 gegen Autohaus Krause GmbH gilt Folgendes."
    keys = client.get("/api/schluessel").json()["schluessel"]
    r = client.post("/api/zurueck", json={"text": antwort, "schluessel_pfad": keys[0]["pfad"], "passwort": "geheim"}).json()
    assert r["text"].startswith("Sehr geehrter Thomas Weber")
    r = client.post("/api/zurueck", json={"text": antwort, "schluessel_pfad": keys[0]["pfad"], "passwort": "falsch"})
    assert r.status_code == 400 and "Passwort" in r.json()["fehler"]
    client.put("/api/einstellungen", json={"werte": {"erweitert": {"rueckuebersetzung": False}}})


def test_ordner_modus_und_fehler(client):
    ordner = HOME / "Akte Krause"
    ordner.mkdir()
    (ordner / "Notiz.txt").write_text("Thomas Weber ruft an, Tel. 0201 5551234.", encoding="utf-8")
    (ordner / "Notiz_anonymisiert.txt").write_text("alt", encoding="utf-8")  # frühere Ausgabe wird nicht erneut gelesen
    client.post("/api/leeren")
    r = client.post("/api/ordner", json={"pfad": str(ordner)}).json()
    assert [d["name"] for d in r["dateien"]] == ["Notiz.txt"]
    client.post("/api/analyse", json={"begriffe": []})
    warte(client)
    client.post("/api/anonymisieren")
    warte(client)
    e = client.get("/api/zustand").json()["ergebnis"]
    assert e["ordner"] == str(ordner)
    assert "[Person_1]" in (ordner / "Notiz_anonymisiert.txt").read_text(encoding="utf-8")
    r = client.post("/api/ordner", json={"pfad": r"C:\gibt\es\nicht"})
    assert r.status_code == 400 and "nicht gefunden" in r.json()["fehler"]
    r = client.post("/api/system/oeffnen", json={"pfad": r"C:\gibt\es\nicht"})
    assert r.status_code == 400
