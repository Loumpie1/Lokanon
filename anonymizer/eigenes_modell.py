"""Eigenes deutsches Erkennungsmodell (gbert-base, lokal trainiert, siehe experimente/eigenes_modell) als
Presidio-Erkenner. Liefert PERSON, ORGANIZATION und ADRESSE; engine.detect behandelt die Treffer wie die der
anderen Modelle (quelle "modell", gleiche Filter).
"""
from __future__ import annotations

from presidio_analyzer import EntityRecognizer, RecognizerResult

NAME = "LokanonNER"
ZUORDNUNG = {"PER": "PERSON", "ORG": "ORGANIZATION", "ADR": "ADRESSE"}


class LokanonNER(EntityRecognizer):
    def __init__(self, pfad: str, schwelle: float = 0.5, fenster: int = 256, schritt: int = 192):
        self.pfad, self.schwelle, self.fenster, self.schritt = pfad, schwelle, fenster, schritt
        super().__init__(supported_entities=sorted(set(ZUORDNUNG.values())), name=NAME, supported_language="de")

    def load(self) -> None:
        import torch
        from transformers import AutoTokenizer, BertForTokenClassification

        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(self.pfad)
        self.model = BertForTokenClassification.from_pretrained(self.pfad).eval()
        self.labels = self.model.config.id2label

    def _wahrscheinlichkeiten(self, ids):
        """Je Token (Label, p) über überlappende Fenster; in der Überlappung zählt das spätere Fenster."""
        torch = self.torch
        n = self.fenster - 2
        out = [None] * len(ids)
        with torch.no_grad():
            for st in range(0, max(1, len(ids)), self.schritt):
                teil = ids[st:st + n]
                if not teil:
                    break
                x = torch.tensor([[self.tok.cls_token_id] + teil + [self.tok.sep_token_id]])
                p = torch.softmax(self.model(input_ids=x).logits[0, 1:-1], -1)
                werte, idx = p.max(-1)
                for k, (w, i) in enumerate(zip(werte.tolist(), idx.tolist())):
                    if st == 0 or k >= n - self.schritt or out[st + k] is None:
                        out[st + k] = (self.labels[i], w)
                if st + n >= len(ids):
                    break
        return out

    def analyze(self, text, entities, nlp_artifacts=None):
        if not text.strip():
            return []
        enc = self.tok(text, return_offsets_mapping=True, add_special_tokens=False)
        ids, offs = enc["input_ids"], enc["offset_mapping"]
        probs = self._wahrscheinlichkeiten(ids)
        spans, akt = [], None  # akt: [start, ende, art, [p…]]
        for (a, b), (lab, p) in zip(offs, probs):
            art = lab[2:] if lab != "O" else None
            weiter = akt and art == akt[2] and (lab.startswith("I-") or text[akt[1]:a] == "")
            if art and weiter:
                akt[1] = b
                akt[3].append(p)
            else:
                if akt:
                    spans.append(akt)
                akt = [a, b, art, [p]] if art else None
        if akt:
            spans.append(akt)
        out = []
        for s, e, art, ps in spans:
            # an Wortgrenzen ausdehnen (Wortteil-Tokens)
            while s > 0 and text[s - 1].isalnum():
                s -= 1
            while e < len(text) and text[e].isalnum():
                e += 1
            score = sum(ps) / len(ps)
            ent = ZUORDNUNG[art]
            if score >= self.schwelle and ent in entities:
                out.append(RecognizerResult(ent, s, e, float(score)))
        return out
