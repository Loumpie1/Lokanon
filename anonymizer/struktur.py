"""Regeln aus dem Aufbau von Briefen, Befunden und Formularen, die das Modell oft übersieht.

  Geburtsdatum mit Stern      "Beate Albers (* 4.4.1997)", "geb.am: 21/06/1967", "Geb.Dat.: 21.06.67"
  Nachname, Vorname           "Patientin: Gebauer, Gerlinde", "FRITZLE, Fridolin" (Vorname aus der Namensliste)
  Titel mit Initialen         "Prof. Dr. med. V. Jäger", "Dr.in Mersiha Kasupovic-Braun", "OA PD Dr. med M. Kienböck"
  Anrede mit Initiale         "Frau I. ist eine 82-jährige Patientin"
  Verfasserzeile              "Geschrieben von Amadea Leber", "gez. Dr. B. Supanic", "Untersuchung durch: …"
  Postleitzahl mit Land       "A-3336 St. Johann am Bergle", "CH-8001 Zürich"
  Straße im Anschriftblock    "Sonnblick 32" in der Zeile über oder unter "A-3336 …"
  Unterschriftenblock         drei und mehr Zeilen mit je nur einem Namen ("Gallner⏎Brune⏎M. Trümner" unter Urteilen)

Alle Regeln liefern Finding-Objekte; engine.detect prüft sie wie andere Treffer (Stopplisten, erlaubte Begriffe).
"""
from __future__ import annotations

import re

from . import lexikon

# Datum in den in Befunden üblichen Schreibweisen, auch mit zweistelligem Jahr und Schrägstrichen
_DATUM = r"(?:\d{1,2}\.[ \t]?\d{1,2}\.[ \t]?(?:\d{4}|\d{2})|\d{1,2}/\d{1,2}/(?:\d{4}|\d{2})|\d{4}-\d{2}-\d{2})(?!\d)"
GEBURT_RX = re.compile(r"(?:(?<![\w*])\*[ \t]?|(?<![\w])[Gg]eb(?:oren|urtsdatum|\.?[ \t]?-?Dat(?:um|\.)?|\.)?"
                       r"(?:[ \t]?am)?[ \t]*:?[ \t]*)(" + _DATUM + r")")

_GROSS = r"[A-ZÄÖÜ]"
_KLEIN = r"[a-zäöüßéèàáíóúâêîôûçñăâîșțşğı]"
_WORT = _GROSS + r"(?:" + _KLEIN + r"|['’\-]" + _GROSS + r")+"
NACHNAME_VORNAME_RX = re.compile(r"(?<![\wäöüß\-,])(" + _GROSS + r"[A-Za-zÄÖÜäöüß'’\-]+),[ \t]+(" + _WORT + r")(?![\wäöüß\-])")

_TITEL = (r"(?:(?:(?:Ao\.|o\.)[ \t]?)?Univ\.[ \t]?-?[ \t]?Prof\.|Prof\.|Dr\.?(?:[ \t]?in|ª|a\.)?|Dra\.|Drª|PD|Priv\.[ \t]?-?"
          r"[ \t]?Doz\.|Ass\.[ \t]?Dr\.|Mag\.(?:a\.?)?|Dipl\.-[A-Za-zäöü]+\.?)")
_TITEL_ZUSATZ = (r"(?:[ \t]*(?:Dr\.[ \t]?in|Drª|med\.|dent\.|univ\.|univers\.|rer\.[ \t]?nat\.|phil\.|jur\.|mult\.|"
                 r"habil\.|sc\.|Dr\.|Prof\.|(?:med|PhD|MSc|MBA)(?![\w])))*")
_INITIALEN = r"(?:(?:" + _GROSS + r"[a-z]?\.)[ \t]?){1,2}"
_PARTIKEL = r"(?:dos|de|da|del|von|van|der|zu|di|du|la|le)"
# Titel und Funktionskürzel sind keine Namensteile ("Dr. med. Helmuth Leber     Prof. Dr. …")
_NAMENSTEIL = (r"(?:(?!(?:Dr|Prof|PD|Med|Univ|Priv|Doz|Mag|Dipl|OA|FA|PhD|MSc)(?![a-zäöüß]))" + _WORT +
               r"(?![A-Za-zÄÖÜäöüß]))")
TITEL_NAME_RX = re.compile(
    r"(?<![\w])" + _TITEL + _TITEL_ZUSATZ + r"[ \t]+((?:" + _INITIALEN + r")?" + _NAMENSTEIL +
    r"(?:[ \t]+(?:" + _PARTIKEL + r"[ \t]+)?" + _NAMENSTEIL + r"){0,2})")
ANREDE_INITIALE_RX = re.compile(r"(?<![\w])(?:Herrn?|Frau|Hr\.|Fr\.)[ \t]+(" + _GROSS + r"\.)(?=[\s,;:)]|$)")
VERFASSER_RX = re.compile(
    r"(?i:geschrieben[ \t]von|diktiert[ \t]von|untersuchung[ \t]durch|untersucht[ \t]von|befundet[ \t]von|"
    r"befundung[ \t]durch|unterzeichnet[ \t]von|gez\.|dikt\.[ \t]?arzt|verfasser(?:in)?|sachbearbeiter(?:in)?|"
    r"ansprechpartner(?:in)?|bearbeiter(?:in)?|i\.[ \t]?a\.|i\.[ \t]?v\.)[ \t]*:?[ \t]*"
    r"(?:(?:OA|OÄ|FA|FÄ|Ass\.)[ \t]+)?(?:" + _TITEL + _TITEL_ZUSATZ + r"[ \t]+)?"
    r"((?:" + _INITIALEN + r")?" + _NAMENSTEIL + r"(?:[ \t]+(?:" + _PARTIKEL + r"[ \t]+)?" + _NAMENSTEIL + r"){0,2})")
PLZ_LAND_RX = re.compile(r"(?<![\w\-])(?:A|D|CH|FL|L|I|NL|B)-\d{4,5}(?:[ \t]+|-)" + _GROSS +
                         r"[\wäöüß.\-]*(?:[ \t]+(?:am|an|im|in|bei|ob|\w+\.)?[ \t]*" + _GROSS + r"[\wäöüß.\-]*){0,3}")
_PLZ_ZEILE_RX = re.compile(r"^[ \t]*(?:(?:A|D|CH)-)?\d{4,5}[ \t]+" + _GROSS)
# Wörter ohne Ziffern, dann die Hausnummer ("Sonnblick 32", "Am Hasenstall 4a"); nicht "Personalnummer 004711 …"
_STRASSE_ZEILE_RX = re.compile(r"^[ \t]*(" + _GROSS + r"[A-Za-zÄÖÜäöüß.\-]*(?:[ \t]+[A-Za-zÄÖÜäöüß.\-]+){0,3}[ \t]+"
                               r"\d{1,4}[ \t]?[a-zA-Z]?)[ \t]*,?[ \t]*$")
_FELDENDEN = ("nummer", "nr.", "nr", "klasse", "zeichen", "datum", "kennzahl", "tarif", "stufe", "gruppe", "seite", "summe")
_NAMENSZEILE_RX = re.compile(r"^[ \t]*((?:" + _GROSS + r"\.[ \t]?)?" + _WORT + r"(?:[ \t]+" + _WORT + r")?)[ \t]*$")
_STOPP = {"zimmer", "station", "raum", "haus", "gebäude", "ebene", "seite", "anlage", "tel", "telefon", "fax", "durchwahl",
          "postfach", "befund", "diagnose", "therapie", "labor", "procedere", "visite", "kontrolle", "nachsorge"}


def _finding(s: int, e: int, entity: str, score: float, text: str, grund: str):
    from .engine import Finding

    return Finding(s, e, entity, score, text[s:e], quelle="heuristik", grund=grund)


def _kein_wort(w: str) -> bool:
    w = w.strip(".,")
    for form in {w, w.capitalize()}:
        if lexikon.ist_name(form):
            return True
    return not (lexikon.gewoehnlich(w.capitalize()) or lexikon.ist_medizin(w))


def _name_ok(name: str) -> bool:
    from .engine import NER_STOPWORDS, ROLES

    woerter = [w.strip(".,") for w in name.split() if len(w.strip(".,")) > 1]
    if not woerter:
        return False
    if any(w.lower() in NER_STOPWORDS or w.lower() in ROLES for w in woerter):
        return False
    letzter = woerter[-1]
    return not (letzter.lower() in _STOPP or lexikon.ist_medizin(letzter) and not lexikon.ist_name(letzter))


def struktur_treffer(text: str) -> list:
    out = []
    for m in GEBURT_RX.finditer(text):
        out.append(_finding(m.start(1), m.end(1), "DATUM", 0.85, text, "Geburtsdatum (* oder geb.)"))
    for m in NACHNAME_VORNAME_RX.finditer(text):
        nach, vor = m.group(1), m.group(2)
        if not lexikon.ist_vorname(vor) or len(nach.strip("-'’")) < 2:
            continue
        if nach.lower() in _STOPP or lexikon.ist_medizin(nach) or not (nach.isupper() or _kein_wort(nach)):
            continue  # "Diagnose, Maria …", "Essen, Michael"; großgeschrieben ("CHRIST, Charlotte") gilt als Name
        if not _name_ok(nach + " " + vor):
            continue
        out.append(_finding(m.start(), m.end(), "PERSON", 0.6, text, "Nachname, Vorname"))
    for m in TITEL_NAME_RX.finditer(text):
        if _name_ok(m.group(1)):
            out.append(_finding(m.start(1), m.end(1), "PERSON", 0.6, text, "nach Titel"))
    for m in ANREDE_INITIALE_RX.finditer(text):
        out.append(_finding(m.start(1), m.end(1), "PERSON", 0.5, text, "Anrede mit Initiale"))
    for m in VERFASSER_RX.finditer(text):
        if _name_ok(m.group(1)):
            out.append(_finding(m.start(1), m.end(1), "PERSON", 0.6, text, "Verfasser- oder Unterschriftszeile"))
    for m in PLZ_LAND_RX.finditer(text):
        out.append(_finding(m.start(), m.end(), "PLZ_ORT", 0.85, text, "Postleitzahl mit Landeskennung"))
    # Straße ohne Straßenwort direkt über oder unter der Zeile mit Postleitzahl ("Sonnblick 32")
    zeilen, pos = [], 0
    for z in text.split("\n"):
        zeilen.append((pos, z))
        pos += len(z) + 1
    for i, (_p, z) in enumerate(zeilen):
        if not _PLZ_ZEILE_RX.match(z):
            continue
        for j in (i - 1, i + 1):
            if not 0 <= j < len(zeilen):
                continue
            zp, zz = zeilen[j]
            m = _STRASSE_ZEILE_RX.match(zz)
            if m and len(zz) <= 45 and ":" not in zz and m.group(1).split()[0].lower() not in _STOPP \
                    and not any(w.lower().endswith(_FELDENDEN) for w in m.group(1).split()[:-1]):
                out.append(_finding(zp + m.start(1), zp + m.end(1), "ADRESSE", 0.6, text, "Anschriftblock"))
    out += _unterschriftenblock(text, zeilen)
    return out


def _unterschriftenblock(text: str, zeilen) -> list:
    """Mindestens drei aufeinanderfolgende Zeilen mit je nur einem Namen. Damit Überschriften-Listen ("Diagnose⏎
    Therapie⏎Verlauf") nicht mitkommen, müssen mindestens drei Fünftel der Zeilen eindeutig Namen sein (kein
    gewöhnliches Wort); im Block gelten dann auch "Rose", "Berg", "Volk" als Namen."""
    out, block = [], []

    def eindeutig(m) -> bool:  # mit Initiale ("C. Klar") oder kein gewöhnliches Wort
        return "." in m.group(1) or _kein_wort(m.group(1).split()[-1])

    def abschliessen():
        # Überschriften davor und danach ("Lehrereingruppierung", "Diagnosen") gehören nicht zum Block
        teil = list(block)
        while teil and not eindeutig(teil[0][1]):
            teil.pop(0)
        while teil and not eindeutig(teil[-1][1]):
            teil.pop()
        if len(teil) >= 3:
            if sum(1 for _p, m in teil if eindeutig(m)) * 5 >= len(teil) * 3:
                for zp, m in teil:
                    if _name_ok(m.group(1)):
                        out.append(_finding(zp + m.start(1), zp + m.end(1), "PERSON", 0.55, text,
                                            "Unterschriftenblock"))
        block.clear()

    for zp, z in zeilen:
        m = _NAMENSZEILE_RX.match(z)
        if m and m.group(1).split()[-1].lower() not in _STOPP:
            block.append((zp, m))
        else:
            abschliessen()
    abschliessen()
    return out
