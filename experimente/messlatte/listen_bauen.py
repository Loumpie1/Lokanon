"""Wortlisten aus Wikidata (CC0) für anonymizer/daten bauen: medizinische Begriffe und zusätzliche Vornamen.

Rohdaten (SPARQL-Abfragen, siehe LIESMICH.md) unter %USERPROFILE%\\Lokanon\\messdaten\\wikidata:
  P267 ATC-Code, Q28885102 Arzneimittel, P3345 RxNorm  → Wirkstoffe und Handelsnamen
  P494 ICD-10, P7807 ICD-11, P486 MeSH, P1323 TA98, P4338 LOINC → Krankheiten, Anatomie, Laborwerte
  vn_Q12308941/Q11879590/Q3409032 → männliche, weibliche, geschlechtsneutrale Vornamen

    python experimente/messlatte/listen_bauen.py

Eigennamen in Krankheitsbezeichnungen ("Alzheimer-Krankheit", "Morbus Crohn") kommen nicht in die Medizinliste,
damit ein Patient namens Parkinson weiter erkannt wird. Vornamen, die gewöhnliche deutsche Wörter sind ("Rose",
"Hope"), kommen nicht in die Vornamenliste.
"""
import csv
import gzip
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from anonymizer import lexikon  # noqa: E402

ROH = Path(os.environ.get("LOKANON_MESSDATEN", Path.home() / "Lokanon" / "messdaten")) / "wikidata"
ZIEL = ROOT / "anonymizer" / "daten"
ARZNEI = ["P267", "Q28885102", "P3345"]
MEDIZIN = ["P494", "P7807", "P486", "P1323", "P4338"]
ENDUNGEN = ("itis", "ose", "osis", "om", "oms", "ome", "omen", "ie", "ien", "ämie", "algie", "ektomie", "tomie", "skopie",
            "graphie", "grafie", "plastik", "pathie", "urie", "penie", "zytose", "ismus", "ase", "in", "ol", "al", "id",
            "at", "on", "an", "ung", "sion", "tion", "ität", "isch", "al", "är", "ös", "iv", "ell")
EPONYM_RX = re.compile(r"(?:Morbus|M\.)\s+([A-ZÄÖÜ][\wäöüß]+)|([A-ZÄÖÜ][\wäöüß]+)(?:-|\s)?(?:Syndrom|Krankheit|Erkrankung|"
                       r"Zeichen|Reflex|Test|Tumor|Zyste|Operation|Plastik|Fraktur|Linie|Formel|Klassifikation|Score|"
                       r"Skala|Lähmung|Phänomen|Anomalie|Ulkus|Ödem|Kontraktur|Typ)\b|([A-ZÄÖÜ][\wäöüß]+)['’]s?\b|"
                       r"([A-ZÄÖÜ][\wäöüß]+)sche[nmrs]?\b")
TOKEN_RX = re.compile(r"[A-Za-zÄÖÜäöüßéèàáíóúâêîôûçñ]+")


def labels(datei):
    p = ROH / f"{datei}.csv"
    with open(p, encoding="utf-8", newline="") as fh:
        r = csv.reader(fh)
        next(r, None)
        for zeile in r:
            if zeile:
                yield zeile[0]


def ist_namensform(w):
    return lexikon.ist_name(w) or lexikon.ist_name(w.capitalize())


def medizin():
    eponyme = set()
    for d in MEDIZIN + ARZNEI:
        for lab in labels(d):
            for m in EPONYM_RX.finditer(lab):
                eponyme.add(next(g for g in m.groups() if g).lower())
    woerter = set()
    for d in ARZNEI:
        for lab in labels(d):
            for t in TOKEN_RX.findall(lab):
                if len(t) >= 4 and not ist_namensform(t) and t.lower() not in eponyme:
                    woerter.add(t.lower())
    klein = {t for d in MEDIZIN for lab in labels(d) for t in TOKEN_RX.findall(lab) if t[:1].islower()}
    for d in MEDIZIN:
        for lab in labels(d):
            for t in TOKEN_RX.findall(lab):
                low = t.lower()
                if len(t) < 4 or ist_namensform(t) or low in eponyme:
                    continue
                if t[:1].islower() or low in klein or low.endswith(ENDUNGEN) or (len(t) >= 8 and t.isupper() is False):
                    woerter.add(low)
    return woerter, eponyme


def vornamen():
    out = set()
    for q in ("Q12308941", "Q11879590", "Q3409032"):
        for lab in labels(f"vn_{q}"):
            lab = lab.strip()
            if not re.fullmatch(r"[A-ZÄÖÜ][a-zäöüßéèàáíóúâêîôûçñ]{2,}(?:-[A-ZÄÖÜ][a-zäöüßéèàáíóúâêîôûçñ]{2,})?", lab):
                continue
            if lexikon.ist_vorname(lab) or not (lexikon.ist_wort(lab) or lexikon.ist_wort(lab.lower())):
                out.add(lab)
    return out - set(lexikon._liste("vornamen"))


def schreiben(name, woerter):
    with gzip.open(ZIEL / f"{name}.txt.gz", "wt", encoding="utf-8") as fh:
        fh.write("\n".join(sorted(woerter)) + "\n")
    print(f"{name}: {len(woerter)} Einträge")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    med, epo = medizin()
    schreiben("medizin", med)
    print(f"  ausgelassene Eigennamen in Krankheitsbezeichnungen: {len(epo)}")
    schreiben("vornamen_wikidata", vornamen())
