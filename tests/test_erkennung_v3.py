"""Erkennung v3 (04.11.2026): Tabellenaufbau, Felder (Bezeichnung → Wert), Wörterbuch-Prüfung, Kontextwörter als
ganzes Wort, Ligaturen in der Leck-Prüfung. Alle Texte und Dokumente sind erfunden."""
import io
import sys
from pathlib import Path

import docx
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from anonymizer import files as fio
from anonymizer import lexikon
from anonymizer.engine import build_analyzer, detect, pseudonymize, replacement_pairs
from anonymizer.felder import feld_treffer

ROOT = Path(__file__).resolve().parents[1]
KORPUS = ROOT / "testdaten/korpus"


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


def test_felder_tabelle_kopf_und_zeile(cfg):
    text = ("Versicherungsnehmer Name | Koch | Wolf\n"
            "Vorname | Stefanie | Michael\n"
            "Steuer-ID | SV-Nummer | Krankenkasse | Geburtsdatum\n"
            "57 281 463 956 | 13 150380 B 120 | AOK Rheinland/Hamburg | 15.03.1980\n"
            "Personalnummer | Steuerklasse | Konfession\n"
            "004711 | 1 | rk\n"
            "Zeuge | Anschrift | Telefon\n"
            "Ayşe Demir | Aktienstraße 88 | 0176 55120983\n"
            "Name | Menge | Preis\n"
            "Thermostatkopf Danfoss RA 2000 | 4 | 24,90\n"
            "Lastschrift Vertrag 4711-3392-01 Kd-Nr. 300-4471-882 | -96,00\n"
            "Versichertennr.: F703815524   Fallnummer: 2026-118044\n")
    got = {(f.entity, f.text) for f in feld_treffer(text, cfg["entities"])}
    for erwartet in [("PERSON", "Koch"), ("PERSON", "Wolf"), ("PERSON", "Stefanie"), ("PERSON", "Michael"),
                     ("DE_TAX_ID", "57 281 463 956"), ("DE_SOCIAL_SECURITY", "13 150380 B 120"),
                     ("DATUM", "15.03.1980"), ("PERSONALNR", "004711"), ("PERSON", "Ayşe Demir"),
                     ("VERSICHERUNGSNR", "4711-3392-01"), ("KENNNUMMER", "300-4471-882"),
                     ("DE_HEALTH_INSURANCE", "F703815524"), ("KENNNUMMER", "2026-118044")]:
        assert erwartet in got, erwartet
    texte = {t for _e, t in got}
    # Bezeichnungen und Spaltenköpfe sind nie Werte, Beträge und Produkte auch nicht
    assert not texte & {"Anschrift", "Telefon", "Menge", "Preis", "Steuerklasse", "1", "24,90", "-96,00"}
    assert not any("Thermostat" in t for t in texte)


def test_lexikon_gewoehnliche_woerter_und_namen():
    for w in ("Gespräch", "Vaters", "Ferienregelung", "Familienpsychologisches", "Schadentag", "Krankengeldzuschuss",
              "AN-Anteil"):
        assert lexikon.gewoehnlich(w), w
    # Nachnamen, die auch Wörter sind, und unbekannte Namen entscheidet weiter das Modell
    for w in ("Fischer", "Koch", "Engel", "Vogel", "Brinkhoff", "Kowalczyk", "Rehbein", "Lindemann", "Hoffmann"):
        assert not lexikon.gewoehnlich(w), w


def test_fachwoerter_sind_keine_namen(analyzer, cfg):
    text = ("Herr Werner Fuchs stellte sich mit Diarrhöen vor. Ileitis terminalis im MRT. Das Gespräch mit dem "
            "Vater ergab keine Hinweise. Die Ferienregelung bleibt. Gefahren wurde ein Skoda Octavia.\n"
            "Frau\nMonika Klein\nZweigertstraße 8\n45130 Essen\n")
    texte = {f.text for f in _detect(analyzer, cfg, text) if f.entity in ("PERSON", "ORGANIZATION")}
    assert {"Werner Fuchs", "Monika Klein"} <= texte
    assert not texte & {"Ileitis terminalis", "Gespräch", "Ferienregelung", "Skoda Octavia", "Vater"}


def test_kontextwort_nur_als_ganzes_wort(analyzer, cfg):
    text = ("Geburtsdatum: 14.02.1961\n\nVersicherungsverlauf (Auszug)\nArbeitgeber | Zeitraum\n"
            "Stahlbau Kerkhoff GmbH | 01.09.1980 – 30.06.2004\n")
    daten = {f.text for f in _detect(analyzer, cfg, text) if f.entity == "DATUM"}
    assert "14.02.1961" in daten
    assert not daten & {"01.09.1980", "30.06.2004"}  # "Arbeitgeber" enthält "geb", ist aber kein Geburtskontext


def test_tabellen_trennzeichen_nie_in_ausgabe(analyzer, cfg):
    d = docx.Document()
    d.add_paragraph("Schadenmeldung")
    t = d.add_table(rows=3, cols=2)
    for r, (a, b) in enumerate([("Name", "Schneider"), ("Vorname", "Monika"), ("Telefon", "0208 4419273")]):
        t.cell(r, 0).text, t.cell(r, 1).text = a, b
    buf = io.BytesIO()
    d.save(buf)
    text, _ = fio.read_document("meldung.docx", buf.getvalue())
    assert "Name | Schneider" in text
    fs = _detect(analyzer, cfg, text)
    assert {"Schneider", "Monika", "0208 4419273"} <= {f.text for f in fs}
    assert not any("|" in f.text for f in fs)
    res = pseudonymize(text, fs)
    pairs = replacement_pairs(text, fs, res.mapping, None, res.zuordnung)
    assert not any("|" in o for o, _p in pairs)
    out = fio.read_document("x.docx", fio.write_docx(buf.getvalue(), pairs))[0]
    assert "Schneider" not in out and "Monika" not in out and "|" not in out.replace(" | ", "")


def test_umbruch_in_tabellenzelle_bleibt_zusammen():
    import pymupdf

    page = pymupdf.open(KORPUS / "L2_Kontoauszug_Wolf.pdf")[0]
    text = fio.pdf_zeilentext(page)
    assert any("DE41 3506 0190 0001 5200 33" in z for z in text.splitlines())
    assert "Buchungstag | Wertstellung" in text


def test_leckpruefung_findet_namen_trotz_ligatur():
    data = (KORPUS / "B4_Rentenbescheid_Hoffmann.pdf").read_bytes()  # PDF-Schrift setzt "ff" als Ligatur "ﬀ"
    import pymupdf

    assert "Hoﬀmann" in pymupdf.open(stream=data, filetype="pdf")[0].get_text()
    assert fio.verify_pdf(data, ["Renate Hoffmann"]) == ["Renate Hoffmann"]
    out = fio.write_pdf(data, [("Renate Hoffmann", "[Person_1]"), ("Hoffmann", "[Person_1]")])
    assert fio.verify_pdf(out, ["Renate Hoffmann", "Hoffmann"]) == []
