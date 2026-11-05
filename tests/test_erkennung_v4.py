"""Erkennung v4 (05.11.2026): Strukturregeln aus Arztbriefen und Befunden, Filter gegen Medikamente, Fachbegriffe
und Abkürzungen, GLiNER nur mit bekannten Labels, plausible URLs. Alle Texte sind erfunden."""
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from anonymizer import lexikon
from anonymizer.engine import Finding, _url_plausibel, build_analyzer, detect
from anonymizer.felder import feld_treffer
from anonymizer.struktur import struktur_treffer

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def analyzer():
    return build_analyzer("de_core_news_lg")


@pytest.fixture(scope="module")
def cfg():
    return yaml.safe_load((ROOT / "testdaten/kanzlei/config_eval.yaml").read_text(encoding="utf-8"))


def _detect(analyzer, cfg, text):
    return detect(analyzer, text, entities=cfg["entities"], threshold=0.4, allow_list=cfg.get("allow_list"),
                  deny_list=[], manual_terms=None, propagate_repeats=True, include_name_parts=True,
                  mask_locations=False, keep_institutions=True)


def _texte(treffer, art=None):
    return {f.text for f in treffer if art is None or f.entity == art}


def test_geburtsdatum_mit_stern_und_kurzformen():
    text = ("Wir berichten über Frau Ilse Brommer (* 4.4.1957), Herrn Ole Taddik, *21/3/1949, und "
            "Name: Jens Vohwinkel, Geb.Dat.: 21.06.67. Kontrolle am 12.05.2026, Leukozyten 4*10^9.")
    daten = _texte(struktur_treffer(text), "DATUM")
    assert daten == {"4.4.1957", "21/3/1949", "21.06.67"}


def test_nachname_komma_vorname_und_titel_mit_initialen():
    text = ("Patientin: Brommer, Ilse geb. am 21.09.1957\nBetr.: TADDIK, Ole\nDiagnose, Maria hat Fieber.\n"
            "Mit freundlichen Grüßen\nProf. Dr. med. V. Kessling     Dr. med. Helmuth Leber\n"
            "gez. Dr.med.univers. B. Supanc\nUntersuchung durch: Priv.Doz. Dr.in Mersa Kovac-Braun\n"
            "Frau I. ist eine 82-jährige Patientin.")
    personen = _texte(struktur_treffer(text), "PERSON")
    for name in ("Brommer, Ilse", "TADDIK, Ole", "V. Kessling", "Helmuth Leber", "B. Supanc", "Mersa Kovac-Braun", "I."):
        assert name in personen, name
    assert not any("Diagnose" in p or "Maria" == p for p in personen)


def test_postleitzahl_mit_land_und_strasse_im_anschriftblock():
    text = "Klinik für Chirurgie\nKlinikvorstand: Prof. Dr. Hanno Wurst\nA-3336 St. Kolomann am Berg\nSonnblick 32,\nTel. 01234"
    t = struktur_treffer(text)
    assert "A-3336 St. Kolomann am Berg" in _texte(t, "PLZ_ORT") and "Sonnblick 32" in _texte(t, "ADRESSE")


def test_klinik_kennnummern_als_feld():
    text = "Frau Ilse Brommer, Fall-Nr.6733340001, PIZ: 1822544, FN:445544767, E-Nr.: 17217277\nSV Nr.: 4445311299"
    werte = {f.text for f in feld_treffer(text, ["KENNNUMMER", "DE_SOCIAL_SECURITY"])}
    assert {"6733340001", "1822544", "445544767", "17217277", "4445311299"} <= werte


def test_medikamente_abkuerzungen_und_befundsaetze_keine_namen(analyzer, cfg):
    text = ("Medikation: Concor 5 MG 1-0-0, Novalgin Trpf bei Bedarf, Fucidine Salbe.\n"
            "Pat. ist wach. Unauff. Befund. Labor: Leuko 8.830, Hb 9.4, CRP 0.9.\n"
            "Befund: deutliches kogn. Defizit, Gangunsicherheit. Zustand nach Pleurapunktion.\n"
            "Die Patientin Ilse Brommer wurde von Dr. Kessling betreut.")
    f = _detect(analyzer, cfg, text)
    gefunden = _texte(f)
    assert "Ilse Brommer" in gefunden and any("Kessling" in g for g in gefunden)
    for kein in ("Concor", "Novalgin", "Fucidine", "Pat", "Unauff", "Leuko 8.830", "Hb 9.4", "Gangunsicherheit",
                 "Pleurapunktion"):
        assert not any(kein in g for g in gefunden), kein
    assert not any(x.entity == "DIKTATZEICHEN" for x in f)


def test_url_nur_mit_plausibler_domain():
    assert _url_plausibel("www.kanzlei-beispiel.de") and _url_plausibel("praxis-brommer.de")
    assert _url_plausibel("https://example.org/a")
    for kein in ("A.me", "c.et", "Neurolog.St", "Mening.ne", "BWS.Al"):
        assert not _url_plausibel(kein), kein


def test_wortlisten_medizin_ohne_eigennamen():
    assert lexikon.ist_medizin("Ramipril") and lexikon.ist_medizin("Laparotomie")
    for name in ("Alzheimer", "Parkinson", "Crohn", "Fischer", "Weber"):
        assert not lexikon.ist_medizin(name), name
    assert lexikon.ist_abkuerzung("Unauff") and lexikon.ist_abkuerzung("körperl")


def test_unterschriftenblock_unter_urteil():
    text = ("Die Kostenentscheidung folgt aus § 91 ZPO.\n Gallner\n Brune\n Schlünder\n M. Trümner\n"
            "Lehrereingruppierung\nDiagnosen\nTherapie\nVerlauf\n")
    personen = _texte(struktur_treffer(text), "PERSON")
    assert personen == {"Gallner", "Brune", "Schlünder", "M. Trümner"}


def test_aktiengesellschaft_ist_keine_einrichtung(analyzer, cfg):
    """Das Kürzel „AG“ steht für Amtsgericht nur am Anfang („AG Essen“), „Siemens AG“ muss ersetzt werden."""
    from anonymizer.engine import _is_institution

    assert _is_institution("AG Essen") and _is_institution("LG Duisburg")
    assert not _is_institution("Krause Logistik AG") and not _is_institution("H AG")
    f = _detect(analyzer, cfg, "Der Kläger war bei der Krause Logistik AG beschäftigt. Das AG Essen hat entschieden.")
    assert "Krause Logistik AG" in _texte(f, "ORGANIZATION")
    assert not any("AG Essen" in t for t in _texte(f))
