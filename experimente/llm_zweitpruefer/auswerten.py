"""Schritt 3 (Lokanon-venv): Wirkung des Zweitprüfers messen, mit derselben Zählweise wie evaluate.py.

    python experimente/llm_zweitpruefer/auswerten.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

import evaluate as E  # noqa: E402
from anonymizer.engine import Finding  # noqa: E402

HIER = Path(__file__).parent
ERG = HIER / "ergebnisse"
WEITERGABE = {"wiederholung", "namensteil", "vorgang"}


def echt(case, f):
    return any(min(e, f["end"]) > max(s, f["start"]) for s, e, lab in case["spans"] if lab not in E.NICHT_GEZAEHLT)


def gefiltert(case, lauf, urteile):
    """Treffer ohne die vom Modell verworfenen; deren Weitergaben (gleicher Text) fallen mit weg."""
    weg = [f for f in case[lauf] if urteile.get((case.get("datei", ""), f["start"], f["end"], f["entity"])) is False]
    weg_texte = {f["text"].lower() for f in weg}
    bleibt = [f for f in case[lauf] if f not in weg]
    behalten_texte = {f["text"].lower() for f in bleibt if f["quelle"] not in WEITERGABE}
    return [f for f in bleibt if not (f["quelle"] in WEITERGABE and f["text"].lower() in weg_texte - behalten_texte)]


def messen(cfg, faelle, treffer):
    E.detect_fall = lambda _a, _c, text: [Finding(**f) for f in treffer[text]]
    r = E.auswerten(None, cfg, faelle)["gesamt"]
    return r["recall"], r["precision"], r["fp"], r["total"] - r["hit"]


def finde(text, zitat):
    """Zitat im Text suchen (Groß-/Kleinschreibung und Leerraum egal)."""
    muster = r"\s+".join(re.escape(w) for w in zitat.split())
    m = re.search(muster, text, re.IGNORECASE) if muster else None
    return (m.start(), m.end()) if m else None


def main():
    cfg = yaml.safe_load(open(ROOT / "testdaten/kanzlei/config_eval.yaml", encoding="utf-8"))
    faelle = json.load(open(ERG / "kandidaten.json", encoding="utf-8"))
    prot = json.load(open(ERG / "llm_protokoll.json", encoding="utf-8"))
    urteile = {(a["datei"], a["start"], a["end"], a["entity"]): a["anonymisieren"] for a in prot["a"]}
    bericht = {"modell": prot["modell"], "a": {}, "a_entscheidungen": {}, "b": {}}

    print(f"Modell: {prot['modell']}\n\nA) Zweitprüfer – Recall / Precision / Fehlalarme / übersehen")
    for sammlung in ("korpus", "pruefung", "kanzlei"):
        fs = [c for c in faelle if c["sammlung"] == sammlung]
        for lauf in ("normal", "niedrig"):
            for mit in (False, True):
                treffer = {c["text"]: (gefiltert(c, lauf, urteile) if mit else c[lauf]) for c in fs}
                rec, prec, fp, uebersehen = messen(cfg, fs, treffer)
                name = f"{lauf} {'+ Zweitprüfer' if mit else ''}".strip()
                bericht["a"][f"{sammlung}/{name}"] = [rec, prec, fp, uebersehen]
                print(f"  {sammlung:<9}{name:<24}{rec:7.1%}{prec:9.1%}{fp:5d}{uebersehen:5d}")

    # Wie gut entscheidet das Modell über die vorgelegten Treffer?
    tabelle, beispiele = Counter(), {"richtig_verworfen": [], "falsch_verworfen": [], "falsch_behalten": []}
    nach_datei = {c.get("datei", ""): c for c in faelle}
    for a in prot["a"]:
        case = nach_datei[a["datei"]]
        ist_echt = echt(case, a)
        frei = any(min(e, a["end"]) > max(s, a["start"]) for s, e, lab in case["spans"] if lab in E.NICHT_GEZAEHLT)
        if frei and not ist_echt:
            tabelle["optional/indirekt (zählt nicht)"] += 1
            continue
        if a["anonymisieren"] is None:
            tabelle["keine Antwort"] += 1
        elif ist_echt and a["anonymisieren"]:
            tabelle["echt, behalten"] += 1
        elif ist_echt:
            tabelle["echt, VERWORFEN"] += 1
            beispiele["falsch_verworfen"].append(f"{a['entity']}: {a['text']} ({a['datei']})")
        elif a["anonymisieren"]:
            tabelle["Fehlalarm, behalten"] += 1
            beispiele["falsch_behalten"].append(f"{a['entity']}: {a['text']} ({a['datei']})")
        else:
            tabelle["Fehlalarm, verworfen"] += 1
            beispiele["richtig_verworfen"].append(f"{a['entity']}: {a['text']} ({a['datei']})")
    bericht["a_entscheidungen"] = {"tabelle": dict(tabelle), **beispiele}
    print("\n  Entscheidungen über vorgelegte Treffer:", dict(tabelle))
    for k, v in beispiele.items():
        print(f"  {k}: {v[:15]}")

    # B) indirekte Hinweise
    print("\nB) Indirekte Hinweise")
    for sammlung in ("saetze", "korpus", "pruefung", "kanzlei"):
        gold = gefunden = nicht_woertlich = 0
        bekannt, zusaetzlich, getroffen, verpasst = [], [], [], []
        for b in (x for x in prot["b"] if x["sammlung"] == sammlung):
            ind = [(s, e) for s, e, lab in b["spans"] if lab == "INDIREKT"]
            andere = [(s, e) for s, e, lab in b["spans"] if lab != "INDIREKT"]
            orte = []
            for z in b["stellen"]:
                o = finde(b["text"], z)
                if o is None:
                    nicht_woertlich += 1
                    zusaetzlich.append(f"„{z}“ (nicht wörtlich im Text, {b['datei']})")
                    continue
                orte.append(o)
                if any(min(e, o[1]) > max(s, o[0]) for s, e in ind):
                    continue
                if any(min(e, o[1]) > max(s, o[0]) for s, e in andere):
                    bekannt.append(f"„{z}“ ({b['datei']})")
                else:
                    zusaetzlich.append(f"„{z}“ ({b['datei']})")
            for s, e in ind:
                gold += 1
                abgedeckt = sum(max(0, min(e, o[1]) - max(s, o[0])) for o in orte) / (e - s)
                (getroffen if abgedeckt >= 0.5 else verpasst).append(b["text"][s:e])
                gefunden += abgedeckt >= 0.5
        dauer = [x["sekunden"] for x in prot["b"] if x["sammlung"] == sammlung]
        bericht["b"][sammlung] = {"gold": gold, "gefunden": gefunden, "getroffen": getroffen, "verpasst": verpasst,
                                  "ueberschneidet_bekannte_angabe": bekannt, "zusaetzlich": zusaetzlich,
                                  "nicht_woertlich": nicht_woertlich, "dokumente": len(dauer),
                                  "sekunden_mittel": sum(dauer) / max(1, len(dauer))}
        print(f"  {sammlung}: {gefunden}/{gold} indirekte Hinweise gefunden, {len(bekannt)} Stellen mit Namen o. ä., "
              f"{len(zusaetzlich)} weitere Stellen, {sum(dauer) / max(1, len(dauer)):.0f} s je Dokument")
        print(f"    verpasst: {verpasst}\n    weitere: {zusaetzlich[:20]}\n    mit bekannter Angabe: {bekannt[:10]}")

    zeiten = prot.get("a_zeit", [])
    if zeiten:
        n = sum(z[1] for z in zeiten)
        s = sum(z[2] for z in zeiten)
        bericht["a_zeit"] = {"dokumente": len(zeiten), "vorschlaege": n, "sekunden": s}
        print(f"\nZeit Zweitprüfer: {s:.0f} s für {n} Vorschläge in {len(zeiten)} Dokumenten ({s / len(zeiten):.0f} s je Dokument)")
    with open(ERG / "bericht.json", "w", encoding="utf-8") as fh:
        json.dump(bericht, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
