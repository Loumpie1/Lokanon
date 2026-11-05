"""Kombi-Experiment: mehr Modelle vereinigen (spaCy + GLiNER + GLiNER2-PII), Schwellen senken und die zusätzlichen
Fehlalarme mit dem Zweitprüfer (experimente/zweitpruefer/modell) wieder herausfiltern.

    python experimente/kombi/kombi.py [--sets grascco_train,ler_dev,pruefung,kanzlei,korpus]

Varianten:
  jetzt          wie im Produkt (spaCy + GLiNER, Schwellen 0,4 / 0,5)
  +gliner2       zusätzlich GLiNER2-PII (Schwelle 0,5)
  +gliner2 tief  alle Schwellen gesenkt (0,25 / 0,3 / 0,3)
  … + zweit 0,3  Zweitprüfer verwirft Namens-/Firmenvorschläge aus Modell oder Heuristik unter p = 0,3
Ergebnisse in experimente/kombi/ergebnisse.json.
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
for unter in ("experimente/zweitpruefer", "experimente/modellvergleich", "experimente/messlatte"):
    sys.path.insert(0, str(ROOT / unter))

import torch  # noqa: E402
import yaml  # noqa: E402

import evaluate as E  # noqa: E402
import messen as M  # noqa: E402
from anonymizer.engine import build_analyzer  # noqa: E402

HIER = Path(__file__).parent
WEITERGABE = {"wiederholung", "namensteil", "vorgang", "firmenteil"}


def zweitpruefer():
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    import trainieren as Z

    tok = AutoTokenizer.from_pretrained(Z.MODELL)
    model = AutoModelForSequenceClassification.from_pretrained(Z.MODELL).eval()

    def filtern(text, fs, schwelle):
        from beispiele import GEPRUEFT, QUELLEN, umgebung

        pruef = [f for f in fs if f.entity in GEPRUEFT and f.quelle in QUELLEN]
        if not pruef:
            return fs
        p = []
        with torch.no_grad():
            for i in range(0, len(pruef), 32):
                teil = pruef[i:i + 32]
                enc = tok([f"{Z.ART[f.entity]}: {f.text}" for f in teil],
                          [Z.kontext_sauber(f.text, umgebung(text, f.start, f.end)) for f in teil],
                          truncation="only_second", max_length=Z.MAX_LEN, padding=True, return_tensors="pt")
                p += torch.softmax(model(**enc).logits, -1)[:, 1].tolist()
        weg = [f for f, x in zip(pruef, p) if x < schwelle]
        weg_t = {f.text.lower() for f in weg}
        bleibt = [f for f in fs if f not in weg]
        halten = {f.text.lower() for f in bleibt if f.quelle not in WEITERGABE}
        return [f for f in bleibt if not (f.quelle in WEITERGABE and f.text.lower() in weg_t - halten)]
    return filtern


def main(args):
    sys.stdout.reconfigure(encoding="utf-8")
    torch.set_num_threads(6)
    sets = args[args.index("--sets") + 1].split(",") if "--sets" in args else \
        ["grascco_train", "ler_dev", "pruefung", "kanzlei", "korpus"]
    cfg = yaml.safe_load(open(ROOT / "testdaten/kanzlei/config_eval.yaml", encoding="utf-8"))
    tief = {**cfg, "threshold": 0.25, "gliner_threshold": 0.3}
    from vergleich import G2, Gliner2

    def mit_g2(c, schwelle):
        an = build_analyzer(c["spacy_model"], c["gliner_model"], c["gliner_threshold"])
        an.registry.add_recognizer(Gliner2("fastino/gliner2-privacy-filter-PII-multi",
                                           {k: (v, schwelle) for k, v in G2.items()}))
        return an

    filtern = zweitpruefer()
    ziel = HIER / "ergebnisse.json"
    alle = json.load(open(ziel, encoding="utf-8")) if ziel.exists() else {}
    original = E.detect_fall
    for name, c, bauen in (("+gliner2", cfg, lambda: mit_g2(cfg, 0.5)), ("+gliner2 tief", tief, lambda: mit_g2(tief, 0.3))):
        an = bauen()
        for s in sets:
            faelle = M.faelle(s)
            t0 = time.time()
            roh = {case["text"]: original(an, c, case["text"]) for case in faelle}
            dauer = time.time() - t0
            for zs in (None, 0.3):
                gef = roh if zs is None else {t: filtern(t, fs, zs) for t, fs in roh.items()}
                E.detect_fall = lambda _a, _c, text, gef=gef: gef[text]
                r = E.auswerten(None, c, faelle)
                v = name + ("" if zs is None else f" + zweit {zs}")
                alle.setdefault(v, {})[s] = {"gesamt": r["gesamt"], "uebersehen": r["uebersehen"],
                                             "fehlalarme": r["fehlalarme"], "sekunden": dauer}
                g = r["gesamt"]
                print(f"{v:<26}{s:<15} Recall {g['recall']:6.1%}  Precision {g['precision']:6.1%}  "
                      f"übersehen {g['total'] - g['hit']:4d}  Fehlalarme {g['fp']:4d}  ({dauer:.0f} s)", flush=True)
            E.detect_fall = original
            with open(ziel, "w", encoding="utf-8") as fh:
                json.dump(alle, fh, ensure_ascii=False, indent=1)
        del an


if __name__ == "__main__":
    main(sys.argv[1:])
