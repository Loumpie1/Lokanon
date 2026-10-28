"""Erkennung v2: Befunde aus dem ersten Pilot-Testvorgang (gedrehte Scans, OCR-Müll, vorgangsweite Namen,
eigene Bezeichnungen). Die Texte hier sind fiktiv, aber nach den echten Mustern gebaut."""
import sys
from pathlib import Path

import pymupdf
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from anonymizer import files as fio
from anonymizer.engine import (Finding, bezeichnung_normieren, build_analyzer, deanonymize, detect, propagate_vorgang,
                               pseudonymize, replacement_pairs)
from anonymizer.ocr import ausrichtung, erkenne_seite

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def analyzer():
    return build_analyzer("de_core_news_lg")


@pytest.fixture(scope="module")
def cfg():
    return yaml.safe_load((ROOT / "testdaten/kanzlei/config_eval.yaml").read_text(encoding="utf-8"))


def _detect(analyzer, cfg, text, **kw):
    args = dict(entities=cfg["entities"], threshold=0.4, allow_list=cfg.get("allow_list"), deny_list=[],
                manual_terms=None, propagate_repeats=True, include_name_parts=True, mask_locations=False,
                keep_institutions=True)
    args.update(kw)
    return detect(analyzer, text, **args)


# ---------------------------------------------------------------- B4/B9: kein Müll als Person/Firma

def test_rollen_pronomen_und_substantive_sind_keine_namen(analyzer, cfg):
    t = ("Ihr Mandant hat den Anhänger nicht bezahlt. Die Einzelrichterin und der Beklagten-Vertreter erschienen.\n"
         "Die Justizbeschäftigte protokollierte. Kunden zahlen Netto. Rechnungs Datum: siehe Anlage. Bl. 12 I. III.\n"
         "Ihres Erachtens ist die Planenfarbe falsch. Geschäftsstelle des Gerichts. www.beispiel.de ist keine Person.")
    texte = {f.text for f in _detect(analyzer, cfg, t) if f.entity in ("PERSON", "ORGANIZATION")}
    for nicht in ("Ihr Mandant", "Ihr", "Ihres", "Anhänger", "Einzelrichterin", "Beklagten-Vertreter", "Justizbeschäftigte",
                  "Kunden", "Netto", "Rechnungs Datum", "Rechnungs", "Bl", "I.", "III.", "Planenfarbe", "Geschäftsstelle",
                  "www.beispiel.de"):
        assert nicht not in texte, nicht


def test_echte_namen_bleiben_erkannt(analyzer, cfg):
    t = ("Beklagte: Cornelia Günther, vertreten durch Rechtsanwalt Bleischwitz. Zeuge: Herr Tackenberg.\n"
         "Firma: Autohaus Krause GmbH, P+P Rental OHG ./. Günther")
    fs = _detect(analyzer, cfg, t)
    texte = {f.text for f in fs}
    assert {"Cornelia Günther", "Bleischwitz", "Tackenberg", "Autohaus Krause GmbH"} <= texte
    assert "P+P Rental OHG" in texte and not any("./." in x for x in texte)


def test_email_muss_at_haben_und_diktatzeichen(analyzer, cfg):
    t = "Ihre E-Mail-Anschrift lautet info@kanzlei-muster.de. Unser Zeichen: AN/DS, Ihr Zeichen: mü-ka"
    fs = _detect(analyzer, cfg, t)
    assert {f.text for f in fs if f.entity == "EMAIL_ADDRESS"} == {"info@kanzlei-muster.de"}
    assert "AN/DS" in {f.text for f in fs if f.entity == "DIKTATZEICHEN"}


def test_datum_in_worten(analyzer, cfg):
    t = ("Herr Weber ist am 3. Juni 1975 geboren.\nDie Parteien haben einen schriftlichen Vertrag geschlossen, "
         "der sehr umfangreich ist.\nDer Vertrag datiert vom 12. März 2024 und ist unstreitig.")
    fs = _detect(analyzer, cfg, t)
    daten = {f.text for f in fs if f.entity == "DATUM"}
    assert "3. Juni 1975" in daten and "12. März 2024" not in daten


def test_gegenseite_kontakt_wird_maskiert(analyzer, cfg):
    t = ("Rechtsanwalt\nRAe Bleischwitz & Schierer\nViolenstraße 13, 28195 Bremen\nTel:0421/321511;Fax 0421/321301\n"
         "Bankverbindung: Commerzbank Cuxhaven\nAmtsgericht Bremen, Domsheide 16, 28195 Bremen, Tel. 0421 361-0")
    fs = _detect(analyzer, cfg, t)
    texte = {f.text for f in fs}
    assert {"Violenstraße 13", "0421/321511", "0421/321301"} <= texte
    assert any(x.startswith("28195 Bremen") for x in texte)
    # Gericht samt Adresse und Telefon bleibt stehen (Abstandsregel), Bank ist Einrichtung
    assert "Domsheide 16" not in texte and "0421 361-0" not in texte and "Commerzbank Cuxhaven" not in texte


def test_zeilenlange_ocr_frisst_nicht_alles(analyzer, cfg):
    """Vor v2 blendete 'Landgericht' am Zeilenanfang jede Kontaktangabe in derselben Riesenzeile aus."""
    t = "Landgericht Bremen hat entschieden. " + "Der Mandant bestreitet dies ausdrücklich. " * 6 + \
        "Erreichbar unter Tel. 0421/32 15 11, Violenstraße 13, 28195 Bremen."
    texte = {f.text for f in _detect(analyzer, cfg, t)}
    assert "Violenstraße 13" in texte and "0421/32 15 11" in texte


def test_person_zwischen_einrichtung_und_adresse(analyzer, cfg):
    """Die Anschrift nach 'unser Mandant Moritz Günther' gehört zur Person, nicht zur Versicherung davor."""
    t = ("In der Sache Günther ./. Allianz Versicherungs-AG teilen wir mit, dass unser Mandant Moritz Günther, "
         "Violenstraße 13, 28195 Bremen, Tel. 0421 / 12 34 56, den Unfall erlitten hat.")
    texte = {f.text for f in _detect(analyzer, cfg, t)}
    assert {"Violenstraße 13", "28195 Bremen", "0421 / 12 34 56"} <= texte
    # Ohne Person dazwischen bleibt die Anschrift der Einrichtung stehen
    t2 = "Beklagte: Allianz Versicherungs-AG, Königinstraße 28, 80802 München, Tel. 089 / 38 00 0."
    texte2 = {f.text for f in _detect(analyzer, cfg, t2)}
    assert not {"Königinstraße 28", "80802 München"} & texte2


# ---------------------------------------------------------------- B1/B7: vorgangsweit und Nachnamen

def test_propagation_ueber_dateien(analyzer, cfg):
    a = "Mandant: Moritz Günther, Bremer Straße 115a, 27211 Bassum."
    b = "Betreff: P+P Rental OHG ./. Günther, unser Az: 602/25. Der Käufer Günther zahlte nicht."
    fa = _detect(analyzer, cfg, a)
    fb = _detect(analyzer, cfg, b)
    fa2, fb2 = propagate_vorgang([a, b], [fa, fb], cfg.get("allow_list"))
    assert "Günther" in {f.text for f in fb2 if f.entity == "PERSON"}
    assert sum(1 for f in fb2 if f.text == "Günther") == 2
    mapping = {}
    for t, fs in ((a, fa2), (b, fb2)):
        res = pseudonymize(t, fs, mapping)
        mapping = res.mapping
    assert "Günther" not in res.anonymized and res.anonymized.count("[PERSON_1]") == 2


def test_nachname_gehoert_zur_haeufigeren_person():
    t = "Moritz Günther kam. Moritz Günther ging. Cornelia Günther blieb. Herr Günther zahlte."
    fs = [Finding(0, 14, "PERSON", 0.9, "Moritz Günther"), Finding(20, 34, "PERSON", 0.9, "Moritz Günther"),
          Finding(41, 57, "PERSON", 0.9, "Cornelia Günther"), Finding(70, 77, "PERSON", 0.01, "Günther")]
    res = pseudonymize(t, fs)
    assert res.mapping == {"PERSON_1": "Moritz Günther", "PERSON_2": "Cornelia Günther"}
    assert res.anonymized.endswith("Herr [PERSON_1] zahlte.")


# ---------------------------------------------------------------- B10: eigene Bezeichnungen

def test_eigene_bezeichnungen_ueberall():
    t = "Hans Müller traf Petra Schmidt. Müller lachte."
    fs = [Finding(0, 11, "PERSON", 0.9, "Hans Müller"), Finding(17, 30, "PERSON", 0.9, "Petra Schmidt"),
          Finding(32, 38, "PERSON", 0.01, "Müller")]
    res = pseudonymize(t, fs, bezeichnungen={"PERSON_1": "Mandant", "PERSON_2": "Zeugin Schmidt"})
    assert res.anonymized == "[MANDANT] traf [ZEUGIN_SCHMIDT]. [MANDANT] lachte."
    assert bezeichnung_normieren("Zeuge Günther") == "ZEUGE_GUENTHER"
    pairs = dict(replacement_pairs(t, fs, res.mapping, {"PERSON_1": "Mandant"}))
    assert pairs["Hans Müller"] == "[MANDANT]" and pairs["Müller"] == "[MANDANT]" and pairs["Petra Schmidt"] == "[PERSON_2]"
    back = deanonymize("Der [MANDANT] und [Zeugin Schmidt] sowie Mandant und [PERSON_2].", res.mapping,
                       {"PERSON_1": "Mandant", "PERSON_2": "Zeugin Schmidt"})
    assert back == "Der Hans Müller und Petra Schmidt sowie Hans Müller und Petra Schmidt."


# ---------------------------------------------------------------- B2: gedrehter Scan

@pytest.fixture(scope="module")
def gedrehter_scan(tmp_path_factory):
    src = pymupdf.open(ROOT / "testdaten/kanzlei/Fall4_Verkehrsrecht_Einspruch_Bussgeld_Engel.pdf")
    pix = src[0].get_pixmap(matrix=pymupdf.Matrix(200 / 72, 200 / 72).prerotate(90))  # Seite liegt quer
    out = pymupdf.open()
    page = out.new_page(width=src[0].rect.height, height=src[0].rect.width)
    page.insert_image(page.rect, pixmap=pix)
    p = tmp_path_factory.mktemp("scan") / "gedreht.pdf"
    out.save(p, garbage=4, deflate=True)
    return p.read_bytes()


def test_ausrichtung_erkannt(gedrehter_scan):
    page = pymupdf.open(stream=gedrehter_scan, filetype="pdf")[0]
    rot, _ = ausrichtung(page)
    assert rot in (90, 270)
    seite = erkenne_seite(page)
    assert seite.zeilen >= 10 and "Dr. Claudia Engel" in seite.text and "Moltkestraße 15" in seite.text


def test_gedrehter_scan_wird_aufrecht_geschwaerzt(gedrehter_scan):
    text, info = fio.read_document("gedreht.pdf", gedrehter_scan)
    assert info["ocr_seiten"] == 1 and "Dr. Claudia Engel" in text
    pairs = [("Dr. Claudia Engel", "[PERSON_1]"), ("Engel", "[PERSON_1]"), ("J010B7XY351", "[FUEHRERSCHEIN_1]"),
             ("Moltkestraße 15", "[ADRESSE_1]"), ("45138 Essen", "[ORT_1]")]
    out = fio.write_pdf(gedrehter_scan, pairs)
    d = pymupdf.open(stream=out, filetype="pdf")
    assert d[0].rect.width < d[0].rect.height  # wieder hochkant
    seite = erkenne_seite(d[0], rotation=0)
    low = seite.text.lower()
    assert "engel" not in low and "j010b7xy351" not in low and seite.zeilen >= 10
    assert fio.verify_pdf(out, [o for o, _ in pairs]) == []
