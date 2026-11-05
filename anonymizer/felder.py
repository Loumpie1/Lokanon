"""Felder in Formularen und Tabellen: Bezeichnung → Wert ("Name | Koch", "Kundennummer K-20419",
"Steuer-ID | SV-Nummer" über der Wertezeile). Die Bezeichnung selbst wird nie markiert.

Drei Wege, alle nur mit passender Wertform (Nummer braucht Ziffern, Name großgeschriebene Wörter …):
  in der Zeile     "Kundennummer K-20419", "Versichertennr.: F703815524", "Name: Jan Becker"
  Tabellenzeile    Bezeichnung in einer Zelle, Wert(e) in den Zellen rechts daneben
  Tabellenkopf     Bezeichnungen in einer Zeile, Werte in derselben Spalte der folgenden Zeilen
Zellen trennt files.SPALTE (" | "), siehe files.read_document und ocr.
"""
from __future__ import annotations

import re

from .recognizers_de import DATUM_ALLE_RX, RECHTSFORMEN

SCORE = 0.85  # "sicher": Bezeichnung + passende Wertform

_PERSON_ROLLEN = [
    "versicherte", "versicherter", "versicherungsnehmer", "versicherungsnehmerin", "patient", "patientin",
    "arbeitnehmer", "arbeitnehmerin", "mitarbeiter", "mitarbeiterin", "halter", "halterin", "fahrzeughalter",
    "fahrer", "fahrerin", "betroffene", "betroffener", "kontoinhaber", "kontoinhaberin", "vollmachtgeber",
    "vollmachtgeberin", "antragsteller", "antragstellerin", "zeuge", "zeugin", "mieter", "mieterin", "vermieter",
    "vermieterin", "erblasser", "erblasserin", "ehegatte", "ehegattin", "ehefrau", "ehemann", "kind", "kunde",
    "kundin", "auftraggeber", "auftraggeberin", "empfänger", "empfängerin", "schuldner", "schuldnerin",
    "gläubiger", "gläubigerin", "geschädigte", "geschädigter", "unterhaltspflichtige", "unterhaltspflichtiger",
]
# (Bezeichnungen, Entität, Wertform)
FELDER = [
    (["name", "nachname", "familienname", "geburtsname", "vorname", "vornamen", "zuname", "name, vorname",
      "vorname, name", "name/vorname", "vor- und nachname", "vor- und zuname", "vollständiger name"], "PERSON", "name"),
    (_PERSON_ROLLEN, "PERSON", "name_oder_firma"),
    (["arbeitgeber", "firma", "unternehmen", "dienstherr"], "ORGANIZATION", "name_oder_firma"),
    (["geburtsdatum", "geb.-datum", "geb.datum", "geb. am", "geboren am", "geburtstag", "sterbedatum", "todestag",
      "verstorben am", "todesdatum", "geb.dat.", "geb.-dat.", "geb. dat.", "geb.am", "geburtsdat."], "DATUM", "datum"),
    (["versicherten-nr.", "versichertennr.", "versichertennummer", "krankenversichertennummer", "kv-nr.",
      "kv-nummer", "kvnr"], "DE_HEALTH_INSURANCE", "nummer"),
    (["sv-nummer", "sv-nr.", "sv nr.", "svnr.", "sv-nr", "sozialversicherungsnummer", "rentenversicherungsnummer", "rv-nummer", "rv-nr.",
      "versicherungsnummer"], "DE_SOCIAL_SECURITY", "nummer"),
    (["versicherungsschein-nr.", "versicherungsscheinnummer", "versicherungsschein", "vertragsnummer", "vertrags-nr.",
      "vertragsnr.", "vertrag", "vertrag nr.", "police", "policennummer", "police-nr.", "schadennummer", "schaden-nr.",
      "schadennr.", "schaden-nummer", "schadenummer"], "VERSICHERUNGSNR", "nummer"),
    (["kundennummer", "kunden-nr.", "kundennr.", "kd.-nr.", "kd-nr.", "kd.nr.", "kd. nr.", "mitgliedsnummer",
      "mitglieds-nr.", "mitgliedsnr.", "fallnummer", "fall-nr.", "fallnr.", "patientennummer", "patienten-nr.",
      "pat.-nr.", "kassenzeichen", "vorgangsnummer", "vorgangs-nr.", "zählernummer", "zähler-nr.",
      "personenkennziffer", "mandantennummer", "mandanten-nr.",
      # Krankenhaus und Labor
      "fallzahl", "fall-zahl", "fn", "piz", "pat.-id", "patienten-id", "patientenid", "pid", "e-nr.", "einsende-nr.",
      "eingangs-nr.", "eingangsnummer", "auftrags-nr.", "auftragsnummer", "labor-nr.", "labornummer", "befund-nr.",
      "befundnummer", "histo-nr.", "h-nr.", "hnr.", "aufnahme-nr.", "aufnahmenummer", "probennummer", "proben-nr."],
     "KENNNUMMER", "nummer"),
    (["personalnummer", "personal-nummer", "personal-nr.", "personalnr.", "pers.-nr.", "pers.nr.", "pers-nr.",
      "mitarbeiternummer", "mitarbeiter-nr.", "pnr."], "PERSONALNR", "nummer"),
    (["steuer-id", "steuer-idnr.", "steuer-id-nr.", "steuerliche identifikationsnummer", "identifikationsnummer",
      "idnr.", "steuer-identifikationsnummer"], "DE_TAX_ID", "nummer"),
    (["steuernummer", "st.-nr.", "steuer-nr.", "stnr."], "DE_TAX_NUMBER", "nummer"),
    (["führerschein-nr.", "führerscheinnummer", "führerschein nr.", "führerschein"], "FUEHRERSCHEIN", "nummer"),
    (["fahrzeug-ident.-nr.", "fahrzeug-identnummer", "fahrzeugidentifikationsnummer", "fahrgestellnummer",
      "fahrgestell-nr.", "fin", "vin"], "FIN", "nummer"),
    (["kennzeichen", "amtl. kennzeichen", "amtliches kennzeichen", "kfz-kennzeichen", "pol. kennzeichen"], "KFZ",
     "nummer"),
    (["kontonummer", "konto-nr.", "kontonr.", "kto.-nr.", "kto-nr.", "depot-nr.", "depotnummer"], "KONTONUMMER",
     "nummer"),
    (["arzt-nr.", "arztnummer", "lanr", "lebenslange arztnummer"], "DE_LANR", "nummer"),
    (["betriebsstätten-nr.", "betriebsstättennummer", "bsnr"], "DE_BSNR", "nummer"),
    (["personalausweis-nr.", "personalausweisnummer", "ausweisnummer", "ausweis-nr."], "DE_ID_CARD", "nummer"),
    (["reisepass-nr.", "reisepassnummer", "passnummer", "pass-nr."], "DE_PASSPORT", "nummer"),
]
_BEZEICHNUNGEN = sorted(((b, ent, form) for namen, ent, form in FELDER for b in namen), key=lambda t: -len(t[0]))
_BEZ_INDEX = {b: (ent, form) for b, ent, form in _BEZEICHNUNGEN}

# Typische Spaltenköpfe: stehen sie rechts neben einer Bezeichnung, ist die Zeile ein Tabellenkopf, kein Wert
_KOPFWOERTER = {"menge", "preis", "einzelpreis", "gesamtpreis", "betrag", "anzahl", "einheit", "summe", "gesamt",
                "bemerkung", "bemerkungen", "art", "typ", "wert", "status", "zeitraum", "uhrzeit", "rolle", "funktion",
                "beruf", "geschlecht", "staatsangehörigkeit", "familienstand", "verhältnis", "beziehung", "kontakt",
                "unterschrift", "datum", "ort", "nr.", "lfd. nr.", "pos.", "position", "anteil", "kosten"}
_TITEL = {"herr", "herrn", "frau", "dr.", "prof.", "med.", "dent.", "jur.", "dipl.-ing.", "dipl.-psych.", "dipl.-kfm.",
          "familie", "fam."}
_PARTIKEL = {"von", "van", "de", "zu", "der", "den", "vom", "zum", "di", "da", "el", "al", "und"}
_RECHTSFORM_RX = re.compile(rf"(?<![\wäöüß])(?:{RECHTSFORMEN})(?![\wäöüß])")
_TOK = r"(?:[A-Za-z]{0,4}[-/]?\d[\dA-Za-z\-/.]*|[A-Z]{1,4})"
_NUMMER_RX = re.compile(rf"{_TOK}(?:[ ]{_TOK}){{0,5}}")
_BETRAG_RX = re.compile(r"-?\d{1,3}(?:[.\s]\s?\d{3})*\s?,\s?\d{2}\s?(?:€|EUR)?")
_DATUM_RX = re.compile(DATUM_ALLE_RX + r"|\b\d{1,2}[./]\d{1,2}[./]\d{2}(?:\d{2})?(?!\d)|\b\d{4}-\d{2}-\d{2}\b")
# "Name: …" im Fließtext nur mit Doppelpunkt; Nummern und Daten auch ohne ("Kundennummer K-20419")
_INLINE_RX = re.compile(
    r"(?<![\wäöüß\-])(?P<bez>" + "|".join(re.escape(b) for b, _e, _f in _BEZEICHNUNGEN) + r")(?:(?<=\.)(?=\d)|(?![\wäöüß\-]))"
    r"(?P<sep>[ \t]*:[ \t]*|[ \t]+|(?<=\.)(?=\d))", re.IGNORECASE)


def _bezeichnung(zelle: str) -> tuple[str, str] | None:
    """(Entität, Wertform), wenn die Zelle eine Feldbezeichnung ist ("Name, Vorname des Versicherten",
    "Geburtsdatum Fahrer", "Versicherungsnehmer Name")."""
    z = re.sub(r"\s+", " ", zelle.strip().rstrip(":").strip()).lower()
    if not z or len(z) > 45 or len(z.split()) > 6 or any(ch.isdigit() for ch in z):
        return None
    if z in _BEZ_INDEX:
        return _BEZ_INDEX[z]
    for b, ent, form in _BEZEICHNUNGEN:
        if len(b) >= 3 and (re.match(re.escape(b) + r"(?=[ ,(])", z) or re.search(r"(?<=[ ,/])" + re.escape(b) + r"$", z)):
            return ent, form
    return None


def _name_span(s: str) -> tuple[int, int] | None:
    """Personenname am Anfang von s (ohne Anrede/Titel): 1–4 großgeschriebene Wörter, auch "Koch, Stefanie"."""
    teile = s.split(",")
    kandidaten = [s] if len(teile) == 2 and len(teile[1].split()) <= 2 else []
    kandidaten.append(teile[0])
    for k in kandidaten:
        woerter = list(re.finditer(r"[^\s,]+", k))
        while woerter and woerter[0].group().lower() in _TITEL:
            woerter.pop(0)
        if not 1 <= len(woerter) <= (6 if any(w.group() == "und" for w in woerter) else 4):
            continue
        ok = True
        for w in woerter:
            t = w.group()
            if t.lower() in _PARTIKEL:
                continue
            kern = t.replace("-", "").replace("'", "").replace("’", "")
            initiale = len(t) == 2 and t.endswith(".") and t[0].isupper()
            if not (initiale or (t[0].isupper() and kern.isalpha() and len(kern) >= 2)):
                ok = False
                break
        if ok and woerter[-1].group().lower() not in _PARTIKEL:
            return woerter[0].start(), woerter[-1].end()
    return None


def _wert(s: str, form: str, entity: str) -> tuple[int, int, str] | None:
    """(Start, Ende, Entität) des Werts am Anfang von s, wenn er zur Wertform passt."""
    if form == "datum":
        m = _DATUM_RX.match(s)
        return (m.start(), m.end(), entity) if m else None
    if form == "nummer":
        m = _NUMMER_RX.match(s)
        if not m:
            return None
        wert = m.group()
        while wert and re.search(r"[ ][A-Z]{1,4}$", wert):  # angehängte Wörter ("… 120 AOK") abschneiden
            wert = wert[:wert.rindex(" ")]
        wert = wert.rstrip(".-/")
        if sum(ch.isdigit() for ch in wert) < 3 or len(wert) > 32 or _BETRAG_RX.fullmatch(wert):
            return None
        if _DATUM_RX.fullmatch(wert):
            return None
        return m.start(), m.start() + len(wert), entity
    if form == "name_oder_firma":
        m = _RECHTSFORM_RX.search(s)
        if m and "," not in s[:m.start()]:
            return 0, m.end(), "ORGANIZATION"
        if entity == "ORGANIZATION":
            return None
    sp = _name_span(s)
    return (sp[0], sp[1], "PERSON") if sp else None


def _zellen(zeile: str, start: int) -> list[tuple[int, str]]:
    """(Offset, Text) je Zelle einer Zeile."""
    out, pos = [], 0
    for teil in zeile.split("|"):
        lead = len(teil) - len(teil.lstrip())
        out.append((start + pos + lead, teil.strip()))
        pos += len(teil) + 1
    return out


def feld_treffer(text: str, entities: list[str] | set[str]) -> list:
    from .engine import Finding

    erlaubt = set(entities)
    out: list = []

    from .engine import FIELD_LABEL_WORDS, NER_STOPWORDS

    def neu(start: int, s: str, form: str, entity: str, bez: str) -> None:
        k = s.strip().rstrip(":").lower()
        if k in NER_STOPWORDS or k in FIELD_LABEL_WORDS or k in _KOPFWOERTER or k.rstrip(".") in _KOPFWOERTER:
            return  # Spaltenkopf statt Wert ("Zeuge | Anschrift | Telefon")
        w = _wert(s, form, entity)
        if w and w[2] in erlaubt and w[1] > w[0]:
            grund = "Formularfeld „" + re.sub(r"\s+", " ", bez.strip().rstrip(":")) + "“"
            out.append(Finding(start + w[0], start + w[1], w[2], SCORE, text[start + w[0]:start + w[1]], quelle="feld",
                               grund=grund))

    zeilen, pos = [], 0
    for z in text.split("\n"):
        zeilen.append((pos, z))
        pos += len(z) + 1
    zellen = [_zellen(z, p) for p, z in zeilen]
    for zi, cells in enumerate(zellen):
        bez = [_bezeichnung(c) for _o, c in cells]
        if len(cells) >= 2:
            vorher = len(out)
            # Tabellenzeile: Bezeichnung, Werte rechts daneben (erste Spalte: alle Zellen der Zeile)
            for ci, b in enumerate(bez):
                if not b:
                    continue
                ziele = range(ci + 1, len(cells)) if ci == 0 else range(ci + 1, min(ci + 2, len(cells)))
                for cj in ziele:
                    if bez[cj]:
                        break
                    neu(cells[cj][0], cells[cj][1], b[1], b[0], cells[ci][1])
            # Tabellenkopf: Werte in derselben Spalte der folgenden Zeilen (gleiche Spaltenzahl)
            # (mindestens zwei Bezeichnungen, oder eine in einer Kopfzeile ohne Werte: "Personalnummer | Steuerklasse")
            n_bez = sum(1 for b in bez if b)
            kopf = n_bez >= 2 or (n_bez and len(cells) >= 3 and len(out) == vorher
                                  and not any(ch.isdigit() for _o, c in cells for ch in c))
            if kopf:
                for nz in zellen[zi + 1:zi + 4]:
                    if len(nz) != len(cells) or any(_bezeichnung(c) for _o, c in nz):
                        break
                    for ci, b in enumerate(bez):
                        if b:
                            neu(nz[ci][0], nz[ci][1], b[1], b[0], cells[ci][1])
    # In der Zeile: Bezeichnung, dann Wert
    for m in _INLINE_RX.finditer(text):
        ent, form = _BEZ_INDEX[m.group("bez").lower()]
        rest_ende = text.find("\n", m.end())
        rest = text[m.end():rest_ende if rest_ende >= 0 else len(text)].split("|")[0]
        if form in ("name", "name_oder_firma") and ":" not in m.group("sep"):
            # Namen sonst nur nach Doppelpunkt ("Name des Antragstellers", "Kind und Mutter"). Ausnahme: Formular
            # ohne Doppelpunkt mit "Nachname, Vorname" ("Name, Vorname des Versicherten Engel, Sabine")
            q = re.fullmatch(r"(?:(?:des|der)\s+[A-ZÄÖÜ]\w+\s+)?([A-ZÄÖÜ][\w'’\-]+,\s*[A-ZÄÖÜ][\w'’\-]+)\s*", rest)
            if form == "name" and q:
                neu(m.end() + q.start(1), q.group(1), form, ent, m.group("bez"))
            continue
        if form in ("name", "name_oder_firma"):
            rest = re.split(r"[;(]|\s{2,}", rest)[0]
        neu(m.end(), rest, form, ent, m.group("bez"))
    return out
