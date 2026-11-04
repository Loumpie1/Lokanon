"""Zweitprüfer im Ganzen messen: Erkennung wie im Produkt, danach verwirft das Prüfmodell Namens- und
Firmenvorschläge (aus Modell oder Heuristik), die es für falsch hält. Weitergaben desselben Texts fallen mit weg.

Gemessen mit denselben Zählregeln wie evaluate.py, für die normalen und für niedrigere Schwellen.

    python experimente/zweitpruefer/messen.py [schwelle_zweitpruefer ...]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402
import yaml  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402

import evaluate as E  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from beispiele import GEPRUEFT, QUELLEN, umgebung  # noqa: E402
from trainieren import ART, MAX_LEN, MODELL  # noqa: E402

SAMMLUNGEN = {"pruefung": ROOT / "testdaten/pruefung/referenz.jsonl",
              "kanzlei": ROOT / "testdaten/kanzlei/referenz_markierungen.jsonl",
              "korpus": ROOT / "testdaten/korpus/referenz.jsonl"}
WEITERGABE = {"wiederholung", "namensteil", "vorgang"}


def main():
    schwellen = [float(a) for a in sys.argv[1:]] or [0.5]
    tok = AutoTokenizer.from_pretrained(MODELL)
    model = AutoModelForSequenceClassification.from_pretrained(MODELL).eval()
    cfg = yaml.safe_load(open(ROOT / "testdaten/kanzlei/config_eval.yaml", encoding="utf-8"))
    laeufe = {"normal": cfg, "niedrig": {**cfg, "threshold": 0.25, "gliner_threshold": 0.3}}
    ergebnis, verworfen = {}, []
    for lauf, c in laeufe.items():
        an = E.analyzer_fuer(c)
        for sname, pfad in SAMMLUNGEN.items():
            faelle = list(E.lade_faelle([pfad]))
            roh = {case["text"]: _ORIGINAL(an, c, case["text"]) for case in faelle}
            p = {}
            for text, fs in roh.items():
                pruef = [f for f in fs if f.entity in GEPRUEFT and f.quelle in QUELLEN]
                if not pruef:
                    continue
                with torch.no_grad():
                    enc = tok([f"{ART[f.entity]}: {f.text}" for f in pruef],
                              [umgebung(text, f.start, f.end) for f in pruef],
                              truncation="only_second", max_length=MAX_LEN, padding=True, return_tensors="pt")
                    wk = torch.softmax(model(**enc).logits, -1)[:, 1].tolist()
                for f, x in zip(pruef, wk):
                    p[(text, f.start, f.end, f.entity)] = x
            for s in [None] + schwellen:
                def gefiltert(text, fs):
                    if s is None:
                        return fs
                    weg = [f for f in fs if p.get((text, f.start, f.end, f.entity), 1.0) < s]
                    weg_t = {f.text.lower() for f in weg}
                    bleibt = [f for f in fs if f not in weg]
                    halten = {f.text.lower() for f in bleibt if f.quelle not in WEITERGABE}
                    return [f for f in bleibt if not (f.quelle in WEITERGABE and f.text.lower() in weg_t - halten)]
                gef = {t: gefiltert(t, fs) for t, fs in roh.items()}
                E.detect_fall = lambda _a, _c, text: gef[text]
                r = E.auswerten(None, c, faelle)
                g = r["gesamt"]
                name = f"{lauf} " + ("ohne Zweitprüfer" if s is None else f"Zweitprüfer {s}")
                ergebnis[f"{sname}/{name}"] = {"recall": g["recall"], "precision": g["precision"], "fp": g["fp"],
                                               "uebersehen": r["uebersehen"], "fehlalarme": r["fehlalarme"]}
                print(f"{sname:<9}{name:<28} recall {g['recall']:.1%}  precision {g['precision']:.1%}  "
                      f"fehlalarme {g['fp']:3d}", flush=True)
                if s == schwellen[0]:
                    for t, fs in roh.items():
                        for f in fs:
                            x = p.get((t, f.start, f.end, f.entity))
                            if x is not None and x < s:
                                verworfen.append([sname, lauf, f.entity, f.text, round(x, 3)])
            E.detect_fall = _ORIGINAL
    with open(Path(__file__).parent / "daten/messung.json", "w", encoding="utf-8") as fh:
        json.dump({"ergebnis": ergebnis, "verworfen": verworfen}, fh, ensure_ascii=False, indent=1)
    print("\nVerworfen:", *verworfen, sep="\n  ")


_ORIGINAL = E.detect_fall

if __name__ == "__main__":
    main()
