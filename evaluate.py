"""Misst die Erkennungsqualität gegen handmarkierte Testdaten.

Aufruf:  python evaluate.py [--config testdaten\\kanzlei\\config_eval.yaml] testdaten\\beispiel.jsonl  [weitere.jsonl ...]
Ohne --config gilt die persönliche config.yaml (eigene Allow-Liste!). Für die Kanzlei-Referenzfälle
die mitgelieferte config_eval.yaml nutzen, sonst zählt die fiktive Kanzlei als Fehlalarm.
Format je Zeile: {"text": "...", "spans": [[start, ende, "LABEL"], ...]}

Recall    = Anteil der sensiblen Stellen, die maskiert wurden (das Wichtigste!)
Precision = Anteil der Maskierungen, die wirklich sensibel waren
Ein Treffer zählt, wenn mindestens 50 % der markierten Zeichen abgedeckt sind.
Der Typ muss nicht stimmen – maskiert ist maskiert.
Namensteile (z. B. "Jutta" allein, wenn "Jutta Lange" markiert ist) zählen nicht als Fehlalarm,
werden aber gesondert ausgewiesen.
"""
import json
import sys
import time
from collections import defaultdict

import yaml

from anonymizer.engine import build_analyzer, detect


def coverage(gold, found):
    s, e = gold
    covered = sum(max(0, min(e, f.end) - max(s, f.start)) for f in found)
    return covered / max(1, e - s)


def main(paths):
    sys.stdout.reconfigure(encoding="utf-8")
    cfg_path = "config.yaml"
    if "--config" in paths:
        i = paths.index("--config")
        cfg_path = paths[i + 1]
        paths = paths[:i] + paths[i + 2:]
    cfg = yaml.safe_load(open(cfg_path, encoding="utf-8"))
    print(f"Konfiguration: {cfg_path}")
    t0 = time.time()
    analyzer = build_analyzer(cfg["spacy_model"], cfg.get("gliner_model") or None, cfg.get("gliner_threshold", 0.4))
    print(f"Modelle geladen in {time.time() - t0:.0f} s"
          + (f" (spaCy + GLiNER {cfg['gliner_model']})" if cfg.get("gliner_model") else " (spaCy)"))
    hit, total = defaultdict(int), defaultdict(int)
    fp_by_type, found_by_type = defaultdict(int), defaultdict(int)
    missed, false_pos, name_parts = [], [], []
    n_chars, t_detect = 0, 0.0

    for path in paths:
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            case = json.loads(line)
            text, gold = case["text"], case["spans"]
            gold_person_tokens = {w.strip(".,").lower() for s, e, lab in gold if lab == "PERSON"
                                  for w in text[s:e].split()}
            t1 = time.time()
            found = detect(analyzer, text, cfg["entities"], cfg["threshold"], cfg.get("allow_list"),
                           cfg.get("deny_list"), None, cfg.get("propagate_repeats", True),
                           cfg.get("include_name_parts", True), cfg.get("mask_locations", False),
                           cfg.get("keep_institutions", True))
            t_detect += time.time() - t1
            n_chars += len(text)
            for s, e, lab in gold:
                total[lab] += 1
                if coverage((s, e), found) >= 0.5:
                    hit[lab] += 1
                else:
                    missed.append((lab, text[s:e], case.get("datei", "")))
            for f in found:
                found_by_type[f.entity] += 1
                if not any(min(e, f.end) > max(s, f.start) for s, e, _ in gold):
                    if f.entity == "PERSON" and f.text.strip(".,").lower() in gold_person_tokens:
                        name_parts.append(f.text)
                    else:
                        fp_by_type[f.entity] += 1
                        false_pos.append((f.entity, f.text, f.quelle, case.get("datei", "")))

    print(f"\n{'Typ':<20}{'erkannt':>8}{'gesamt':>8}{'Recall':>8}")
    for lab in sorted(total):
        print(f"{lab:<20}{hit[lab]:>8}{total[lab]:>8}{hit[lab] / total[lab]:>8.0%}")
    all_hit, all_tot = sum(hit.values()), sum(total.values())
    print(f"{'GESAMT':<20}{all_hit:>8}{all_tot:>8}{all_hit / max(1, all_tot):>8.0%}")

    n_found, fp = sum(found_by_type.values()), sum(fp_by_type.values())
    n_real = n_found - len(name_parts)
    print(f"\n{'Treffer-Typ':<20}{'gesamt':>8}{'falsch':>8}{'Precision':>10}")
    for lab in sorted(found_by_type):
        n, bad = found_by_type[lab], fp_by_type[lab]
        print(f"{lab:<20}{n:>8}{bad:>8}{(n - bad) / max(1, n):>10.0%}")
    print(f"\nPrecision: {(n_real - fp) / max(1, n_real):.0%}  ({fp} Fehlalarme bei {n_real} Treffern; "
          f"{len(name_parts)} Namensteile nicht mitgezählt)")
    print(f"Tempo: {t_detect:.1f} s für {n_chars:,} Zeichen ({t_detect / max(1, n_chars) * 1000:.2f} s je 1.000)")
    if missed:
        print("\nÜbersehen:")
        for lab, t, datei in missed:
            print(f"  [{lab}] {t}" + (f"   ({datei})" if datei else ""))
    if false_pos:
        print("\nFehlalarme:")
        for lab, t, quelle, datei in false_pos:
            print(f"  [{lab}] {t}   <{quelle}>" + (f" ({datei})" if datei else ""))
    if name_parts:
        print("\nNamensteile (ok, nicht in Referenz markiert): " + ", ".join(sorted(set(name_parts))))


if __name__ == "__main__":
    main(sys.argv[1:] or ["testdaten/beispiel.jsonl"])
