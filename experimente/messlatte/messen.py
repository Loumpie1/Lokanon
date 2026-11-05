"""Alle Messlatten in einem Lauf: eigene Sammlungen und öffentliche Datensätze, mit einmal geladenen Modellen.

    python experimente/messlatte/messen.py NAME [--sets korpus,pruefung,...] [--gegen NAME] [--alt-gliner]
                                           [--ohne-gliner] [--eigenes-modell PFAD] [--ner-schwelle 0.5]

Ergebnisse unter experimente/messlatte/ergebnisse/NAME.json. Sammlungen:
- korpus, pruefung, kanzlei: erfundene Dokumente im Projekt (pruefung nie zum Nachbessern verwenden)
- grascco_train, ler_dev: Entwicklung an öffentlichen Daten (Fehleranalyse erlaubt)
- grascco_test, ler_test: nur zum Messen, keine Fehleranalyse
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

import evaluate as E  # noqa: E402
from anonymizer import engine  # noqa: E402

HIER = Path(__file__).parent
DATEN = Path(os.environ.get("LOKANON_MESSDATEN", Path.home() / "Lokanon" / "messdaten"))
SETS = {"korpus": ROOT / "testdaten/korpus/referenz.jsonl", "pruefung": ROOT / "testdaten/pruefung/referenz.jsonl",
        "kanzlei": ROOT / "testdaten/kanzlei/referenz_markierungen.jsonl",
        "grascco_train": DATEN / "grascco_train.jsonl", "ler_dev": DATEN / "ler_train.jsonl",
        "grascco_test": DATEN / "grascco_test.jsonl", "ler_test": DATEN / "ler_test.jsonl"}
STANDARD = ["korpus", "pruefung", "kanzlei", "grascco_train", "ler_dev"]
LER_DEV_N = 60  # Ausschnitt aus dem LER-Trainingsteil, damit ein Lauf in Minuten fertig ist


def faelle(name):
    f = list(E.lade_faelle([SETS[name]]))
    return f[:LER_DEV_N] if name == "ler_dev" else f


def main(args):
    sys.stdout.reconfigure(encoding="utf-8")
    name = args[0]
    sets = STANDARD
    gegen = None
    if "--sets" in args:
        sets = args[args.index("--sets") + 1].split(",")
    if "--gegen" in args:
        gegen = json.load(open(HIER / "ergebnisse" / (args[args.index("--gegen") + 1] + ".json"), encoding="utf-8"))
    if "--alt-gliner" in args:
        engine.GLINER_NUR_BEKANNTE = False
    cfg = yaml.safe_load(open(ROOT / "testdaten/kanzlei/config_eval.yaml", encoding="utf-8"))
    if "--eigenes-modell" in args:
        cfg["ner_modell"] = args[args.index("--eigenes-modell") + 1]
    if "--ner-schwelle" in args:
        cfg["ner_schwelle"] = float(args[args.index("--ner-schwelle") + 1])
    an = E.analyzer_fuer(cfg, "--ohne-gliner" in args)
    ziel = HIER / "ergebnisse" / f"{name}.json"
    alle = json.load(open(ziel, encoding="utf-8")) if ziel.exists() else {}
    for s in sets:
        t0 = time.time()
        r = E.auswerten(an, cfg, faelle(s))
        alle[s] = r
        g = r["gesamt"]
        zeile = (f"{s:<15} Recall {g['recall']:6.1%}  Precision {g['precision']:6.1%}  übersehen {g['total'] - g['hit']:4d}"
                 f"  Fehlalarme {g['fp']:4d}  ({time.time() - t0:.0f} s)")
        if gegen and s in gegen:
            b = gegen[s]["gesamt"]
            zeile += (f"   Δ Recall {(g['recall'] - b['recall']) * 100:+.1f}  Δ Precision "
                      f"{(g['precision'] - b['precision']) * 100:+.1f}")
        print(zeile, flush=True)
        with open(ziel, "w", encoding="utf-8") as fh:
            json.dump(alle, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
