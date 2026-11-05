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
    # Der Name im Dateinamen wird wie im Text ersetzt ("Weber" allein gehört jetzt zu Jonas)
    neu = f"Schreiben {ids['Jonas Weber']['ph']}_anonymisiert.txt"
    assert e["dateien"][0]["status"] == "ok" and e["dateien"][0]["ausgabe"] == neu
    out = Path(e["ordner"]) / neu
    assert out.exists() and e["ordner"] == str(HOME / "Anonymisiert")
    inhalt = out.read_text(encoding="utf-8")
    assert "[Mandant]" in inhalt and "Thomas" not in inhalt and "Spedition Nolte" in inhalt and "Goethestraße" not in inhalt
    assert e["schluessel_pfad"] == ""  # Rückübersetzung ist aus



def test_lernen_aus_korrekturen(client):
    """"Künftig immer stehen lassen" und "künftig immer suchen" gelten in späteren Durchläufen; in den
    Einstellungen sichtbar und löschbar."""
    def durchlauf(text):
        client.post("/api/leeren")
        client.post("/api/dateien", files=[("datei", ("Notiz.txt", text.encode("utf-8"), "text/plain"))])
        client.post("/api/analyse", json={"begriffe": []})
        warte(client)
        return {i["name"]: i for i in client.get("/api/zustand").json()["identitaeten"]}

    ids = durchlauf(TEXT)
    nolte = ids["Spedition Nolte"]
    assert nolte["belege"] and not nolte["gelernt"]
    client.post("/api/identitaet", json={"ph": nolte["ph"], "aktiv": False})
    z = client.post("/api/lernen", json={"art": "stehen_lassen", "begriffe": nolte["varianten"]}).json()
    assert {i["name"]: i for i in z["identitaeten"]}["Spedition Nolte"]["gelernt"]
    client.post("/api/lernen", json={"art": "immer_ersetzen", "begriffe": ["Projekt Phoenix"]})
    assert client.post("/api/lernen", json={"art": "unbekannt", "begriffe": ["x"]}).status_code == 400
    cfg = client.get("/api/einstellungen").json()
    assert [g["begriff"] for g in cfg["gelernt"]["stehen_lassen"]] == nolte["varianten"]
    assert cfg["gelernt"]["immer_ersetzen"][0]["datum"]
    ids = durchlauf(TEXT + "\nIntern: Projekt Phoenix.")
    assert "Spedition Nolte" not in ids and "Projekt Phoenix" in ids
    # vergessen (Einstellungen speichern ohne Eintrag) -> wieder vorgeschlagen
    client.put("/api/einstellungen", json={"werte": {"gelernt": {}}})
    ids = durchlauf(TEXT)
    assert "Spedition Nolte" in ids and "Formularfeld" not in " ".join(ids["Thomas Weber"]["belege"])

def test_namen_im_dateinamen(client):
    client.post("/api/leeren")
    akte = "Mandant Thomas Weber, Goethestraße 12, 45127 Essen. Herr Weber bittet um Rückruf."
    client.post("/api/dateien", files=[("datei", ("Akte.txt", akte.encode("utf-8"), "text/plain")),
                                       ("datei", ("Notiz Thomas Weber.txt", b"Rueckruf erbeten.", "text/plain")),
                                       ("datei", ("Weber & Co (Entwurf).txt", b"Bitte pruefen.", "text/plain")),
                                       ("datei", ("Weber.txt", b"Termin am Montag.", "text/plain")),
                                       ("datei", ("Thomas-Weber.txt", b"Termin am Dienstag.", "text/plain"))])
    client.post("/api/analyse", json={"begriffe": []})
    warte(client)
    client.post("/api/anonymisieren")
    warte(client)
    e = client.get("/api/zustand").json()["ergebnis"]
    namen = {d["name"]: d["ausgabe"] for d in e["dateien"]}
    # Name steht nur in einer anderen Datei, Sonderzeichen bleiben, gleiche Ausgabenamen werden durchnummeriert
    assert namen["Akte.txt"] == "Akte_anonymisiert.txt"
    assert namen["Notiz Thomas Weber.txt"] == "Notiz Person_1_anonymisiert.txt"
    assert namen["Weber & Co (Entwurf).txt"] == "Person_1 & Co (Entwurf)_anonymisiert.txt"
    assert namen["Weber.txt"] == "Person_1_anonymisiert.txt"
    assert namen["Thomas-Weber.txt"] == "Person_1_anonymisiert (2).txt"
    assert all((Path(e["ordner"]) / n).exists() for n in namen.values())


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


def test_fehlerfall_rueckweg_und_protokoll_ohne_klartext(client, monkeypatch):
    """Scheitert die Gegenprüfung, sagt das Ergebnis wo und was zu tun ist; „Zurück zum Prüfen“ behält die Prüfung;
    das Protokoll nennt nur Platzhalter und Dateinummern."""
    from anonymizer import files as fio
    from server import dienst

    client.post("/api/leeren")
    client.post("/api/dateien", files=[("datei", ("Schreiben Weber.txt", TEXT.encode("utf-8"), "text/plain"))])
    client.post("/api/analyse", json={"begriffe": []})
    warte(client)
    n_ids = len(client.get("/api/zustand").json()["identitaeten"])

    def scheitert(*_a, **_k):
        raise fio.PdfLeck([("Thomas Weber", "im Strukturbaum der PDF (Alternativtext oder Ersatztext, nicht sichtbar)")])
    monkeypatch.setattr(dienst.aus, "erzeuge", scheitert)
    client.post("/api/anonymisieren")
    warte(client)
    d = client.get("/api/zustand").json()["ergebnis"]["dateien"][0]
    assert d["status"] == "fehler" and d["funde"][0]["text"] == "Thomas Weber" and "Strukturbaum" in d["funde"][0]["ort"]
    assert "Textfassung" in d["rat"]

    z = client.post("/api/zurueck-zum-pruefen").json()
    assert z["ergebnis"] is None and z["fortschritt"]["fertig"] and len(z["identitaeten"]) == n_ids

    p = client.get("/api/protokoll").json()
    text = "\n".join(e["text"] for e in p["eintraege"])
    assert "Analyse gestartet" in text and "Gegenprüfung fand [Person_1]" in text and "Datei 1 (.txt)" in text
    datei = "\n".join(f.read_text(encoding="utf-8") for f in Path(p["ordner"]).glob("*.log"))
    for klar in ("Weber", "Goethestraße", "Krause", "Nolte", "0201 5551234"):
        assert klar not in text and klar not in datei, klar


def test_markieren_und_im_rest_suchen(client):
    """Anforderung Markieren und Suchen: Stelle markieren → Fundstellen in allen Dateien (auch getrennt am
    Zeilenende, nicht „Noltenbach“) → anwenden → nichts mehr lesbar; Rückgängig stellt alles wieder her;
    einzelne Stelle stehen lassen und wieder anonymisieren."""
    from server import markieren as mk

    a = ("Die Ware holte die Spedition Nolte am Montag ab. Laut Spedition Nolte fehlte ein Karton.\n"
         "Die Rechnung der Spedi-\ntion Nolte liegt bei.")
    b = "Rückfrage an Spedition Nolte, Lager Noltenbach."
    client.post("/api/leeren")
    client.post("/api/dateien", files=[("datei", ("A.txt", a.encode("utf-8"), "text/plain")),
                                       ("datei", ("B.txt", b.encode("utf-8"), "text/plain"))])
    client.post("/api/analyse", json={"begriffe": []})
    warte(client)
    vorher = [d["anonym"] for d in client.get("/api/zustand").json()["dokumente"]]
    s = a.index("Spedition Nolte") + 2  # ungenau markiert: Wortanfang abgeschnitten
    r = client.post("/api/auswahl", json={"dok": 0, "s": s, "e": s + len("Spedition Nolte") - 2}).json()
    assert r["begriff"] == "Spedition Nolte" and r["art"] == "ORGANIZATION" and r["gesamt"] == 4 and not r["warnung"]
    texte = [st["text"] for f in r["dateien"] for st in f["stellen"]]
    assert "Spedi-\ntion Nolte" in texte and not any("Noltenbach" in t for t in texte)
    stellen = [{"dok": f["i"], "s": st["s"], "e": st["e"]} for f in r["dateien"] for st in f["stellen"] if not st["schon"]]
    if stellen:
        z = client.post("/api/markieren", json={"begriff": r["begriff"], "art": r["art"], "stellen": stellen,
                                               "ursprung": {"dok": 0, "s": r["s"]}}).json()
        assert z["neu"] == len(stellen) and z["rueckgaengig"].startswith("Markierung")
    z = client.get("/api/zustand").json()
    for d in z["dokumente"]:
        assert "Nolte " not in d["anonym"] and "Nolte," not in d["anonym"] and "tion Nolte" not in d["anonym"]
    assert "Noltenbach" in z["dokumente"][1]["anonym"]
    if stellen:
        z = client.post("/api/rueckgaengig").json()
        assert [d["anonym"] for d in z["dokumente"]] == vorher
        client.post("/api/markieren", json={"begriff": r["begriff"], "art": r["art"], "stellen": stellen})
    # Eine Stelle stehen lassen und wieder anonymisieren
    z = client.get("/api/zustand").json()
    import re
    m = re.search(r'data-s="(\d+)" data-e="(\d+)"', z["dokumente"][1]["markiert_html"])
    s1, e1 = int(m.group(1)), int(m.group(2))
    z = client.post("/api/stelle", json={"dok": 1, "s": s1, "e": e1, "aktion": "hier"}).json()
    assert b[s1:e1] in z["dokumente"][1]["anonym"]
    z = client.post("/api/stelle", json={"dok": 1, "s": s1, "e": e1, "aktion": "wieder"}).json()
    assert b[s1:e1] not in z["dokumente"][1]["anonym"]
    # Sehr häufiger Begriff: Warnung
    class D:  # noqa: D401 – Minimaldokument für die reine Textsuche
        name, findings, schluessel = "X.txt", [], {}
        text = "Bank " * 60
    assert mk.fundstellen([D()], "Bank", "MANUELL")["warnung"]
