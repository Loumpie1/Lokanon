"""Misst die Erkennungsqualität gegen handmarkierte Testdaten.

Aufruf:  python evaluate.py [--config testdaten\\kanzlei\\config_eval.yaml] [--ohne-gliner] [--json ergebnis.json]
                            [--gegen basis.json] [--leise] [--eigene] [--klartext] testdaten\\beispiel.jsonl  [...]
--eigene nimmt die eigenen Testfälle aus geprüften Vorgängen dazu (Einstellungen → Erweitert, verschlüsselt im
Datenordner). Dann erscheinen übersehene Stellen und Fehlalarme nur mit Art und Länge, ohne Klartext, außer mit
--klartext.
Ohne --config gilt die persönliche config.yaml (eigene Allow-Liste!). Für die Kanzlei-Referenzfälle und die
Testsammlung (testdaten/korpus) die mitgelieferte config_eval.yaml nutzen, sonst zählt die fiktive Kanzlei als
Fehlalarm.
Format je Zeile: {"datei": "...", "familie": "...", "seiten": 1, "text": "...", "spans": [[start, ende, "LABEL"], ...],
                  "fehlend": [["LABEL", "Wert"], ...]}

Recall    = Anteil der sensiblen Stellen, die maskiert wurden (das Wichtigste!)
Precision = Anteil der Maskierungen, die wirklich sensibel waren
Ein Treffer zählt, wenn mindestens 50 % der markierten Zeichen abgedeckt sind.
Der Typ muss nicht stimmen – maskiert ist maskiert. Typfehler bei Person/Firma werden gesondert gezählt.
Namensteile (z. B. "Jutta" allein, wenn "Jutta Lange" markiert ist) zählen nicht als Fehlalarm,
werden aber gesondert ausgewiesen.
INDIREKT (Umschreibungen) und OPTIONAL (darf maskiert werden, muss aber nicht) zählen weder beim Recall noch als
Fehlalarm. "fehlend" sind markierte Werte, die im gelesenen Text nicht mehr auffindbar waren (z. B. von der
Texterkennung verstümmelt) – sie zählen als übersehen.
"""
import json
import sys
import time
from collections import defaultdict

import yaml

from anonymizer.engine import build_analyzer, detect

NICHT_GEZAEHLT = {"INDIREKT", "OPTIONAL"}
TYP_GRUPPEN = {"PERSON": "PERSON", "ORGANIZATION": "ORGANIZATION"}


def coverage(gold, found):
    s, e = gold
    covered = sum(max(0, min(e, f.end) - max(s, f.start)) for f in found)
    return covered / max(1, e - s)


def lade_faelle(paths):
    for path in paths:
        for line in open(path, encoding="utf-8"):
            if line.strip():
                yield json.loads(line)


def analyzer_fuer(cfg, ohne_gliner=False):
    return build_analyzer(cfg["spacy_model"], None if ohne_gliner else (cfg.get("gliner_model") or None),
                          cfg.get("gliner_threshold", 0.5), cfg.get("gliner_onnx_file", ""),
                          cfg.get("ner_modell", ""), cfg.get("ner_schwelle", 0.5))


def detect_fall(analyzer, cfg, text):
    return detect(analyzer, text, cfg["entities"], cfg.get("threshold", 0.4), cfg.get("allow_list"),
                  cfg.get("deny_list"), None, cfg.get("propagate_repeats", True), cfg.get("include_name_parts", True),
                  cfg.get("mask_locations", False), cfg.get("keep_institutions", True),
                  cfg.get("datum_modus", "kontext"))


def _leer():
    return {"hit": 0, "total": 0, "found": 0, "fp": 0, "namensteile": 0, "seiten": 0, "dokumente": 0}


def auswerten(analyzer, cfg, faelle) -> dict:
    """Wertet alle Fälle aus. Ergebnis ist JSON-fähig (für --json und den Vergleich mit einer Basislinie)."""
    gesamt, je_familie = _leer(), defaultdict(_leer)
    hit_typ, tot_typ = defaultdict(int), defaultdict(int)
    found_typ, fp_typ = defaultdict(int), defaultdict(int)
    missed, false_pos, name_parts, typfehler = [], [], [], []
    n_chars, t_detect = 0, 0.0

    for case in faelle:
        text, datei = case["text"], case.get("datei", "")
        fam = je_familie[case.get("familie", "kanzlei")]
        gold = [g for g in case["spans"] if g[2] not in NICHT_GEZAEHLT]
        frei = case["spans"]  # Treffer auf INDIREKT/OPTIONAL sind keine Fehlalarme
        gold_person_tokens = {w.strip(".,").lower() for s, e, lab in gold if lab == "PERSON"
                              for w in text[s:e].split()}
        t1 = time.time()
        found = detect_fall(analyzer, cfg, text)
        t_detect += time.time() - t1
        n_chars += len(text)
        for z in (gesamt, fam):
            z["dokumente"] += 1
            z["seiten"] += case.get("seiten", 1)
        for s, e, lab in gold:
            tot_typ[lab] += 1
            treffer = coverage((s, e), found) >= 0.5
            for z in (gesamt, fam):
                z["total"] += 1
                z["hit"] += treffer
            if treffer:
                hit_typ[lab] += 1
                if lab in TYP_GRUPPEN:
                    typen = {f.entity for f in found if min(e, f.end) > max(s, f.start)}
                    if TYP_GRUPPEN[lab] not in typen:
                        typfehler.append([lab, "/".join(sorted(typen)), text[s:e], datei])
            else:
                missed.append([lab, text[s:e], datei])
        for lab, wert in case.get("fehlend", []):
            tot_typ[lab] += 1
            for z in (gesamt, fam):
                z["total"] += 1
            missed.append([lab, wert + "  (im gelesenen Text nicht auffindbar)", datei])
        for f in found:
            if any(min(e, f.end) > max(s, f.start) for s, e, lab in frei if lab in NICHT_GEZAEHLT) and not any(
                    min(e, f.end) > max(s, f.start) for s, e, _ in gold):
                continue
            found_typ[f.entity] += 1
            if not any(min(e, f.end) > max(s, f.start) for s, e, _ in gold):
                if f.entity == "PERSON" and f.text.strip(".,").lower() in gold_person_tokens:
                    name_parts.append(f.text)
                    for z in (gesamt, fam):
                        z["namensteile"] += 1
                else:
                    fp_typ[f.entity] += 1
                    false_pos.append([f.entity, f.text, f.quelle, datei])
                    for z in (gesamt, fam):
                        z["fp"] += 1
            for z in (gesamt, fam):
                z["found"] += 1

    def kennzahlen(z):
        n_real = z["found"] - z["namensteile"]
        return {**z, "recall": z["hit"] / max(1, z["total"]), "precision": (n_real - z["fp"]) / max(1, n_real),
                "fehlalarme_je_seite": z["fp"] / max(1, z["seiten"])}

    return {
        "gesamt": kennzahlen(gesamt),
        "familien": {k: kennzahlen(v) for k, v in sorted(je_familie.items())},
        "recall_je_typ": {k: [hit_typ[k], tot_typ[k]] for k in sorted(tot_typ)},
        "precision_je_typ": {k: [found_typ[k], fp_typ[k]] for k in sorted(found_typ)},
        "uebersehen": missed, "fehlalarme": false_pos, "typfehler": typfehler,
        "namensteile": sorted(set(name_parts)),
        "tempo_s_je_1000": t_detect / max(1, n_chars) * 1000, "zeichen": n_chars,
    }


def _verdecken(r: dict) -> dict:
    """Klartext aus Listen entfernen (eigene Testfälle enthalten echte Daten)."""
    def v(t):
        return f"‹{len(t)} Zeichen›"
    return {**r, "uebersehen": [[lab, v(t), d] for lab, t, d in r["uebersehen"]],
            "fehlalarme": [[lab, v(t), q, d] for lab, t, q, d in r["fehlalarme"]],
            "typfehler": [[lab, typ, v(t), d] for lab, typ, t, d in r["typfehler"]],
            "namensteile": [v(t) for t in r["namensteile"]]}


def eigene_bilanz(faelle) -> None:
    """Was die Prüfung an den eigenen Vorgängen geändert hat: nachgetragene Stellen = von Lokanon übersehen,
    abgewählte Vorschläge = Fehlalarme. Das ist die Messung der Version, mit der geprüft wurde."""
    vor = sum(len(f.get("vorschlaege", [])) for f in faelle)
    ab = sum(1 for f in faelle for v in f.get("vorschlaege", []) if not v[4])
    nach = sum(f.get("nachgetragen", 0) for f in faelle)
    gold = sum(len(f["spans"]) for f in faelle)
    print(f"\nEigene Prüfungen: {len(faelle)} Dateien, {gold} ersetzte Stellen. Damals {vor} Vorschläge, davon {ab} "
          f"abgewählt; {nach} Stellen von Hand nachgetragen.")
    if gold:
        print(f"  Recall damals ≈ {(gold - nach) / gold:.1%}, Precision damals ≈ {(vor - ab) / max(1, vor):.1%}")


def ausgeben(r: dict, leise: bool = False) -> None:
    print(f"\n{'Familie':<22}{'Dok.':>5}{'Recall':>9}{'Precision':>11}{'Fehlalarme/Seite':>18}")
    for name, z in list(r["familien"].items()) + [("GESAMT", r["gesamt"])]:
        print(f"{name:<22}{z['dokumente']:>5}{z['recall']:>9.0%}{z['precision']:>11.0%}"
              f"{z['fehlalarme_je_seite']:>18.1f}")
    print(f"\n{'Typ':<22}{'erkannt':>8}{'gesamt':>8}{'Recall':>8}")
    for lab, (h, t) in r["recall_je_typ"].items():
        print(f"{lab:<22}{h:>8}{t:>8}{h / max(1, t):>8.0%}")
    print(f"\n{'Treffer-Typ':<22}{'gesamt':>8}{'falsch':>8}{'Precision':>10}")
    for lab, (n, bad) in r["precision_je_typ"].items():
        print(f"{lab:<22}{n:>8}{bad:>8}{(n - bad) / max(1, n):>10.0%}")
    g = r["gesamt"]
    print(f"\nRecall: {g['recall']:.1%}   Precision: {g['precision']:.1%}  ({g['fp']} Fehlalarme, "
          f"{g['namensteile']} Namensteile nicht mitgezählt, {len(r['typfehler'])} Typfehler)")
    print(f"Tempo: {r['tempo_s_je_1000']:.2f} s je 1.000 Zeichen ({r['zeichen']:,} Zeichen)")
    if leise:
        return
    if r["uebersehen"]:
        print("\nÜbersehen:")
        for lab, t, datei in r["uebersehen"]:
            print(f"  [{lab}] {t}" + (f"   ({datei})" if datei else ""))
    if r["fehlalarme"]:
        print("\nFehlalarme:")
        for lab, t, quelle, datei in r["fehlalarme"]:
            print(f"  [{lab}] {t}   <{quelle}>" + (f" ({datei})" if datei else ""))
    if r["typfehler"]:
        print("\nTypfehler (maskiert, aber falsche Art):")
        for lab, typ, t, datei in r["typfehler"]:
            print(f"  [{lab} → {typ}] {t}   ({datei})")
    if r["namensteile"]:
        print("\nNamensteile (ok, nicht in Referenz markiert): " + ", ".join(r["namensteile"]))


def vergleichen(r: dict, basis: dict) -> None:
    print("\nVergleich mit der Basislinie:")
    for name in sorted(set(r["familien"]) | set(basis["familien"])) + ["GESAMT"]:
        a = r["gesamt"] if name == "GESAMT" else r["familien"].get(name)
        b = basis["gesamt"] if name == "GESAMT" else basis["familien"].get(name)
        if not a or not b:
            print(f"  {name:<22} (nur in einer Messung)")
            continue
        print(f"  {name:<22} Recall {b['recall']:.0%} → {a['recall']:.0%} ({(a['recall'] - b['recall']) * 100:+.1f})"
              f"   Precision {b['precision']:.0%} → {a['precision']:.0%} "
              f"({(a['precision'] - b['precision']) * 100:+.1f})")
    alt_miss = {tuple(m) for m in basis["uebersehen"]}
    neu_miss = {tuple(m) for m in r["uebersehen"]}
    alt_fp = {tuple(f[:2] + f[3:]) for f in basis["fehlalarme"]}
    neu_fp = {tuple(f[:2] + f[3:]) for f in r["fehlalarme"]}
    for titel, menge in (("Neu übersehen", neu_miss - alt_miss), ("Nicht mehr übersehen", alt_miss - neu_miss),
                         ("Neue Fehlalarme", neu_fp - alt_fp), ("Behobene Fehlalarme", alt_fp - neu_fp)):
        if menge:
            print(f"\n{titel} ({len(menge)}):")
            for m in sorted(menge):
                print(f"  [{m[0]}] {m[1]}   ({m[-1]})")


def main(args):
    sys.stdout.reconfigure(encoding="utf-8")

    def option(name):
        nonlocal args
        if name in args:
            i = args.index(name)
            wert = args[i + 1]
            args = args[:i] + args[i + 2:]
            return wert
        return None

    cfg_path = option("--config") or "config.yaml"
    json_out, gegen = option("--json"), option("--gegen")
    ohne_gliner, leise = "--ohne-gliner" in args, "--leise" in args
    eigene, klartext = "--eigene" in args, "--klartext" in args
    paths = [a for a in args if a not in ("--ohne-gliner", "--leise", "--eigene", "--klartext")]
    if not paths and not eigene:
        paths = ["testdaten/beispiel.jsonl"]
    cfg = yaml.safe_load(open(cfg_path, encoding="utf-8"))
    print(f"Konfiguration: {cfg_path}")
    t0 = time.time()
    analyzer = analyzer_fuer(cfg, ohne_gliner)
    print(f"Modelle geladen in {time.time() - t0:.0f} s"
          + (f" (spaCy + GLiNER {cfg['gliner_model']})" if cfg.get("gliner_model") and not ohne_gliner
             else " (spaCy)"))
    faelle = list(lade_faelle(paths))
    if eigene:
        from server import einstellungen as est
        from server import testfaelle as tf

        mein = tf.laden(est.daten_ordner())
        eigene_bilanz(mein)
        faelle += mein
    r = auswerten(analyzer, cfg, faelle)
    if eigene and not klartext:
        r = _verdecken(r)
    ausgeben(r, leise)
    if gegen:
        vergleichen(r, json.load(open(gegen, encoding="utf-8")))
    if json_out:
        with open(json_out, "w", encoding="utf-8") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1)
        print(f"\nErgebnis gespeichert: {json_out}")


if __name__ == "__main__":
    main(sys.argv[1:])
