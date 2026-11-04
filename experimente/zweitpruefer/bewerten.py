"""Wiktionary-Kandidaten vom lokalen Sprachmodell bewerten lassen (nur zum Erzeugen von Trainingsdaten).

Läuft in der eigenen Test-venv mit llama-cpp-python. Setzt nach Abbruch fort (bereits bewertete Kandidaten
werden übersprungen).

    llm-venv\\Scripts\\python -I experimente/zweitpruefer/bewerten.py <modell.gguf> [max_kandidaten]
"""
import json
import sys
import time
from pathlib import Path

from llama_cpp import Llama

DATEN = Path(__file__).resolve().parent / "daten"
JE_ANFRAGE = 8

SYSTEM = (
    "Du bereitest Trainingsdaten für ein Anonymisierungsprogramm vor. Es schlägt Stellen in deutschen Texten als "
    "Person oder Firma vor. Entscheide je Vorschlag, ob die markierte Stelle wirklich eine bestimmte Person "
    "(Vorname, Nachname, auch erfundene Figuren und bekannte Persönlichkeiten) oder eine bestimmte Firma, einen "
    "Verein oder eine private Organisation mit Eigennamen benennt. Dann antworte true. "
    "Antworte false bei gewöhnlichen Wörtern, Berufen und Rollen, Tieren, Göttern, Völkern und Nationen, Orten "
    "und Ländern, Werken, Produkten und Marken als Sache, Fachbegriffen, Krankheiten, Behörden, Gerichten, "
    "Parteien und Staaten als Institution sowie bei Stellen, die nur ein Teil eines Wortes sind oder Satzzeichen "
    "enthalten, die nicht zum Namen gehören. Antworte nur mit JSON.")
SCHEMA = {"type": "object", "properties": {"urteile": {"type": "array", "items": {
    "type": "object", "properties": {"nr": {"type": "integer"}, "anonymisieren": {"type": "boolean"}},
    "required": ["nr", "anonymisieren"]}}}, "required": ["urteile"]}
ART = {"PERSON": "Person", "ORGANIZATION": "Firma/Organisation"}


def main():
    llm = Llama(model_path=sys.argv[1], n_ctx=4096, n_threads=6, verbose=False, seed=1)
    grenze = int(sys.argv[2]) if len(sys.argv) > 2 else 10 ** 9
    kand = [json.loads(z) for z in open(DATEN / "wiki_kandidaten.jsonl", encoding="utf-8")][:grenze]
    ziel = DATEN / "wiki_bewertet.jsonl"
    fertig = {(d["satz"], d["entity"], d["text"]) for d in map(json.loads, open(ziel, encoding="utf-8"))} \
        if ziel.exists() else set()
    offen = [k for k in kand if (k["satz"], k["entity"], k["text"]) not in fertig]
    print(f"{len(kand)} Kandidaten, {len(offen)} offen", flush=True)
    t_start = time.time()
    with open(ziel, "a", encoding="utf-8") as fh:
        for i in range(0, len(offen), JE_ANFRAGE):
            gruppe = offen[i:i + JE_ANFRAGE]
            liste = "\n".join(f"{j + 1}. „{k['text']}“ als {ART[k['entity']]} – Stelle: {k['kontext']}"
                              for j, k in enumerate(gruppe))
            r = llm.create_chat_completion(
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": f"Vorschläge (die Stelle ist mit « » markiert):\n{liste}\n\n"
                                                      "Beurteile jeden Vorschlag. /no_think"}],
                response_format={"type": "json_object", "schema": SCHEMA}, temperature=0.0,
                max_tokens=40 + 20 * len(gruppe))
            try:
                urteil = {u["nr"]: u["anonymisieren"] for u in json.loads(r["choices"][0]["message"]["content"])["urteile"]}
            except (json.JSONDecodeError, KeyError, TypeError):
                urteil = {}
            for j, k in enumerate(gruppe):
                if urteil.get(j + 1) is not None:
                    fh.write(json.dumps({**k, "label": int(urteil[j + 1]), "label_von": "qwen3-4b"},
                                        ensure_ascii=False) + "\n")
            fh.flush()
            n = i + len(gruppe)
            rest = (time.time() - t_start) / n * (len(offen) - n)
            print(f"{n}/{len(offen)} bewertet, noch etwa {rest / 60:.0f} min", flush=True)


if __name__ == "__main__":
    main()
