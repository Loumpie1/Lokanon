"""Eigenes Erkennungsmodell trainieren: deepset/gbert-base als Token-Klassifikator (PER, ORG, ADR), nur CPU.

    python experimente/eigenes_modell/trainieren.py [epochen]

Ergebnis unter experimente/eigenes_modell/modell (nicht im Repository). Messen mit
    python experimente/messlatte/messen.py NAME --eigenes-modell experimente/eigenes_modell/modell
"""
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import AutoTokenizer, BertForTokenClassification

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import daten as D  # noqa: E402

BASIS = "deepset/gbert-base"
TOKENIZER = HIER.parents[0] / "zweitpruefer" / "daten" / "tokenizer"  # gbert hat nur vocab.txt, siehe dort
MODELL = HIER / "modell"


def zusammen(bs):
    n = max(len(b["input_ids"]) for b in bs)
    ids = torch.zeros(len(bs), n, dtype=torch.long)
    att = torch.zeros(len(bs), n, dtype=torch.long)
    lab = torch.full((len(bs), n), -100, dtype=torch.long)
    for i, b in enumerate(bs):
        k = len(b["input_ids"])
        ids[i, :k] = torch.tensor(b["input_ids"])
        att[i, :k] = 1
        lab[i, :k] = torch.tensor(b["labels"])
    return {"input_ids": ids, "attention_mask": att, "labels": lab}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    epochen = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    torch.manual_seed(0)
    torch.set_num_threads(6)
    tok = AutoTokenizer.from_pretrained(TOKENIZER)
    daten = D.bauen(tok)
    print(f"{len(daten)} Fenster zu höchstens {D.FENSTER} Tokens", flush=True)
    model = BertForTokenClassification.from_pretrained(
        BASIS, num_labels=len(D.LABELS), id2label=dict(enumerate(D.LABELS)), label2id=D.L2I)
    opt = torch.optim.AdamW(model.parameters(), lr=4e-5, weight_decay=0.01)
    groesse = 16
    schritte = epochen * ((len(daten) + groesse - 1) // groesse)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / (0.06 * schritte)) * max(0.0, 1 - s / schritte))
    t0, s = time.time(), 0
    for ep in range(epochen):
        model.train()
        # ähnlich lange Fenster zusammen, das spart Rechenzeit
        dl = DataLoader(daten, batch_size=groesse, shuffle=True, collate_fn=zusammen)
        for enc in dl:
            loss = model(**enc).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            s += 1
            if s % 25 == 0:
                print(f"Epoche {ep + 1}, Schritt {s}/{schritte}, Verlust {loss.item():.3f}, "
                      f"{(time.time() - t0) / s * (schritte - s) / 60:.0f} min übrig", flush=True)
        MODELL.mkdir(exist_ok=True)
        model.save_pretrained(MODELL)
        tok.save_pretrained(MODELL)
        print(f"Epoche {ep + 1} gespeichert ({(time.time() - t0) / 60:.0f} min)", flush=True)
    print(f"Fertig in {(time.time() - t0) / 60:.0f} min, gespeichert in {MODELL}")


if __name__ == "__main__":
    main()
