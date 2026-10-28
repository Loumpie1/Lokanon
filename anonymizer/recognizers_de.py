"""Deutsche Erkenner für Presidio.

Zwei Quellen:
1. Die in Presidio eingebauten DE_*-Erkenner (Steuer-ID, Ausweis, Kfz, KVNR, LANR …) – standardmäßig
   deaktiviert, hier registriert.
2. Eigene Muster für alles, was Presidio nicht kennt: Telefon, Adresse, PLZ+Ort, Aktenzeichen,
   FIN, Grundbuch, Versicherungs-/Schadennummern, Kontonummern, Firmen mit Rechtsform, Datum.

Score = Grundvertrauen (0–1). Kontextwörter in der Nähe heben den Score um 0,35 (Presidio-
Kontextverstärkung, siehe engine.build_analyzer). Schwache Muster (Score < 0,4) greifen also nur
mit Kontextwort – so bleiben Fehlalarme bei Zahlenkolonnen aus.
"""
import re

from presidio_analyzer import Pattern, PatternRecognizer
from presidio_analyzer.predefined_recognizers import (
    CreditCardRecognizer,
    DeBsnrRecognizer,
    DeFuehrerscheinRecognizer,
    DeHandelsregisterRecognizer,
    DeHealthInsuranceRecognizer,
    DeIdCardRecognizer,
    DeKfzRecognizer,
    DeLanrRecognizer,
    DePassportRecognizer,
    DeSocialSecurityRecognizer,
    DeTaxIdRecognizer,
    DeTaxNumberRecognizer,
    DeVatIdRecognizer,
    EmailRecognizer,
    IbanRecognizer,
    IpRecognizer,
    UrlRecognizer,
)

LANG = "de"

# Kontextwörter, die ein Datum personenbezogen machen (Geburt, Tod). Presidio vergleicht mit
# spaCy-Lemmata ("verstorben" -> "versterben"), deshalb beide Formen.
DATUM_KONTEXT = ["geboren", "gebären", "geb.", "geb", "geburtsdatum", "geburtstag", "geburt", "verstorben",
                 "versterben", "gestorben", "sterben", "todestag", "sterbedatum", "tod", "todesdatum"]
MONATE = r"(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember|Jan\.|Feb\.|Mär\.|Apr\.|Aug\.|Sept?\.|Okt\.|Nov\.|Dez\.)"
# Datum numerisch ("03.04.2026") oder in Worten ("3. Juni 2025")
DATUM_ALLE_RX = r"\b\d{1,2}\.\s?\d{1,2}\.\s?(?:19|20)\d{2}\b|\b\d{1,2}\.\s?" + MONATE + r"\s(?:19|20)\d{2}\b"

# Rechtsformen für die Firmenerkennung
RECHTSFORMEN = (
    r"GmbH(?:\s*&\s*Co\.?\s*KG)?|gGmbH|AG|KG|KGaA|OHG|GbR|UG(?:\s*\(haftungsbeschränkt\))?|mbH|"
    r"e\.\s?V\.|SE|eG|PartG(?:mbB)?|Partnerschaft(?:sgesellschaft)?|Stiftung|Inc\.|Ltd\.|B\.V\.|S\.A\."
)


def _pr(entity, patterns, context=None):
    return PatternRecognizer(
        supported_entity=entity,
        supported_language=LANG,
        patterns=[Pattern(f"{entity}_{i}", rx, score) for i, (rx, score) in enumerate(patterns)],
        context=context or [],
        # Presidio prüft sonst ohne Groß-/Kleinschreibung – wir brauchen sie (Namen, Kennzeichen)
        global_regex_flags=re.DOTALL | re.MULTILINE,
    )


def german_recognizers():
    return [
        # ---------- Kontakt und Anschrift ----------
        _pr(
            "TELEFON",
            [(r"(?<![\w+])(?:\+49|0049|\(0\d{2,5}\)|0\d{2,5})[\s/\-]?\(?\d[\d\s/\-()]{4,16}\d(?!\d)", 0.6)],
            ["tel", "telefon", "mobil", "handy", "fax", "rufnummer", "erreichbar", "durchwahl"],
        ),
        # Straße + Hausnummer ("Hauptstraße 12", "Kölner Straße 5a", "Am Ring 3")
        _pr(
            "ADRESSE",
            [
                (r"\b(?:[A-ZÄÖÜ][a-zäöüß]+[ \-])?[A-ZÄÖÜ]?[a-zäöüß\-]*"
                 r"(?i:straße|strasse|str\.|weg|allee|platz|gasse|ring|damm|ufer|chaussee|pfad|steig)"
                 r"\s?\d{1,4}\s?[a-zA-Z]?\b", 0.7),
            ],
            ["wohnhaft", "anschrift", "adresse", "straße"],
        ),
        # PLZ + Ort ("45468 Mülheim an der Ruhr", "10115 Berlin")
        _pr(
            "PLZ_ORT",
            [(r"\b\d{5}[ \t]+[A-ZÄÖÜ][a-zäöüß]+"
              r"(?:(?:[ \t](?:an der|am|an|im|in der|ob der|vor der)[ \t]|-)[A-ZÄÖÜ][a-zäöüß]+)?", 0.7)],
        ),
        # ---------- Verfahren und Akten ----------
        _pr(
            "AKTENZEICHEN",
            [
                # Gerichtliches Az.: "14 VI 512/26", "3 O 123/24", "2 StR 45/25"
                (r"(?<![\w/])\d{1,3}\s[A-Z][A-Za-z]{0,4}\s\d{1,6}/\d{2,4}(?![\w/])", 0.5),
                # Kanzlei-/Behördenzeichen: "LP-2026/0417", "VU 2026/14385"
                (r"(?<![\w/])[A-Z]{1,4}[\s\-]?\d{2,4}/\d{3,6}(?![\w/])", 0.3),
                # Nummeriert mit Punkt/Bindestrich: "7.1-552318/26"
                (r"(?<![\w/])\d{1,3}(?:\.\d{1,2})?-\d{4,8}/\d{2,4}(?![\w/])", 0.35),
                # Nackte Nummer mit Jahr: "318/2024" – nur mit Kontext
                (r"(?<![\w/.])\d{2,6}/(?:19|20)?\d{2}(?![\w/])", 0.1),
            ],
            ["aktenzeichen", "az", "az.", "zeichen", "geschäftszeichen", "vorgangsnummer", "vorgang",
             "ur-nr", "urkunde", "urkundenrolle", "verfahren", "registernummer", "nr.", "nr"],
        ),
        # Grundbuch / Kataster
        _pr(
            "GRUNDBUCH",
            [
                (r"\b[A-ZÄÖÜ][a-zäöüß\-]+\s+Blatt\s+\d{1,6}\b", 0.6),
                (r"\bFlurst(?:ück|\.)\s*\d+(?:/\d+)?\b", 0.5),
                (r"\bGemarkung\s+[A-ZÄÖÜ][a-zäöüß\-]+\b", 0.5),
            ],
            ["grundbuch", "grundbuchamt", "kataster", "flur", "eigentum", "grundstück"],
        ),
        # ---------- Fahrzeug ----------
        # Kfz-Kennzeichen ("MH-AB 1234", "E XY 99E"); Bindestrich-Formen sind eindeutiger
        _pr(
            "KFZ",
            [
                (r"(?<![\w-])[A-ZÄÖÜ]{1,3}-[A-Z]{1,2}[\s\-]?\d{1,4}[EH]?(?![\w-])", 0.45),
                (r"(?<![\w-])[A-ZÄÖÜ]{1,3}\s[A-Z]{1,2}\s?\d{1,4}[EH]?(?![\w-])", 0.3),
            ],
            ["kennzeichen", "kfz", "fahrzeug", "auto", "pkw", "lkw", "anhänger", "halter", "zugmaschine",
             "amtl.", "amtliches"],
        ),
        # FIN / VIN: 17 Zeichen ohne I, O, Q, mindestens ein Buchstabe und eine Ziffer
        _pr(
            "FIN",
            [(r"\b(?=[A-HJ-NPR-Z0-9]{17}\b)(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-HJ-NPR-Z0-9]{17}\b", 0.5)],
            ["fin", "vin", "fahrgestellnummer", "fahrzeug-identifizierungsnummer", "fahrzeugidentnummer",
             "fahrzeugidentifizierungsnummer"],
        ),
        # Führerschein-Nr. (z. B. "J010B7XY351") – Presidios Muster greift nur für ein Format
        _pr(
            "FUEHRERSCHEIN",
            [(r"\b[A-Z]\d{2,3}[A-Z0-9]{6,9}\b", 0.2)],
            ["führerschein", "führerschein-nr", "führerscheinnummer", "fahrerlaubnis", "fahrerlaubnisnummer"],
        ),
        # ---------- Versicherung, Konto ----------
        _pr(
            "VERSICHERUNGSNR",
            [(r"(?<![\w-])[A-Z]{1,4}[\s\-]?\d{2,6}[\-/]\d{3,8}(?:[\-/]\d{2,8})?(?![\w-])", 0.25),
             (r"(?<![\w-])\d{2,4}[\-/]\d{4,8}[\-/]\d{2,8}(?![\w-])", 0.2)],
            ["versicherungsschein", "versicherungsschein-nr", "versicherungsnummer", "versicherung",
             "schadennummer", "schaden-nr", "schadensnummer", "vertragsnummer", "police", "policennummer",
             "kundennummer", "mitgliedsnummer", "vorgangsnummer"],
        ),
        _pr(
            "KONTONUMMER",
            [(r"\b\d{3}[\s.]\d{3}[\s.]\d{3,4}\b", 0.15), (r"\b\d{7,10}\b", 0.1)],
            ["kontonummer", "konto-nr", "konto", "kto", "depot", "depotnummer", "depot-nr", "kundenkonto",
             "bankverbindung", "blz", "sparbuch"],
        ),
        # ---------- Firmen mit Rechtsform ----------
        _pr(
            "ORGANIZATION",
            [(r"\b[A-ZÄÖÜ][\wäöüß&.\-]*(?:[ \t]+[A-ZÄÖÜ&][\wäöüß&.\-]*){0,3}[ \t]+(?:" + RECHTSFORMEN + r")(?![\wäöüß])", 0.6)],
        ),
        # ---------- Datum ----------
        # Niedrig – nur mit Personenkontext (Geburt, Tod, Unfall) relevant; sonst bleiben Daten stehen
        _pr("DATUM", [(r"\b\d{1,2}\.\s?\d{1,2}\.\s?(?:19|20)\d{2}\b", 0.3),
                      (r"\b\d{1,2}\.\s?" + MONATE + r"\s(?:19|20)\d{2}\b", 0.3)], DATUM_KONTEXT),
        # Diktat-/Bearbeiterzeichen der Kanzlei: "Zeichen: AN/DS", "bl-bö", "Mü/Ka"
        _pr(
            "DIKTATZEICHEN",
            [(r"(?<![\w/])[A-Za-zÄÖÜäöü]{1,3}/[A-Za-zÄÖÜäöü]{1,3}(?![\w/])", 0.15),
             (r"(?<![\w-])[a-zäöü]{2,3}-[a-zäöü]{2,3}(?![\w-])", 0.1)],
            ["zeichen", "diktatzeichen", "bearbeiterzeichen", "unser zeichen", "ihr zeichen", "sachbearbeiter"],
        ),
        # ---------- Eingebaute deutsche Erkenner (Presidio) ----------
        DeTaxIdRecognizer(),
        DeTaxNumberRecognizer(),
        DeVatIdRecognizer(),
        DeSocialSecurityRecognizer(),
        DeIdCardRecognizer(),
        DePassportRecognizer(),
        DeFuehrerscheinRecognizer(),
        DeHealthInsuranceRecognizer(),
        DeLanrRecognizer(),
        DeBsnrRecognizer(),
        DeHandelsregisterRecognizer(),
        DeKfzRecognizer(),
        # Steuer-ID mit Leerzeichen ("12 345 678 901") – Presidio kennt nur die kompakte Form
        _pr(
            "DE_TAX_ID",
            [(r"\b[1-9]\d\s\d{3}\s\d{3}\s\d{3}\b", 0.3)],
            ["steuer", "steuer-id", "steueridentifikationsnummer", "idnr", "identifikationsnummer", "tin"],
        ),
        # ---------- Vordefinierte internationale Erkenner, auf Deutsch registriert ----------
        EmailRecognizer(supported_language=LANG),
        IbanRecognizer(supported_language=LANG, context=["iban", "konto", "bankverbindung"]),
        IpRecognizer(supported_language=LANG),
        UrlRecognizer(supported_language=LANG),
        CreditCardRecognizer(supported_language=LANG, context=["kreditkarte", "karte", "visa", "mastercard"]),
    ]
