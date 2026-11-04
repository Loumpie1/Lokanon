"""Zweitprüfer trainieren: gbert-base entscheidet für einen Namens- oder Firmenvorschlag "anonymisieren ja/nein".

Training: Abwandlungen der Testsammlung (Lösung bekannt) + 80 % der Wiktionary-Kandidaten (Lösung vom
Sprachmodell). Die übrigen 20 % (nach Satz getrennt) dienen als Test. Prüfsammlung und Kanzleifälle sind nicht dabei.

    python experimente/zweitpruefer/trainieren.py [epochen]
"""
import json
import random
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer

HIER = Path(__file__).resolve().parent
DATEN = HIER / "daten"
MODELL = HIER / "modell"
BASIS = "deepset/gbert-base"
ART = {"PERSON": "Person", "ORGANIZATION": "Firma"}
MAX_LEN = 128


def eingabe(b):
    return f"{ART[b['entity']]}: {b['text']}", b["kontext"]


def laden():
    korpus = [json.loads(z) for z in open(DATEN / "korpus_beispiele.jsonl", encoding="utf-8")]
    wiki = [json.loads(z) for z in open(DATEN / "wiki_bewertet.jsonl", encoding="utf-8")]
    saetze = sorted({w["satz"] for w in wiki})
    random.Random(3).shuffle(saetze)
    test_saetze = set(saetze[: len(saetze) // 5])
    train = korpus + [w for w in wiki if w["satz"] not in test_saetze]
    test = [w for w in wiki if w["satz"] in test_saetze]
    return train, test


def batches(tok, daten, groesse, mischen):
    def zusammen(bs):
        a, b = zip(*(eingabe(x) for x in bs))
        enc = tok(list(a), list(b), truncation="only_second", max_length=MAX_LEN, padding=True, return_tensors="pt")
        enc["labels"] = torch.tensor([x["label"] for x in bs])
        return enc
    return DataLoader(daten, batch_size=groesse, shuffle=mischen, collate_fn=zusammen)


@torch.no_grad()
def wahrscheinlichkeiten(model, tok, daten):
    model.eval()
    out = []
    for enc in batches(tok, daten, 32, False):
        enc.pop("labels")
        out += torch.softmax(model(**enc).logits, -1)[:, 1].tolist()
    return out


def kennzahlen(p, daten, schwelle=0.5):
    tp = sum(1 for x, d in zip(p, daten) if x >= schwelle and d["label"])
    fn = sum(1 for x, d in zip(p, daten) if x < schwelle and d["label"])
    tn = sum(1 for x, d in zip(p, daten) if x < schwelle and not d["label"])
    fp = sum(1 for x, d in zip(p, daten) if x >= schwelle and not d["label"])
    return {"echte_behalten": tp, "echte_verworfen": fn, "fehlalarme_verworfen": tn, "fehlalarme_behalten": fp}


def main():
    epochen = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    torch.manual_seed(0)
    torch.set_num_threads(6)
    train, test = laden()
    print(f"Training {len(train)} ({sum(b['label'] for b in train)} echt), Test {len(test)} "
          f"({sum(b['label'] for b in test)} echt)", flush=True)
    tok = AutoTokenizer.from_pretrained(BASIS)
    model = AutoModelForSequenceClassification.from_pretrained(BASIS, num_labels=2)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-5, weight_decay=0.01)
    schritte = epochen * ((len(train) + 15) // 16)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / (0.1 * schritte)) * max(0.0, 1 - s / schritte))
    t0, s = time.time(), 0
    for ep in range(epochen):
        model.train()
        for enc in batches(tok, train, 16, True):
            loss = model(**enc).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            s += 1
            if s % 50 == 0:
                print(f"Epoche {ep + 1}, Schritt {s}/{schritte}, Verlust {loss.item():.3f}, "
                      f"{(time.time() - t0) / s * (schritte - s) / 60:.0f} min übrig", flush=True)
        p = wahrscheinlichkeiten(model, tok, test)
        print(f"Nach Epoche {ep + 1}: Test {kennzahlen(p, test)}", flush=True)
    MODELL.mkdir(exist_ok=True)
    model.save_pretrained(MODELL)
    tok.save_pretrained(MODELL)
    p = wahrscheinlichkeiten(model, tok, test)
    with open(DATEN / "test_vorhersagen.jsonl", "w", encoding="utf-8") as fh:
        for x, d in zip(p, test):
            fh.write(json.dumps({**d, "p": x}, ensure_ascii=False) + "\n")
    print(f"Fertig in {(time.time() - t0) / 60:.0f} min, gespeichert in {MODELL}")


if __name__ == "__main__":
    main()
