"""Schritt 1 (Lokanon-venv): Treffer der normalen Erkennung für alle Testdokumente als JSON ablegen.

Zwei Läufe: mit den Schwellen aus config_eval.yaml ("normal") und mit niedrigeren Schwellen ("niedrig"),
damit der Zweitprüfer zeigen kann, ob er zusätzliche, sonst verworfene Treffer retten kann.

    python experimente/llm_zweitpruefer/kandidaten.py
"""
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

import evaluate as E  # noqa: E402

HIER = Path(__file__).parent
SAMMLUNGEN = {"korpus": ROOT / "testdaten/korpus/referenz.jsonl",
              "pruefung": ROOT / "testdaten/pruefung/referenz.jsonl",
              "kanzlei": ROOT / "testdaten/kanzlei/referenz_markierungen.jsonl"}
NIEDRIG = {"threshold": 0.25, "gliner_threshold": 0.3}


def main():
    cfg = yaml.safe_load(open(ROOT / "testdaten/kanzlei/config_eval.yaml", encoding="utf-8"))
    cfg_n = {**cfg, **NIEDRIG}
    normal, niedrig = E.analyzer_fuer(cfg), E.analyzer_fuer(cfg_n)
    out = []
    for name, pfad in SAMMLUNGEN.items():
        for case in E.lade_faelle([pfad]):
            case = {**case, "sammlung": name,
                    "normal": [asdict(f) for f in E.detect_fall(normal, cfg, case["text"])],
                    "niedrig": [asdict(f) for f in E.detect_fall(niedrig, cfg_n, case["text"])]}
            out.append(case)
            print(name, case.get("datei", ""), len(case["normal"]), len(case["niedrig"]), flush=True)
    (HIER / "ergebnisse").mkdir(exist_ok=True)
    with open(HIER / "ergebnisse/kandidaten.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)


if __name__ == "__main__":
    main()
