"""Trainingsdaten für das eigene Erkennungsmodell (Token-Klassifikation, BIO) aus Dokumenten mit Goldspannen.

Quellen (nur Trainingsteile; Prüfsammlung, Kanzleifälle und die Messteile von LER/GraSCCo bleiben draußen):
  - LER-Trainingsteil (Urteile), Abschnitte mit Namen/Firmen/Adressen bevorzugt
  - GraSCCo-Trainingsteil (Arztbriefe), dreifach gewichtet (wenig Daten, wichtige Textsorte)
  - Abwandlungen der Testsammlung (testdaten/korpus) mit zufälligen Namen aus den Wörterbuchlisten

Labels: PER (Person), ORG (Firma), ADR (Anschrift, PLZ und Ort). Zahlen, Daten, Kontakte erkennen die Regeln.
OPTIONAL und INDIREKT werden im Training ignoriert (-100), ebenso Tokens, die schon Teil einer Goldspanne
anderer Art sind. Einzelne Namensteile, die die Referenz nicht eigens markiert ("Mia" zu "Mia Schneider"),
werden als PER nachgetragen, sonst lernte das Modell, sie stehen zu lassen.
"""
import json
import os
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experimente" / "zweitpruefer"))

MESS = Path(os.environ.get("LOKANON_MESSDATEN", Path.home() / "Lokanon" / "messdaten"))
ZUORDNUNG = {"PERSON": "PER", "ORGANIZATION": "ORG", "ADRESSE": "ADR", "PLZ_ORT": "ADR"}
IGNORIEREN = {"OPTIONAL", "INDIREKT"}
LABELS = ["O", "B-PER", "I-PER", "B-ORG", "I-ORG", "B-ADR", "I-ADR"]
L2I = {l: i for i, l in enumerate(LABELS)}
FENSTER, SCHRITT = 256, 192


def _namensteile(case):
    """Namensteile markierter Personen, die an anderer Stelle allein stehen, als PERSON nachtragen."""
    text, spans = case["text"], list(case["spans"])
    teile = {w.strip(".,") for s, e, lab in spans if lab == "PERSON" for w in text[s:e].split()
             if len(w.strip(".,")) >= 3 and w[:1].isupper()}
    belegt = [(s, e) for s, e, _ in spans]
    for t in teile:
        for m in re.finditer(rf"(?<![\wäöüß]){re.escape(t)}(?:s)?(?![\wäöüß])", text):
            if not any(m.start() < e and m.end() > s for s, e in belegt):
                spans.append([m.start(), m.end(), "PERSON"])
                belegt.append((m.start(), m.end()))
    return {**case, "spans": spans}


def fenster(tok, case):
    """Text in überlappende Fenster zu FENSTER Tokens; je Token ein Label (oder -100)."""
    enc = tok(case["text"], return_offsets_mapping=True, add_special_tokens=False)
    ids, offs = enc["input_ids"], enc["offset_mapping"]
    labs = []
    spans = sorted(case["spans"])
    for (a, b) in offs:
        lab, anfang = "O", False
        for s, e, l in spans:
            if a < e and b > s:
                if l in IGNORIEREN or l not in ZUORDNUNG:
                    lab = None if l in IGNORIEREN else "O"
                else:
                    anfang = a <= s
                    lab = ZUORDNUNG[l]
                break
        if lab is None:
            labs.append(-100)
        elif lab == "O":
            labs.append(L2I["O"])
        else:
            vorher = labs[-1] if labs else -1
            fortsetzung = not anfang and vorher in (L2I[f"B-{lab}"], L2I[f"I-{lab}"])
            labs.append(L2I[("I-" if fortsetzung else "B-") + lab])
    n = FENSTER - 2
    for st in range(0, max(1, len(ids)), SCHRITT):
        teil_ids, teil_labs = ids[st:st + n], labs[st:st + n]
        if not teil_ids:
            break
        # Überlappung: die ersten Tokens eines Folgefensters zählen nicht doppelt
        if st > 0:
            teil_labs = [-100] * min(n - SCHRITT, len(teil_labs)) + teil_labs[n - SCHRITT:]
        yield {"input_ids": [tok.cls_token_id] + teil_ids + [tok.sep_token_id],
               "labels": [-100] + teil_labs + [-100],
               "hat_name": any(l not in (-100, L2I["O"]) for l in teil_labs)}
        if st + n >= len(ids):
            break


def lade(pfad):
    return [json.loads(z) for z in open(pfad, encoding="utf-8") if z.strip()]


def korpus_abwandlungen(n=12, seed=11):
    import beispiele as B

    vor, nach = B._liste("vornamen"), B._liste("nachnamen")
    rnd = random.Random(seed)
    faelle = lade(ROOT / "testdaten/korpus/referenz.jsonl")
    return [B.abwandeln(c, vor, nach, rnd) for _ in range(n) for c in faelle]


def bauen(tok, seed=5, ler_fenster=2200, ohne_name_anteil=0.25):
    rnd = random.Random(seed)
    gruppen = {"ler": lade(MESS / "ler_train.jsonl"), "grascco": lade(MESS / "grascco_train.jsonl"),
               "korpus": korpus_abwandlungen()}
    alle = []
    for name, faelle in gruppen.items():
        fs = [f for c in faelle for f in fenster(tok, _namensteile(c))]
        mit = [f for f in fs if f["hat_name"]]
        ohne = [f for f in fs if not f["hat_name"]]
        rnd.shuffle(mit)
        rnd.shuffle(ohne)
        if name == "ler":
            mit = mit[:ler_fenster]
        ohne = ohne[:int(len(mit) * ohne_name_anteil / (1 - ohne_name_anteil))]
        wahl = (mit + ohne) * (3 if name == "grascco" else 1)
        print(f"{name}: {len(fs)} Fenster, davon {len(mit)} mit Namen genommen, {len(ohne)} ohne → {len(wahl)}")
        alle += wahl
    rnd.shuffle(alle)
    return alle
