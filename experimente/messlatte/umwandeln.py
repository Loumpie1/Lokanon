"""Öffentliche deutsche Datensätze in das Messformat von evaluate.py umwandeln (eine JSON-Zeile je Dokument).

Die Rohdaten liegen außerhalb des Projekts unter %USERPROFILE%\\Lokanon\\messdaten (siehe LIESMICH.md, laden.py).
Ausgabe daneben: ler_test.jsonl, ler_train.jsonl, grascco_test.jsonl, grascco_train.jsonl.

    python experimente/messlatte/umwandeln.py

Zuordnung der Labels (was Lokanon maskieren soll; OPTIONAL = darf, muss aber nicht; INDIREKT = zählt nicht):
- LER (Urteile, CoNLL, IOB2): PER/RR/AN → PERSON (nur ausgeschriebene Namen; Initialen wie „F.“ sind schon
  anonymisiert → OPTIONAL), UN → ORGANIZATION, STR → ADRESSE; ORG, INN, GRT, LD, ST, LDS, MRK, RS, LIT → OPTIONAL.
  Gesetze und Normen (GS, VO, EUN, VS, VT) bleiben unmarkiert: Treffer darauf sind Fehlalarme.
- GraSCCo_PII (Arztbriefe, INCEpTION-JSON): Namen → PERSON, Titel → OPTIONAL, Straße → ADRESSE, PLZ → PLZ_ORT,
  Einrichtung → ORGANIZATION, Klinik → OPTIONAL (Lokanon lässt Kliniken
  standardmäßig stehen), ID → KENNNUMMER (kurze unter 5 Ziffern wie Station oder Zimmer → OPTIONAL), Telefon/Fax → TELEFON, E-Mail → EMAIL_ADDRESS,
  Geburtsdatum (mit „geb.“ davor) → DATUM, andere Daten, Alter, Stadt, Land → OPTIONAL, Beruf → INDIREKT.
"""
import glob
import json
import os
import random
import sys
from pathlib import Path

DATEN = Path(os.environ.get("LOKANON_MESSDATEN", Path.home() / "Lokanon" / "messdaten"))

LER_GOLD = {"PER": "PERSON", "RR": "PERSON", "AN": "PERSON", "UN": "ORGANIZATION", "STR": "ADRESSE"}
LER_OPTIONAL = {"ORG", "INN", "GRT", "LD", "ST", "LDS", "MRK", "RS", "LIT"}
OHNE_LEER_DAVOR = set(".,;:!?)]}%") | {"''", "'s"}
OHNE_LEER_DANACH = set("([{„")

GRASCCO = {"NAME_PATIENT": "PERSON", "NAME_DOCTOR": "PERSON", "NAME_RELATIVE": "PERSON", "NAME_EXT": "PERSON",
           "NAME_USERNAME": "PERSON", "NAME_TITLE": "OPTIONAL", "LOCATION_STREET": "ADRESSE",
           "LOCATION_ZIP": "PLZ_ORT", "LOCATION_HOSPITAL": "OPTIONAL", "LOCATION_ORGANIZATION": "ORGANIZATION",
           "ID": "KENNNUMMER", "CONTACT_PHONE": "TELEFON", "CONTACT_FAX": "TELEFON", "CONTACT_EMAIL": "EMAIL_ADDRESS",
           "DATE": "OPTIONAL", "AGE": "OPTIONAL", "LOCATION_CITY": "OPTIONAL", "LOCATION_COUNTRY": "OPTIONAL",
           "PROFESSION": "INDIREKT"}


# ---------------------------------------------------------------------------------------------------- LER
def _ler_saetze(pfad):
    satz = []
    for zeile in open(pfad, encoding="utf-8"):
        zeile = zeile.rstrip("\n")
        if not zeile.strip():
            if satz:
                yield satz
            satz = []
            continue
        tok, _, tag = zeile.rpartition(" ")
        satz.append((tok, tag))
    if satz:
        yield satz


def _initialen(tokens):
    """„F“, „A.“, „B. M.“: vom Gericht schon anonymisiert."""
    return all(len(t.rstrip(".")) <= 2 for t in tokens if t != ".")


def _ler_dokument(saetze):
    """Tokens wieder zu Text zusammensetzen, Spannen aus IOB2."""
    text, spans = [], []
    pos, offen = 0, None  # offen: [start, ende, label, tokens]

    def schliessen():
        nonlocal offen
        if offen:
            s, e, lab, toks = offen
            if lab in LER_GOLD:
                ziel = "OPTIONAL" if lab in ("PER", "RR", "AN") and _initialen(toks) else LER_GOLD[lab]
                spans.append([s, e, ziel])
            elif lab in LER_OPTIONAL:
                spans.append([s, e, "OPTIONAL"])
        offen = None

    for satz in saetze:
        vorher = ""
        for tok, tag in satz:
            leer = bool(text) and tok not in OHNE_LEER_DAVOR and vorher not in OHNE_LEER_DANACH
            if leer:
                text.append(" ")
                pos += 1
            start = pos
            text.append(tok)
            pos += len(tok)
            if tag.startswith("B-") or (tag.startswith("I-") and (not offen or offen[2] != tag[2:])):
                schliessen()
                offen = [start, pos, tag[2:], [tok]]
            elif tag.startswith("I-"):
                offen[1] = pos
                offen[3].append(tok)
            else:
                schliessen()
            vorher = tok
        schliessen()
        text.append("\n")
        pos += 1
    return "".join(text), spans


def ler(n_test=150, n_train=1200, je_dok=25, seed=7):
    saetze = list(_ler_saetze(DATEN / "ler" / "ler.conll"))
    bloecke = [saetze[i:i + je_dok] for i in range(0, len(saetze), je_dok)]
    grenze = int(len(bloecke) * 0.8)  # die letzten 20 % sind nur zum Messen da, nie zum Trainieren
    rnd = random.Random(seed)

    def relevant(b):
        return any(tag[2:] in LER_GOLD for s in b for _, tag in s)

    def schreiben(name, idx, n):
        # zwei Drittel Abschnitte mit Namen/Firmen/Adressen, ein Drittel beliebige (für Fehlalarme)
        mit = [i for i in idx if relevant(bloecke[i])]
        rnd.shuffle(mit)
        rest = list(idx)
        rnd.shuffle(rest)
        wahl = sorted(set(mit[: n * 2 // 3]) | set(rest[: n - n * 2 // 3]))
        with open(DATEN / name, "w", encoding="utf-8") as fh:
            for i in wahl:
                text, spans = _ler_dokument(bloecke[i])
                fh.write(json.dumps({"datei": f"LER-{i:04d}", "familie": "urteil", "seiten": max(1, len(text) // 3000),
                                     "text": text, "spans": spans}, ensure_ascii=False) + "\n")
        return len(wahl)

    a = schreiben("ler_test.jsonl", range(grenze, len(bloecke)), n_test)
    b = schreiben("ler_train.jsonl", range(grenze), n_train)
    print(f"LER: {len(saetze)} Sätze, {len(bloecke)} Abschnitte → {a} zum Messen, {b} zum Trainieren")


# ---------------------------------------------------------------------------------------------------- GraSCCo
def _grascco_dokument(pfad):
    d = json.load(open(pfad, encoding="utf-8"))
    fs = d["%FEATURE_STRUCTURES"]
    text = next(f for f in fs if f["%TYPE"] == "uima.cas.Sofa")["sofaString"]
    spans = []
    for f in fs:
        if f["%TYPE"] != "webanno.custom.PHI" or "kind" not in f:
            continue
        s, e = f.get("begin", 0), f["end"]
        lab = GRASCCO.get(f["kind"], "OPTIONAL")
        if f["kind"] == "ID" and sum(ch.isdigit() for ch in text[s:e]) < 5:
            lab = "OPTIONAL"  # Station, Zimmer, Ambulanz ("A23", "Zi: 119"): kaum identifizierend
        if f["kind"] == "DATE" and any(w in text[max(0, s - 20):s].lower() for w in ("geb", "geboren", "*")):
            lab = "DATUM"
        spans.append([s, e, lab])
    return text, sorted(spans)


def grascco():
    pfade = sorted(glob.glob(str(DATEN / "grascco" / "phi_json" / "*" / "*.json")))
    test = {p for i, p in enumerate(pfade) if i % 3 == 0}  # jedes dritte Dokument nur zum Messen
    n = {"test": 0, "train": 0}
    with open(DATEN / "grascco_test.jsonl", "w", encoding="utf-8") as ft, \
            open(DATEN / "grascco_train.jsonl", "w", encoding="utf-8") as fr:
        for p in pfade:
            text, spans = _grascco_dokument(p)
            name = Path(p).name.split(".")[0]
            zeile = json.dumps({"datei": f"GraSCCo-{name}", "familie": "arztbrief",
                                "seiten": max(1, len(text) // 3000), "text": text, "spans": spans},
                               ensure_ascii=False) + "\n"
            (ft if p in test else fr).write(zeile)
            n["test" if p in test else "train"] += 1
    print(f"GraSCCo: {len(pfade)} Arztbriefe → {n['test']} zum Messen, {n['train']} zum Trainieren")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ler()
    grascco()
