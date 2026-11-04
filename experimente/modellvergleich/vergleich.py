"""Fertige PII-Modelle gegen das jetzige GLiNER-Modell messen, auf Testsammlung, Prüfsammlung und Kanzleifällen.

spaCy, Regeln, Felder und alle Filter bleiben gleich; ausgetauscht wird nur das zweite Modell. Die Erkenner
heißen "GLiNERRecognizer", damit engine.detect ihre Treffer als quelle "modell" mit denselben Filtern behandelt.

    python experimente/modellvergleich/vergleich.py [variante ...]
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402
from presidio_analyzer import EntityRecognizer, RecognizerResult  # noqa: E402

import evaluate as E  # noqa: E402
from anonymizer.engine import build_analyzer  # noqa: E402

HIER = Path(__file__).parent
SAMMLUNGEN = {"korpus": ROOT / "testdaten/korpus/referenz.jsonl",
              "pruefung": ROOT / "testdaten/pruefung/referenz.jsonl",
              "kanzlei": ROOT / "testdaten/kanzlei/referenz_markierungen.jsonl"}

NOBODY = {"person": ("PERSON", 0.5), "address": ("ADRESSE", 0.05), "date of birth": ("DATUM", 0.5),
          "organization": ("ORGANIZATION", 0.5)}
G2 = {"person": "PERSON", "address": "ADRESSE", "date_of_birth": "DATUM", "email": "EMAIL_ADDRESS",
      "phone_number": "TELEFON", "iban": "IBAN_CODE", "bank_account": "KONTONUMMER", "tax_id": "DE_TAX_ID",
      "tax_number": "DE_TAX_NUMBER", "national_id_number": "DE_ID_CARD", "passport_number": "DE_PASSPORT",
      "drivers_license_number": "FUEHRERSCHEIN", "payment_card": "CREDIT_CARD", "ip_address": "IP_ADDRESS",
      "account_id": "KENNNUMMER", "government_id": "KENNNUMMER"}


def _abschnitte(text, groesse=1000, ueberlapp=100):
    s = 0
    while s < len(text):
        yield s, text[s:s + groesse]
        if s + groesse >= len(text):
            break
        s += groesse - ueberlapp


class _Modell(EntityRecognizer):
    """Gemeinsamer Rahmen: Text in Abschnitte teilen, Treffer je Label mit eigener Schwelle übernehmen."""

    def __init__(self, labels):  # labels: {modell_label: (entität, schwelle)}
        self.labels = labels
        super().__init__(supported_entities=sorted({e for e, _ in labels.values()}), name="GLiNERRecognizer",
                         supported_language="de")

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None):
        out, gesehen = [], set()
        for off, stueck in _abschnitte(text):
            for lab, s, e, score in self._treffer(stueck):
                ent, schwelle = self.labels[lab]
                k = (off + s, off + e, ent)
                if score >= schwelle and ent in entities and k not in gesehen:
                    gesehen.add(k)
                    out.append(RecognizerResult(ent, off + s, off + e, float(score)))
        return out


class Gliner1(_Modell):
    def __init__(self, modell, labels):
        from gliner import GLiNER
        self.m = GLiNER.from_pretrained(modell, map_location="cpu")
        super().__init__(labels)

    def _treffer(self, text):
        schwelle = min(s for _, s in self.labels.values())
        for t in self.m.predict_entities(text, list(self.labels), threshold=schwelle):
            yield t["label"], t["start"], t["end"], t["score"]


class Gliner2(_Modell):
    def __init__(self, modell, labels):
        from gliner2 import GLiNER2
        self.m = GLiNER2.from_pretrained(modell)
        super().__init__(labels)

    def _treffer(self, text):
        schwelle = min(s for _, s in self.labels.values())
        r = self.m.extract_entities(text, list(self.labels), threshold=schwelle, include_confidence=True,
                                    include_spans=True)
        for lab, liste in r["entities"].items():
            for t in liste:
                yield lab, t["start"], t["end"], t["confidence"]


def varianten(cfg):
    return {
        "jetzt (urchade)": lambda: build_analyzer(cfg["spacy_model"], cfg["gliner_model"], 0.5),
        "nobody-pii-de, unsere Labels": lambda: build_analyzer(cfg["spacy_model"], "naeyn/nobody-pii-de", 0.5),
        "nobody-pii-de, eigene Labels": lambda: mit(cfg, Gliner1("naeyn/nobody-pii-de", NOBODY)),
        "GLiNER2-PII": lambda: mit(cfg, Gliner2("fastino/gliner2-privacy-filter-PII-multi",
                                                 {k: (v, 0.5) for k, v in G2.items()})),
        "GLiNER2-PII + Firma": lambda: mit(cfg, Gliner2("fastino/gliner2-privacy-filter-PII-multi",
                                                         {**{k: (v, 0.5) for k, v in G2.items()},
                                                          "company": ("ORGANIZATION", 0.5)})),
    }


def mit(cfg, erkenner):
    an = build_analyzer(cfg["spacy_model"], None)
    an.registry.add_recognizer(erkenner)
    return an


def main():
    cfg = yaml.safe_load(open(ROOT / "testdaten/kanzlei/config_eval.yaml", encoding="utf-8"))
    wahl = sys.argv[1:]
    ziel = HIER / "ergebnisse.json"
    alle = json.load(open(ziel, encoding="utf-8")) if ziel.exists() else {}
    for name, bauen in varianten(cfg).items():
        if wahl and not any(w.lower() in name.lower() for w in wahl):
            continue
        t0 = time.time()
        an = bauen()
        laden = time.time() - t0
        erg = {"laden_s": laden}
        for sname, pfad in SAMMLUNGEN.items():
            r = E.auswerten(an, cfg, list(E.lade_faelle([pfad])))
            erg[sname] = {"gesamt": r["gesamt"], "familien": r["familien"], "tempo_s_je_1000": r["tempo_s_je_1000"],
                          "uebersehen": r["uebersehen"], "fehlalarme": r["fehlalarme"]}
            g = r["gesamt"]
            print(f"{name:<32}{sname:<10} recall {g['recall']:.1%}  precision {g['precision']:.1%}  "
                  f"fehlalarme {g['fp']:3d}  {r['tempo_s_je_1000']:.2f} s/1000 Zeichen", flush=True)
        alle[name] = erg
        with open(ziel, "w", encoding="utf-8") as fh:
            json.dump(alle, fh, ensure_ascii=False, indent=1)
        del an


if __name__ == "__main__":
    main()
