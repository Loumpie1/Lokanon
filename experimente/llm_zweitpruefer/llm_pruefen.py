"""Schritt 2 (eigene Test-venv mit llama-cpp-python): lokales Sprachmodell als Zweitprüfer.

A) Unsichere Treffer (Score < 0,7, nicht aus Liste oder Wiederholung) bekommt das Modell mit dem Dokument
   vorgelegt und entscheidet je Treffer: anonymisieren ja/nein.
B) Das Modell sucht indirekte Hinweise auf Personen (Rolle + Ort, Amt, Verwandtschaft, Ereignis), in allen
   Testdokumenten und in den erfundenen Sätzen aus indirekt.txt.

    llm-venv\\Scripts\\python -I experimente/llm_zweitpruefer/llm_pruefen.py <modell.gguf>
"""
import json
import re
import sys
import time
from pathlib import Path

from llama_cpp import Llama

HIER = Path(__file__).resolve().parent
ERG = HIER / "ergebnisse"
OHNE_PRUEFUNG = {"liste", "wiederholung", "namensteil", "vorgang"}
ARTEN = {"PERSON": "Person", "ORGANIZATION": "Firma/Organisation", "ADRESSE": "Anschrift", "LOCATION": "Ort",
         "DATUM": "Datum", "TELEFON": "Telefonnummer", "EMAIL_ADDRESS": "E-Mail", "KFZ": "Kennzeichen",
         "DE_KFZ": "Kennzeichen", "IBAN_CODE": "IBAN", "KENNNUMMER": "Nummer", "AKTENZEICHEN": "Aktenzeichen"}

SYSTEM_A = (
    "Du prüfst Vorschläge eines Anonymisierungsprogramms für deutsche Schriftsätze, Bescheide, Formulare, "
    "Lohn-, Konto- und Arztunterlagen. Ein Vorschlag ist RICHTIG, wenn die markierte Stelle eine bestimmte "
    "Person, Firma oder private Organisation benennt oder eine persönliche Angabe ist: Name, Anschrift, "
    "Geburtsdatum oder anderes persönliches Datum, Telefon, E-Mail, Kennnummer, Kennzeichen, Kontodaten. "
    "FALSCH sind Fachbegriffe, Krankheiten, Medikamente, Untersuchungen und Testverfahren, Produkt- und "
    "Markennamen, Gesetze, Gerichte, Behörden und Krankenkassen als Institution, Überschriften und "
    "Feldbezeichnungen, Beträge, allgemeine Datumsangaben wie Fristen oder Rechnungsdaten und gewöhnliche Wörter. "
    "Antworte nur mit JSON.")

SYSTEM_B = (
    "Du hilfst beim Anonymisieren deutscher Dokumente. Namen, Anschriften, Nummern und Datumsangaben werden "
    "schon von einem anderen Programm erkannt. Deine Aufgabe sind INDIREKTE Hinweise: Textstellen, durch die "
    "eine bestimmte Person auch ohne Namen erkennbar wäre, zum Beispiel eine einmalige Rolle oder Funktion an "
    "einem bestimmten Ort, ein Amt oder Ehrenamt, eine Verwandtschaft zu einer bekannten Person oder ein "
    "besonderes, öffentlich bekanntes Ereignis. NICHT gemeint sind allgemeine Rollen ohne Ortsbezug (der Kläger, "
    "die Mieterin, ein Lagerist, die Versicherung) und Angaben, die nur aus einem Namen, einer Anschrift, einer "
    "Nummer oder einem Datum bestehen. Gib jede Stelle als wörtliches Zitat aus dem Text an, so kurz wie möglich, "
    "aber vollständig. Gibt es keine, gib eine leere Liste zurück. Antworte nur mit JSON.")

SCHEMA_A = {"type": "object", "properties": {"urteile": {"type": "array", "items": {
    "type": "object", "properties": {"nr": {"type": "integer"}, "anonymisieren": {"type": "boolean"}},
    "required": ["nr", "anonymisieren"]}}}, "required": ["urteile"]}
SCHEMA_B = {"type": "object", "properties": {"stellen": {"type": "array", "items": {"type": "string"}}},
            "required": ["stellen"]}


def zeile_um(text, s, e, rand=70):
    a, b = max(0, s - rand), min(len(text), e + rand)
    return re.sub(r"\s+", " ", text[a:s] + "[[" + text[s:e] + "]]" + text[e:b]).strip()


def frage(llm, system, user, schema, max_tokens):
    t0 = time.time()
    r = llm.create_chat_completion(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user + " /no_think"}],
        response_format={"type": "json_object", "schema": schema}, temperature=0.0, max_tokens=max_tokens)
    u = r["usage"]
    return json.loads(r["choices"][0]["message"]["content"]), time.time() - t0, u["prompt_tokens"], u["completion_tokens"]


def indirekt_faelle():
    faelle = []
    for z in (HIER / "indirekt.txt").read_text(encoding="utf-8").splitlines():
        if not z.strip() or z.startswith("#"):
            continue
        text, spans = "", []
        for teil in re.split(r"(«INDIREKT\|[^»]*»)", z):
            m = re.fullmatch(r"«INDIREKT\|([^»]*)»", teil)
            if m:
                spans.append([len(text), len(text) + len(m.group(1)), "INDIREKT"])
                text += m.group(1)
            else:
                text += teil
        faelle.append({"datei": f"satz_{len(faelle) + 1:02d}", "sammlung": "saetze", "text": text, "spans": spans})
    return faelle


def main():
    llm = Llama(model_path=sys.argv[1], n_ctx=6144, n_threads=6, verbose=False, seed=1)
    faelle = json.load(open(ERG / "kandidaten.json", encoding="utf-8"))
    protokoll = {"modell": Path(sys.argv[1]).name, "a": [], "b": []}

    # A) Zweitprüfer
    for case in faelle:
        text, gesehen, kand = case["text"], set(), []
        for lauf in ("normal", "niedrig"):
            for f in case[lauf]:
                k = (f["start"], f["end"], f["entity"])
                if f["score"] < 0.7 and f["quelle"] not in OHNE_PRUEFUNG and k not in gesehen:
                    gesehen.add(k)
                    kand.append(f)
        if not kand:
            continue
        liste = "\n".join(f"{i + 1}. „{f['text']}“ als {ARTEN.get(f['entity'], f['entity'])} – Stelle: …{zeile_um(text, f['start'], f['end'])}…"
                          for i, f in enumerate(kand))
        user = f"Dokument:\n<<<\n{text}\n>>>\n\nVorschläge (die Stelle ist mit [[ ]] markiert):\n{liste}\n\nBeurteile jeden Vorschlag."
        antwort, dauer, pt, ct = frage(llm, SYSTEM_A, user, SCHEMA_A, 40 + 20 * len(kand))
        urteil = {u["nr"]: u["anonymisieren"] for u in antwort.get("urteile", [])}
        for i, f in enumerate(kand):
            protokoll["a"].append({"datei": case.get("datei", ""), "sammlung": case["sammlung"], "start": f["start"],
                                   "end": f["end"], "entity": f["entity"], "text": f["text"],
                                   "anonymisieren": urteil.get(i + 1)})
        protokoll.setdefault("a_zeit", []).append([case.get("datei", ""), len(kand), round(dauer, 1), pt, ct])
        print(f"A {case.get('datei', '')}: {len(kand)} Vorschläge, {dauer:.0f} s ({pt}+{ct} Token)", flush=True)

    # B) indirekte Hinweise
    for case in faelle + indirekt_faelle():
        user = f"Dokument:\n<<<\n{case['text']}\n>>>\n\nWelche Stellen machen eine Person indirekt erkennbar?"
        antwort, dauer, pt, ct = frage(llm, SYSTEM_B, user, SCHEMA_B, 300)
        protokoll["b"].append({"datei": case.get("datei", ""), "sammlung": case["sammlung"], "text": case["text"],
                               "spans": case["spans"], "stellen": antwort.get("stellen", []),
                               "sekunden": round(dauer, 1), "token": [pt, ct]})
        print(f"B {case.get('datei', '')}: {antwort.get('stellen', [])} ({dauer:.0f} s)", flush=True)

    with open(ERG / "llm_protokoll.json", "w", encoding="utf-8") as fh:
        json.dump(protokoll, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
