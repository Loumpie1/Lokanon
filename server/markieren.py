"""Markieren und im Rest suchen (Anforderung docs/anforderungen/markieren-und-suchen.md).

Die Nutzerin markiert in der Dokumentansicht eine Stelle, die Lokanon übersehen hat. Hier stehen die reinen
Textfunktionen dazu: Auswahl an Wortgrenzen ausrichten, die Art vorschlagen (M3) und alle Vorkommen im Vorgang finden
(M4), samt Beugungen, Silbentrennung, Zeilenumbruch und Ligaturen. Reine Textsuche, kein Modell.
"""
from __future__ import annotations

import html
import re

from anonymizer.engine import SALUTATIONS, TITLES, namensteile
from anonymizer.recognizers_de import RECHTSFORMEN

ARTEN = [("PERSON", "Person"), ("ORGANIZATION", "Firma oder Einrichtung"), ("ADRESSE", "Adresse"),
         ("PLZ_ORT", "Ort"), ("EMAIL_ADDRESS", "E-Mail"), ("TELEFON", "Telefon"), ("KENNNUMMER", "Kennnummer"),
         ("DATUM", "Datum"), ("MANUELL", "Sonstiges")]
WARNGRENZE = 50
_BRANCHE = re.compile(r"(?i)\b(?:spedition|autohaus|bäckerei|praxis|kanzlei|apotheke|logistik|bau|handel|service|"
                      r"versicherung|bank|sparkasse|klinik|verlag|werkstatt|gruppe|holding|immobilien|hausverwaltung)")
_STRASSE = re.compile(r"(?i)(?:stra(?:ß|ss)e|str\.|weg|allee|platz|ring|gasse|damm|ufer)\s*\d")
_LIGATUREN = {"ff": "(?:ff|ﬀ)", "fi": "(?:fi|ﬁ)", "fl": "(?:fl|ﬂ)"}
# Zwischen zwei Buchstaben darf eine Silbentrennung stehen ("Spedi-⏎tion", weiches Trennzeichen)
_TRENNUNG = r"(?:­|-[ \t]*\n[ \t]*)?"


def ausrichten(text: str, s: int, e: int) -> tuple[int, int]:
    """Auswahl an Wortgrenzen ausrichten. Abgeschnittene Wortränder bis 2 Zeichen gelten als ungenaue Maus und werden
    ergänzt; wer bewusst mitten im Wort markiert (mehr als 2 Zeichen abgeschnitten), behält die genaue Auswahl."""
    s, e = max(0, s), min(len(text), e)
    while s < e and text[s].isspace():
        s += 1
    while e > s and text[e - 1].isspace():
        e -= 1
    a = s
    while a > 0 and text[a - 1].isalnum():
        a -= 1
    b = e
    while b < len(text) and text[b].isalnum():
        b += 1
    if s - a <= 2:
        s = a
    if b - e <= 2:
        e = b
    return s, e


def art_vorschlag(text: str, s: int, e: int) -> str:
    """Art aus Form und Umgebung: Anrede davor → Person, Rechtsform/Branche → Firma, Muster → passende Art."""
    wert = text[s:e].strip()
    davor = text[max(0, s - 24):s].split()
    if "@" in wert:
        return "EMAIL_ADDRESS"
    if re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{2,4}", wert):
        return "DATUM"
    if _STRASSE.search(wert):
        return "ADRESSE"
    if re.fullmatch(r"\d{5}\s+\S.*", wert):
        return "PLZ_ORT"
    if re.fullmatch(r"[+\d][\d\s/()-]{6,}", wert):
        return "TELEFON"
    if sum(c.isdigit() for c in wert) >= 3:
        return "KENNNUMMER"
    if re.search(rf"(?<!\w)(?:{RECHTSFORMEN})(?!\w)", wert) or _BRANCHE.search(wert):
        return "ORGANIZATION"
    if davor and davor[-1].lower().rstrip(".") in {x.rstrip(".") for x in SALUTATIONS + TITLES}:
        return "PERSON"
    if wert[:1].isupper():
        from anonymizer import lexikon

        if all(lexikon.ist_name(w.strip(".,")) or not lexikon.ist_wort(w.strip(".,")) for w in wert.split()):
            return "PERSON"
    return "MANUELL"


def such_regex(begriff: str, beugung: bool) -> re.Pattern:
    """Ganze Wörter, Groß-/Kleinschreibung egal, Leerraum flexibel (auch Zeilenumbruch), Silbentrennung zwischen
    Buchstaben, Ligaturen; mit beugung auch Genitiv und Adjektivformen ("Noltes", "der Nolte'schen")."""
    teile = []
    for tok in begriff.split():
        zeichen = []
        i = 0
        while i < len(tok):
            paar = tok[i:i + 2].lower()
            if paar in _LIGATUREN:
                zeichen.append(_LIGATUREN[paar])
                i += 2
            else:
                zeichen.append(re.escape(tok[i]))
                i += 1
        teile.append(_TRENNUNG.join(zeichen))
    kern = r"\s+".join(teile)
    endung = r"(?:s|es|['’]s|['’]sche[nmrs]?)?" if beugung else ""
    return re.compile(rf"(?<!\w){kern}{endung}(?!\w)", re.IGNORECASE)


def _kontext(text: str, s: int, e: int, breite: int = 50) -> str:
    vor = text[max(0, s - breite):s].replace("\n", " ")
    nach = text[e:e + breite].replace("\n", " ")
    return (("…" if s > breite else "") + html.escape(vor) + "<b>" + html.escape(text[s:e]) + "</b>" + html.escape(nach)
            + ("…" if e + breite < len(text) else ""))


def fundstellen(docs: list, begriff: str, art: str, nur_dok: int | None = None) -> dict:
    """Alle Vorkommen von begriff in den Dokumenten (oder nur in nur_dok). Bei Personen mit mehreren Wörtern kommen
    die Namensteile als zweite, abwählbare Gruppe dazu („Herrn Günther“ zu „Moritz Günther“). Stellen, die schon zu
    einem Treffer gehören, tragen dessen Platzhalter in "schon" und werden nicht doppelt angelegt."""
    beugung = art in ("PERSON", "ORGANIZATION")
    gruppen = [("voll", such_regex(begriff, beugung))]
    if art == "PERSON" and len(begriff.split()) > 1:
        gruppen += [("teil", such_regex(t, True)) for t in namensteile(begriff)]
    dateien, gesamt = [], 0
    for di, d in enumerate(docs):
        if nur_dok is not None and di != nur_dok:
            continue
        belegt: list[tuple[int, int]] = []
        stellen = []
        for gruppe, rx in gruppen:
            for m in rx.finditer(d.text):
                if any(m.start() < b and m.end() > a for a, b in belegt):
                    continue  # Namensteil innerhalb eines vollen Treffers
                belegt.append((m.start(), m.end()))
                schon = ""
                for i, f in enumerate(d.findings):
                    if f.active and m.start() < f.end and m.end() > f.start:
                        schon = d.schluessel.get(i, "") or "markiert"
                        break
                stellen.append({"s": m.start(), "e": m.end(), "text": m.group(), "gruppe": gruppe, "schon": schon,
                                "ctx": _kontext(d.text, m.start(), m.end())})
        stellen.sort(key=lambda x: x["s"])
        if stellen:
            dateien.append({"i": di, "name": d.name, "stellen": stellen})
            gesamt += len(stellen)
    return {"begriff": begriff, "art": art, "gesamt": gesamt, "warnung": gesamt > WARNGRENZE, "dateien": dateien}
