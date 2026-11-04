"""Trainingsbeispiele für den Zweitprüfer (Namen und Firmen): Vorschlag + Umgebung -> anonymisieren ja/nein.

Quellen (Prüfsammlung und Kanzleifälle bleiben draußen, sie sind die Messlatte):
  1. Abwandlungen der Testsammlung (testdaten/korpus): Namen in den Goldstellen werden durch zufällige Namen
     aus den Wörterbuchlisten ersetzt. Die Lösung ist bekannt.
  2. Beispielsätze aus Wiktionary (kaikki.org, CC BY-SA): Hier entstehen typische Fehlvorschläge. Die Lösung
     liefert erst das lokale Sprachmodell (bewerten.py).

Erkannt wird mit niedrigen Schwellen, damit auch die Vorschläge vorkommen, die sonst knapp verworfen werden.

    python experimente/zweitpruefer/beispiele.py <wiktionary-substantive.jsonl> [<adjektive.jsonl>]
"""
import gzip
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

import evaluate as E  # noqa: E402
from anonymizer.engine import SALUTATIONS, TITLES  # noqa: E402

HIER = Path(__file__).parent
DATEN = HIER / "daten"
GEPRUEFT = {"PERSON", "ORGANIZATION"}
QUELLEN = {"modell", "heuristik"}
NIEDRIG = {"threshold": 0.25, "gliner_threshold": 0.3}
ABWANDLUNGEN = 25
WIKI_SAETZE = 5000
RAND = 120


def _liste(name):
    with gzip.open(ROOT / "anonymizer/daten" / f"{name}.txt.gz", "rt", encoding="utf-8") as fh:
        namen = {z.strip() for z in fh if z.strip()[:1].isupper() and z.strip().isalpha() and len(z.strip()) >= 3}
    return sorted(n for n in namen if not (n.endswith("s") and n[:-1] in namen))  # ohne Genitiv "Aarons"


def umgebung(text, s, e):
    """Ausschnitt um den Vorschlag, Vorschlag mit « » markiert, Zeilenumbrüche als ⏎."""
    a, b = max(0, s - RAND), min(len(text), e + RAND)
    aus = text[a:s] + "«" + text[s:e] + "»" + text[e:b]
    return re.sub(r"[ \t]+", " ", aus.replace("\n", " ⏎ ")).strip()


def kandidaten(an, cfg, text):
    for f in E.detect_fall(an, cfg, text):
        if f.entity in GEPRUEFT and f.quelle in QUELLEN:
            yield f


def abwandeln(case, vornamen, nachnamen, rnd):
    """Namen in PERSON/ORGANIZATION-Goldstellen konsistent ersetzen; Text und Goldstellen neu berechnen."""
    ersetzt = {}

    def neu(tok):
        if tok not in ersetzt:
            ersetzt[tok] = rnd.choice(vornamen if tok in VORNAMEN_SET else nachnamen)
        return ersetzt[tok]

    def tausch(wert):
        def ein(m):
            w = m.group()
            if w.lower().strip(".") in TITLES or w.lower() in SALUTATIONS or not w[0].isupper() or len(w) < 3:
                return w
            if w in VORNAMEN_SET or w in NACHNAMEN_SET or w in ersetzt:
                return neu(w)
            return w
        return re.sub(r"[A-Za-zÄÖÜäöüß]+", ein, wert)

    text, spans, pos, out = case["text"], sorted(case["spans"]), 0, []
    neu_text = []
    for s, e, lab in spans:
        if s < pos:
            continue
        neu_text.append(text[pos:s])
        wert = tausch(text[s:e]) if lab in GEPRUEFT else text[s:e]
        start = sum(len(x) for x in neu_text)
        neu_text.append(wert)
        out.append([start, start + len(wert), lab])
        pos = e
    neu_text.append(text[pos:])
    return {**case, "text": "".join(neu_text), "spans": out}


def label(case, f):
    zaehlt = [(s, e) for s, e, lab in case["spans"] if lab not in E.NICHT_GEZAEHLT]
    frei = [(s, e) for s, e, lab in case["spans"] if lab in E.NICHT_GEZAEHLT]
    if any(min(e, f.end) > max(s, f.start) for s, e in zaehlt):
        return 1
    if any(min(e, f.end) > max(s, f.start) for s, e in frei):
        return None
    return 0


def wiki_saetze(pfade, rnd):
    saetze = []
    for p in pfade:
        for z in open(p, encoding="utf-8"):
            d = json.loads(z)
            for s in d.get("senses", []):
                for ex in s.get("examples", []):
                    t = ex.get("text", "")
                    if 40 < len(t) < 400:
                        saetze.append(t)
    saetze = sorted(set(saetze))
    rnd.shuffle(saetze)
    return saetze[:WIKI_SAETZE]


VORNAMEN_SET, NACHNAMEN_SET = set(), set()


def main():
    global VORNAMEN_SET, NACHNAMEN_SET
    rnd = random.Random(11)
    vornamen, nachnamen = _liste("vornamen"), _liste("nachnamen")
    VORNAMEN_SET, NACHNAMEN_SET = set(vornamen), set(nachnamen)
    cfg = {**yaml.safe_load(open(ROOT / "testdaten/kanzlei/config_eval.yaml", encoding="utf-8")), **NIEDRIG}
    an = E.analyzer_fuer(cfg)
    DATEN.mkdir(exist_ok=True)

    gesehen, n = set(), 0
    with open(DATEN / "korpus_beispiele.jsonl", "w", encoding="utf-8") as fh:
        faelle = list(E.lade_faelle([ROOT / "testdaten/korpus/referenz.jsonl"]))
        for k in range(ABWANDLUNGEN):
            for case in faelle:
                c = abwandeln(case, vornamen, nachnamen, rnd) if k else case
                for f in kandidaten(an, cfg, c["text"]):
                    y = label(c, f)
                    eingabe = (f.entity, umgebung(c["text"], f.start, f.end))
                    if y is None or eingabe in gesehen:
                        continue
                    gesehen.add(eingabe)
                    fh.write(json.dumps({"quelle": "korpus", "datei": case["datei"], "abwandlung": k,
                                         "entity": f.entity, "text": f.text, "kontext": eingabe[1], "score": f.score,
                                         "herkunft": f.quelle, "label": y}, ensure_ascii=False) + "\n")
                    n += 1
            print(f"Abwandlung {k + 1}/{ABWANDLUNGEN}: {n} Beispiele", flush=True)

    n = 0
    with open(DATEN / "wiki_kandidaten.jsonl", "w", encoding="utf-8") as fh:
        for i, satz in enumerate(wiki_saetze(sys.argv[1:], rnd)):
            for f in kandidaten(an, cfg, satz):
                fh.write(json.dumps({"quelle": "wiki", "satz": i, "entity": f.entity, "text": f.text,
                                     "kontext": umgebung(satz, f.start, f.end), "satztext": satz, "score": f.score,
                                     "herkunft": f.quelle}, ensure_ascii=False) + "\n")
                n += 1
            if i % 500 == 499:
                print(f"Wiktionary {i + 1}: {n} Kandidaten", flush=True)


if __name__ == "__main__":
    main()
