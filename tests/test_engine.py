"""Tests für Erkennung, Pseudonymisierung, Rückübersetzung und Vorgang.

Aufruf (aus dem Projektordner, im venv):  python -m pytest tests -q
Die Modelltests laden spaCy (ca. 5 s); GLiNER wird hier nicht geladen.
"""
import json
import re
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from anonymizer.engine import (Finding, build_analyzer, deanonymize, detect, make_allow_matcher, pseudonymize,
                               replacement_pairs)
from anonymizer.vault import decrypt_mapping, encrypt_mapping
from anonymizer.vorgang import (Vorgang, dateien_im_ordner, ist_cloud_pfad, ki_dateiname, mapping_aus_schluessel,
                                pruefbericht_html)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def analyzer():
    return build_analyzer("de_core_news_lg")


@pytest.fixture(scope="module")
def cfg():
    # Testkonfiguration mit der fiktiven Kanzlei auf der Allow-Liste – unabhängig von der persönlichen config.yaml
    return yaml.safe_load((ROOT / "testdaten/kanzlei/config_eval.yaml").read_text(encoding="utf-8"))


def _detect(analyzer, cfg, text, **kw):
    args = dict(entities=cfg["entities"], threshold=0.4, allow_list=cfg.get("allow_list"), deny_list=[],
                manual_terms=None, propagate_repeats=True, include_name_parts=True, mask_locations=False,
                keep_institutions=True)
    args.update(kw)
    return detect(analyzer, text, **args)


# ---------------------------------------------------------------- Rückübersetzung

def test_deanonymize_varianten():
    m = {"Person_1": "Hans Müller", "Firma_2": "Muster GmbH"}
    assert deanonymize("Hallo [Person_1] von [Firma_2].", m) == "Hallo Hans Müller von Muster GmbH."
    assert deanonymize("Person_1 und Person 1 und [Person-1]s Auto", m) == "Hans Müller und Hans Müller und Hans Müllers Auto"
    assert deanonymize("«Person_1» · [ Firma_2 ]", m) == "Hans Müller · Muster GmbH"
    assert deanonymize("Person_1s Anspruch", m) == "Hans Müllers Anspruch"
    assert deanonymize("[Person_9] bleibt", m) == "[Person_9] bleibt"
    assert deanonymize("nichts", {}) == "nichts"


def test_vault_roundtrip():
    m = {"Person_1": "Hans Müller", "Ort_1": "45468 Mülheim an der Ruhr"}
    blob = encrypt_mapping(m, "geheim")
    assert decrypt_mapping(blob, "geheim") == m
    with pytest.raises(ValueError):
        decrypt_mapping(blob, "falsch")
    assert mapping_aus_schluessel({"vorgang": "x", "mapping": m}) == m
    assert mapping_aus_schluessel(m) == m


# ---------------------------------------------------------------- Pseudonymisierung

def test_pseudonymize_namensteile_und_genitiv():
    t = "Hans Müller kam. Müller ging. Müllers Auto blieb. Hans auch."
    fs = [Finding(0, 11, "PERSON", 0.9, "Hans Müller"), Finding(17, 23, "PERSON", 0.01, "Müller"),
          Finding(30, 37, "PERSON", 0.01, "Müllers"), Finding(50, 54, "PERSON", 0.01, "Hans")]
    res = pseudonymize(t, fs)
    assert res.mapping == {"Person_1": "Hans Müller"}
    assert res.anonymized == "[Person_1] kam. [Person_1] ging. [Person_1] Auto blieb. [Person_1] auch."


def test_pseudonymize_fortsetzung_mapping():
    """Zweites Dokument im selben Vorgang: bekannte Person behält Nummer, neue Person zählt weiter."""
    m = {"Person_1": "Hans Müller"}
    t = "Müller traf Petra Schmidt."
    fs = [Finding(0, 6, "PERSON", 0.5, "Müller"), Finding(12, 25, "PERSON", 0.9, "Petra Schmidt")]
    res = pseudonymize(t, fs, m)
    assert res.anonymized == "[Person_1] traf [Person_2]."
    assert res.mapping["Person_2"] == "Petra Schmidt"


def test_replacement_pairs_namensteil():
    t = "Hans Müller und Müller"
    fs = [Finding(0, 11, "PERSON", 0.9, "Hans Müller"), Finding(16, 22, "PERSON", 0.01, "Müller")]
    res = pseudonymize(t, fs)
    pairs = replacement_pairs(t, fs, res.mapping)
    assert pairs == [("Hans Müller", "[Person_1]"), ("Müller", "[Person_1]")]


# ---------------------------------------------------------------- Allow-Liste

def test_allow_matcher_namensteile():
    allowed = make_allow_matcher(["Lehmkuhl & Partner", "Annette Lehmkuhl", "0201 8945120"])
    for s in ("Lehmkuhl & Partner Rechtsanwälte", "Dr. Lehmkuhl", "A. Lehmkuhl", "Frau Annette Lehmkuhl", "lehmkuhl",
              "0201 8945120"):
        assert allowed(s), s
    for s in ("Hans Müller", "Partnerschaft Müller", "0201 8945121"):
        assert not allowed(s), s


# ---------------------------------------------------------------- Erkennung (Modell)

def test_detect_kanzlei_basics(analyzer, cfg):
    t = ("Mandant: Kevin Schulte, geb. 22.09.1993, Moltkestraße 15, 45138 Essen, Tel. 0201 123456.\n"
         "Aktenzeichen: 14 VI 512/26. Kennzeichen MH-KS 1993, FIN: WVWZZZCDZMW123456.\n"
         "Versicherungsschein-Nr. RS-4417-882031. IBAN DE89 3704 0044 0532 0130 00.\n"
         "Nachlassgericht: Amtsgericht Essen, Zweigertstraße 52, 45130 Essen. Essen, 21.10.2026")
    fs = _detect(analyzer, cfg, t)
    texte = {f.text for f in fs}
    for muss in ("Kevin Schulte", "22.09.1993", "Moltkestraße 15", "45138 Essen", "0201 123456", "14 VI 512/26",
                 "MH-KS 1993", "WVWZZZCDZMW123456", "RS-4417-882031"):
        assert muss in texte, muss
    assert any("DE89" in x for x in texte)
    # Gericht samt Adresse und Briefkopf-Datum bleiben stehen
    assert "Amtsgericht Essen" not in texte
    assert "Zweigertstraße 52" not in texte
    assert "21.10.2026" not in texte


def test_detect_feldbezeichner_und_eigene_kanzlei(analyzer, cfg):
    t = ("Lehmkuhl & Partner Rechtsanwälte\nBetreff: Mandatsnotiz\nFIN: ABC\nFührerschein-Nr.: J010B7XY351\n"
         "Mit freundlichen Grüßen\nDr. Annette Lehmkuhl, Rechtsanwältin")
    fs = _detect(analyzer, cfg, t)
    texte = {f.text for f in fs}
    assert "J010B7XY351" in texte
    for nicht in ("Mandatsnotiz", "FIN", "Führerschein-Nr", "Lehmkuhl & Partner", "Dr. Annette Lehmkuhl", "Lehmkuhl"):
        assert nicht not in texte, nicht


def test_detect_titel_und_unterschrift(analyzer, cfg):
    t = "Laut Hausarzt Dr. Michael Essen lag eine Demenz vor.\n\nViele Grüße\nWolle (Wolfgang Rhein)"
    fs = _detect(analyzer, cfg, t)
    texte = {f.text for f in fs}
    assert "Dr. Michael Essen" in texte
    assert "Wolle" in texte
    assert "Wolfgang Rhein" in texte


def test_detect_datum_modus(analyzer, cfg):
    # Kontextfenster von Presidio: 5 Wörter davor, 6 danach – deshalb Abstand zwischen den Sätzen
    t = ("Der Mandant ist geboren am 01.02.1980 in Essen.\n"
         "Die Parteien haben einen schriftlichen Vertrag geschlossen, der sehr umfangreich ist.\n"
         "Der Vertrag datiert vom 03.04.2020 und wurde notariell beurkundet.")
    k = {f.text for f in _detect(analyzer, cfg, t, datum_modus="kontext")}
    a = {f.text for f in _detect(analyzer, cfg, t, datum_modus="alle")}
    n = {f.text for f in _detect(analyzer, cfg, t, datum_modus="keine")}
    assert "01.02.1980" in k and "03.04.2020" not in k
    assert {"01.02.1980", "03.04.2020"} <= a
    assert not any("20" in x for x in n)


def test_evaluate_referenz(analyzer, cfg):
    """Qualitätsschwelle auf den Kanzleifällen (ohne GLiNER): Recall >= 90 %, Precision >= 85 %."""
    hit = tot = fp = n = 0
    for line in (ROOT / "testdaten/kanzlei/referenz_markierungen.jsonl").read_text(encoding="utf-8").splitlines():
        c = json.loads(line)
        text, gold = c["text"], [g for g in c["spans"] if g[2] != "INDIREKT"]
        fs = _detect(analyzer, cfg, text)
        gold_tokens = {w.strip(".,").lower() for s, e, lab in gold if lab == "PERSON" for w in text[s:e].split()}
        for s, e, lab in gold:
            tot += 1
            cov = sum(max(0, min(e, f.end) - max(s, f.start)) for f in fs) / max(1, e - s)
            hit += cov >= 0.5
        for f in fs:
            if f.entity == "PERSON" and f.text.strip(".,").lower() in gold_tokens:
                continue
            n += 1
            fp += not any(min(e, f.end) > max(s, f.start) for s, e, _ in gold)
    assert hit / tot >= 0.90, f"Recall {hit / tot:.0%}"
    assert (n - fp) / n >= 0.85, f"Precision {(n - fp) / n:.0%}"


def test_leck_test_markdown(analyzer, cfg):
    """Kein aktiver Treffer darf im anonymisierten Text übrig bleiben (Wortgrenzen)."""
    for line in (ROOT / "testdaten/kanzlei/referenz_markierungen.jsonl").read_text(encoding="utf-8").splitlines():
        c = json.loads(line)
        fs = _detect(analyzer, cfg, c["text"])
        out = pseudonymize(c["text"], fs).anonymized
        for f in fs:
            assert not re.search(rf"(?<!\w){re.escape(f.text)}(?!\w)", out, re.IGNORECASE), (c["datei"], f.text)


# ---------------------------------------------------------------- Vorgang

def test_ki_dateiname():
    pairs = [("Gerhard Brinkhoff", "[Person_2]"), ("Brinkhoff", "[Person_2]"), ("Person", "[Person_26]")]
    assert ki_dateiname("Fall1_Erbrecht_Brinkhoff.docx", pairs) == "Fall1_Erbrecht_Person_2"
    assert ki_dateiname("Mandat Hans Müller 2026.pdf", [("Hans Müller", "[Person_1]")]) == "Mandat Person_1 2026"
    assert ki_dateiname("HansMueller_Unfall.pdf", [("Hans Mueller", "[Person_1]")]) == "Person_1_Unfall"
    assert ki_dateiname("Rechnung.pdf", pairs) == "Rechnung"


def test_vorgang_ablage():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "a.txt").write_text("x", encoding="utf-8")
    (tmp / "~$b.docx").write_text("x", encoding="utf-8")
    assert [p.name for p in dateien_im_ordner(tmp)] == ["a.txt"]
    assert ist_cloud_pfad(r"C:\Users\x\OneDrive\Akten") and not ist_cloud_pfad(str(tmp))
    # Ordner-Modus: Vorgangsordner = <Akte>/Lokanon
    v = Vorgang(name="Akte 1", ordner=str(tmp), mapping={"Person_1": "Hans Müller"})
    assert v.lege_basis_fest() == tmp / "Lokanon"
    v.schreibe("a.txt", b"Hallo [Person_1]", "md", "a")
    f = Finding(6, 17, "PERSON", 0.9, "Hans Müller")
    v.notiere_treffer("a.txt", [f], 16, True)
    v.schreibe_uebersicht()
    v.schreibe_protokoll()
    bericht = v.schreibe_pruefbericht(pruefbericht_html(v, [{"name": "a.txt", "text": "Hallo Hans Müller", "findings": [f],
                                                             "platzhalter": {(6, 17): "[Person_1]"}}]))
    k = v.speichere_schluessel("pw", tmp / "keys")
    assert (tmp / "Lokanon/Anonymisiert/a.md").read_bytes() == b"Hallo [Person_1]"
    assert (tmp / "Lokanon/Fuer die KI/a.md").exists()
    assert "Hans Müller" in bericht.read_text(encoding="utf-8") and "[Person_1]" in bericht.read_text(encoding="utf-8")
    prot = json.loads((tmp / "Lokanon/Protokoll.json").read_text(encoding="utf-8"))
    assert prot["dateien"][0]["treffer"] == {"Person": 1} and "Hans" not in json.dumps(prot)
    assert mapping_aus_schluessel(decrypt_mapping(k.read_bytes(), "pw")) == {"Person_1": "Hans Müller"}
    v.leere_ausgabe()
    assert not (tmp / "Lokanon/Anonymisiert/a.md").exists() and (tmp / "Lokanon/Fuer die KI").is_dir()
    # Upload-Modus: Vorgangsordner = <Vorgaenge>/<Name>, Originale werden gesichert
    v2 = Vorgang(name="Mandat Müller/2026")
    assert v2.lege_basis_fest(tmp / "Vorgaenge") == tmp / "Vorgaenge" / "Mandat Müller_2026"
    p = v2.sichere_original("brief.txt", b"Original")
    assert p == tmp / "Vorgaenge/Mandat Müller_2026/Originale/brief.txt" and p.read_bytes() == b"Original"
