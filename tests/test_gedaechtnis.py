"""Gedächtnis (gelernte Angaben, Fälle, Fristen, Löschen) ohne Server und ohne Modelle. Alle Daten erfunden."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import gedaechtnis as gm  # noqa: E402

CFG = {"aufbewahrung": {"personen_monate": 12, "abgeschlossen_monate": 3}}


@pytest.fixture
def g(tmp_path, monkeypatch):
    monkeypatch.setattr(gm, "heute", lambda: date(2026, 11, 8))
    monkeypatch.setattr(gm.tresor, "papierkorb", lambda p: Path(p).unlink())
    return gm.Gedaechtnis(lambda: tmp_path)


def _vorgang(g, tmp_path, name, fall):
    pfade = {}
    for art in ("schluessel", "kopie", "test"):
        p = tmp_path / f"{name}-{art}.bin"
        p.write_bytes(b"x")
        pfade[art] = str(p)
    ordner = tmp_path / f"{name}-Vorgang"
    (ordner / "Originale").mkdir(parents=True)
    (ordner / "Originale" / "Brief.txt").write_text("Klartext", encoding="utf-8")
    return g.vorgang_eintragen(name, fall, {"dateien": 1, "angaben": 3, "kopien": [pfade["kopie"]],
                                           "schluessel": pfade["schluessel"], "vorgangsordner": str(ordner),
                                           "testfaelle": [pfade["test"]], "stand": "anonymisiert"}), pfade, ordner


def test_verschluesselt_und_vorschlag_mit_grund(g, tmp_path):
    g.merken("14 C 512/26", [{"text": "Sabine Winter", "art": "PERSON"}, {"text": "Falkenhorst", "art": "PROJEKT"}])
    roh = (tmp_path / gm.DATEI).read_bytes()
    assert b"Winter" not in roh and b"Falkenhorst" not in roh
    e = {x["text"]: x for x in g.fuer_erkennung()["ersetzen"]}
    assert e["Sabine Winter"]["grund"] == "von Ihnen gelernt am 08.11.2026 · Fall 14 C 512/26"
    u = g.uebersicht(CFG)
    fall = u["faelle"][0]
    assert fall["name"] == "14 C 512/26" and [a["text"] for a in fall["angaben"]] == ["Sabine Winter"]
    assert fall["loeschdatum"] == "2027-11-08"
    assert [a["text"] for a in u["ohne_fall"]] == ["Falkenhorst"]  # Projekt: kein Personenbezug, keine Frist


def test_fristen_verlaengern_abschliessen(g):
    fid = g.merken("9 O 88/25", [{"text": "Lena Brinkhoff", "art": "PERSON"}])["fall"]
    u = g.fall_aktion(fid, "verlaengern", CFG, monate=6)
    assert u["faelle"][0]["loeschdatum"] == "2028-05-08"
    u = g.fall_aktion(fid, "verlaengern", CFG, monate=0)
    assert u["faelle"][0]["status"] == "laeuft" and u["faelle"][0]["loeschdatum"] is None
    u = g.fall_aktion(fid, "abschliessen", CFG)
    assert u["faelle"][0]["loeschdatum"] == "2027-02-08"
    with pytest.raises(ValueError):
        g.fall_aktion("f99", "abschliessen", CFG)


def test_hinweis_vor_dem_loeschen_und_aufraeumen(g, tmp_path, monkeypatch):
    vid, pfade, ordner = _vorgang(g, tmp_path, "Nachlass", "9 O 88/25")
    g.merken("9 O 88/25", [{"text": "Lena Brinkhoff", "art": "PERSON"}, {"text": "Jonas Keller", "art": "PERSON"}], vid)
    g.merken("3 O 1120/26", [{"text": "Jonas Keller", "art": "PERSON"}])
    monkeypatch.setattr(gm, "heute", lambda: date(2027, 10, 20))
    u = g.uebersicht(CFG)
    assert [f["name"] for f in u["hinweise"]] == ["9 O 88/25", "3 O 1120/26"]
    monkeypatch.setattr(gm, "heute", lambda: date(2027, 11, 9))
    r = g.aufraeumen(CFG)
    assert r["faelle"] == 2 and not ordner.exists() and not Path(pfade["schluessel"]).exists()
    assert Path(pfade["kopie"]).exists()  # Kopien enthalten keine Namen und bleiben
    u = g.uebersicht(CFG)
    assert not u["faelle"] and u["loeschprotokoll"][0]["grund"] == "Frist abgelaufen"
    assert g.aufraeumen(CFG) == {"faelle": 0}  # nur einmal am Tag


def test_fall_loeschen_mit_geteilter_angabe(g, tmp_path):
    vid, pfade, ordner = _vorgang(g, tmp_path, "Akte Winter", "14 C 512/26")
    g.merken("14 C 512/26", [{"text": "Sabine Winter", "art": "PERSON"}, {"text": "Jonas Keller", "art": "PERSON"}], vid)
    g.merken("3 O 1120/26", [{"text": "Jonas Keller", "art": "PERSON"}])
    g.schluessel_genutzt(pfade["schluessel"])
    fid = next(f["id"] for f in g.uebersicht(CFG)["faelle"] if f["name"] == "14 C 512/26")
    v = g.vorschau(CFG, faelle=[fid])
    assert v["anzahl"] == {"angaben": 1, "geteilt": 1, "schluessel": 1, "vorgangsordner": 1, "testfaelle": 1,
                           "kopien": 1}
    assert any("14 Tagen" in w for w in v["warnungen"])
    r = g.loeschen(CFG, faelle=[fid], grund="abgeschlossen", kopien=True)
    assert r["geloescht"] == {"angaben": 1, "schluessel": 1, "vorgangsordner": 1, "testfaelle": 1, "kopien": 1}
    assert not any(Path(p).exists() for p in pfade.values()) and not ordner.exists()
    texte = [a["text"] for f in g.uebersicht(CFG)["faelle"] for a in f["angaben"]]
    assert texte == ["Jonas Keller"]  # gehört auch zum anderen Fall
    html = g.nachweis_html(r["protokoll_nr"])
    assert "Löschbestätigung" in html and "Winter" not in html and "512/26" not in html


def test_loeschwunsch_ueber_namen(g, tmp_path):
    g.merken("14 C 512/26", [{"text": "Sabine Winter", "art": "PERSON"}])
    g.merken("3 O 1120/26", [{"text": "Sabine Winter", "art": "PERSON"}, {"text": "Jonas Keller", "art": "PERSON"}])
    assert len(g.vorschau(CFG, name="winter")["faelle"]) == 2
    g.loeschen(CFG, name="Winter", grund="mandant", auswahl={"angaben": False})  # Mandantenwunsch: alles muss weg
    assert not g.suche("winter")["angaben"] and not g.uebersicht(CFG)["faelle"]


def test_regeln(g):
    t = "Mandantennr.: 48213\nAktenzeichen AZ-2026-0815 und AZ-2025-0001, PLZ 45127."
    s = t.index("48213")
    r = gm.regel_vorschlag(t, s, s + 5, "KENNNUMMER")
    assert r["art"] == "bezeichnung" and r["wert"] == "Mandantennr."
    s = t.index("AZ-2026")
    r2 = gm.regel_vorschlag(t, s, s + 12, "KENNNUMMER")
    assert r2["art"] == "muster" and r2["form"] == "AZ-0000-0000"
    assert gm.nummern_muster("45127") is None and gm.nummern_muster("Hallo") is None
    g.merken("14 C 512/26", [{"regel": r}, {"regel": r2}])
    treffer = gm.regel_treffer("Mandantennr. 99120 und AZ-2024-1234 sowie 45127", g.fuer_erkennung()["regeln"])
    assert sorted(f.text for f in treffer) == ["99120", "AZ-2024-1234"]
    assert all(f.quelle == "gelernt" and "gelernt" in f.grund for f in treffer)


def test_uebernahme_aus_0_3(g):
    cfg = {"gelernt": {"stehen_lassen": [{"begriff": "Ruhegeld", "datum": "2026-11-01"}],
                       "immer_ersetzen": [{"begriff": "Projekt Phoenix", "datum": "2026-11-01"}]}}
    assert g.uebernehmen(cfg) and "gelernt" not in cfg
    e = g.fuer_erkennung()
    assert e["stehen"] == ["Ruhegeld"] and [x["text"] for x in e["ersetzen"]] == ["Projekt Phoenix"]
    assert g.uebersicht(CFG)["faelle"][0]["name"] == "Übernommen aus Lokanon 0.3.0"
