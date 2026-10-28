"""Kern: Erkennung -> Bereinigung -> konsistente Pseudonymisierung -> Rückübersetzung."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Offline erzwingen: tldextract (für E-Mail-Validierung in Presidio) lädt sonst beim
# ersten Aufruf die Public-Suffix-Liste aus dem Internet. Wir nutzen den mitgelieferten Snapshot.
import tldextract

tldextract.extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import SpacyRecognizer

from .recognizers_de import DATUM_ALLE_RX, DATUM_KONTEXT, german_recognizers

DATUM_KONTEXT_KURZ = ["geb", "geburt", "verstorb", "versterb", "gestorb", "sterb", "tod"]

# Entity -> Platzhalter-Label
LABELS = {
    "PERSON": "PERSON",
    "ORGANIZATION": "FIRMA",
    "LOCATION": "ORT",
    "EMAIL_ADDRESS": "EMAIL",
    "TELEFON": "TELEFON",
    "ADRESSE": "ADRESSE",
    "PLZ_ORT": "ORT",
    "AKTENZEICHEN": "AZ",
    "DIKTATZEICHEN": "ZEICHEN",
    "GRUNDBUCH": "GRUNDBUCH",
    "IBAN_CODE": "IBAN",
    "KONTONUMMER": "KONTO",
    "CREDIT_CARD": "KARTE",
    "VERSICHERUNGSNR": "VERS_NR",
    "DE_TAX_ID": "STEUER_ID",
    "DE_TAX_NUMBER": "STEUERNR",
    "DE_VAT_ID": "UST_ID",
    "DE_SOCIAL_SECURITY": "SV_NR",
    "DE_HEALTH_INSURANCE": "KVNR",
    "DE_ID_CARD": "AUSWEIS",
    "DE_PASSPORT": "PASS",
    "DE_FUEHRERSCHEIN": "FUEHRERSCHEIN",
    "FUEHRERSCHEIN": "FUEHRERSCHEIN",
    "DE_LANR": "LANR",
    "DE_BSNR": "BSNR",
    "DE_HANDELSREGISTER": "HRB",
    "DE_KFZ": "KFZ",
    "KFZ": "KFZ",
    "FIN": "FIN",
    "DATUM": "DATUM",
    "IP_ADDRESS": "IP",
    "URL": "URL",
    "BERUF": "BERUF",
    "DIAGNOSE": "DIAGNOSE",
    "EIGENE_BEGRIFFE": "INTERN",
    "MANUELL": "MANUELL",
}

# Gruppen für die Oberfläche (Reihenfolge = Anzeige)
GRUPPEN = {
    "Personen und Firmen": ["PERSON", "ORGANIZATION"],
    "Kontakt und Anschrift": ["EMAIL_ADDRESS", "TELEFON", "ADRESSE", "PLZ_ORT", "LOCATION", "URL", "IP_ADDRESS"],
    "Akten und Verträge": ["AKTENZEICHEN", "DIKTATZEICHEN", "GRUNDBUCH", "VERSICHERUNGSNR", "DE_HANDELSREGISTER"],
    "Konto und Steuer": ["IBAN_CODE", "KONTONUMMER", "CREDIT_CARD", "DE_TAX_ID", "DE_TAX_NUMBER", "DE_VAT_ID"],
    "Ausweise und Nummern": ["DE_ID_CARD", "DE_PASSPORT", "DE_FUEHRERSCHEIN", "FUEHRERSCHEIN", "DE_SOCIAL_SECURITY",
                             "DE_HEALTH_INSURANCE", "DE_LANR", "DE_BSNR"],
    "Fahrzeug": ["DE_KFZ", "KFZ", "FIN"],
    "Datum": ["DATUM"],
    "Beruf und Gesundheit (indirekte Hinweise)": ["BERUF", "DIAGNOSE"],
    "Eigene Listen": ["EIGENE_BEGRIFFE", "MANUELL"],
}

# Häufige Fehlerkennungen des NER-Modells (Feldbezeichner, Dokumentarten, Anreden)
NER_STOPWORDS = {
    "iban", "bic", "steuer-id", "steuernummer", "ust-idnr", "ust-id", "tel", "telefon", "fax",
    "e-mail", "email", "mail", "mobil", "handy", "anschrift", "adresse", "kennzeichen", "betreff",
    "datum", "anlage", "anlagen", "sehr geehrte", "sehr geehrter", "herr", "herrn", "frau", "dr", "prof", "mfg",
    "gmbh", "ag", "kg", "abteilung", "team", "ki", "pdf", "excel", "word", "fin", "vin", "kanzlei", "praxis",
    "firma", "unternehmen", "gesellschaft", "verein", "behörde", "gericht", "versicherung", "bank",
    "person", "personen", "name", "namen", "platzhalter", "sachverhalt", "beteiligte", "beteiligter",
    # Dokumentarten und Schriftstücke
    "mandatsnotiz", "aktennotiz", "notiz", "vermerk", "protokoll", "messprotokoll", "messfoto", "rohmessdaten",
    "eichschein", "gutachten", "kostenvoranschlag", "abfindungsvorschlag", "rechnung", "schreiben", "bescheid",
    "bußgeldbescheid", "urteil", "beschluss", "antrag", "vollmacht", "testament", "vertrag", "akte", "akteneinsicht",
    "einspruch", "klage", "klageschrift", "mahnung", "angebot", "bestellung", "lieferschein", "nachlassverzeichnis",
    "pflichtteilsverlangen", "unfallaufnahme", "unfallbericht", "arztbrief", "befund", "entlassbrief", "attest",
    # Rollen
    "mandant", "mandantin", "mandanten", "erblasser", "erblasserin", "betroffene", "betroffener", "zeuge", "zeugin",
    "beklagte", "beklagter", "kläger", "klägerin", "antragsteller", "antragstellerin", "halter", "fahrer", "fahrerin",
    "vorsitzender", "vorsitzende", "patient", "patientin", "versicherungsnehmer", "gegenseite", "gegner",
    "sachverständiger", "sachverständige", "gutachter", "bestatter", "hausarzt", "hausärztin", "arbeitgeber",
    # Familie
    "mutter", "vater", "tochter", "sohn", "schwester", "bruder", "ehefrau", "ehemann", "frau", "mann", "tante", "onkel",
    "cousine", "cousin", "oma", "opa", "großmutter", "großvater", "enkel", "enkelin", "nichte", "neffe", "witwe",
    "witwer", "kind", "kinder", "eltern", "partner", "partnerin", "lebensgefährte", "lebensgefährtin",
    # Rollen in Gericht, Kanzlei, Geschäft (aus echten Schriftsätzen)
    "vertreter", "vertreterin", "prozessbevollmächtigter", "prozessbevollmächtigte", "richter", "richterin",
    "einzelrichter", "einzelrichterin", "justizbeschäftigte", "justizbeschäftigter", "urkundsbeamter", "urkundsbeamtin",
    "protokollführer", "protokollführerin", "geschäftsstelle", "kunde", "kundin", "kunden", "kollege", "kollegin",
    "dolmetscher", "dolmetscherin", "sachbearbeiter", "sachbearbeiterin", "mitarbeiter", "mitarbeiterin",
    "geschäftsführer", "geschäftsführerin", "inhaber", "inhaberin", "vorstand", "hersteller", "verkäufer", "verkäuferin",
    "käufer", "käuferin", "lieferant", "auftraggeber", "auftragnehmer", "versicherte", "versicherter",
    "versicherungsnehmerin", "gläubiger", "schuldner", "mieter", "vermieter", "eigentümer", "zeugen", "anwalt", "anwältin",
    "rechtsanwalt", "rechtsanwältin", "notar", "notarin", "steuerberater", "steuerberaterin", "gegenseite",
    "netto", "brutto", "summe", "gesamt", "betrag", "rechnungsbetrag", "endbetrag", "zwischensumme",
}
# Artikel, Pronomen, Präpositionen – nie ein Name oder Namensteil
FUNKTIONSWOERTER = {"der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "eines", "und", "oder", "von",
                    "van", "zu", "zur", "zum", "für", "mit", "bei", "aus", "nach", "vor", "an", "am", "im", "in",
                    "ich", "sie", "er", "es", "wir", "ihr", "ihre", "ihres", "ihrem", "ihren", "ihrer", "sein", "seine",
                    "seiner", "seinem", "seinen", "unser", "unsere", "unserer", "unserem", "unseren", "euer", "eure",
                    "mein", "meine", "meiner", "meinem", "meinen", "dein", "deine", "dieser", "diese", "dieses", "jener"}
# Wortarten laut spaCy, die kein Personenname sein können (einzelnes Wort vom Modell)
_POS_KEIN_NAME = {"PRON", "DET", "ADP", "VERB", "AUX", "ADV", "NUM", "PUNCT", "SCONJ", "CCONJ", "PART", "INTJ", "SYM"}
_ROEMISCH_RX = re.compile(r"[ivxlc]+\.?")
# Endungen zusammengesetzter Substantive, die das Modell (vor allem auf OCR-Text) für Namen hält
_SUBSTANTIV_ENDUNGEN = ("farbe", "nummer", "hummer", "ungs", "ung", "heit", "keit", "schaft", "datum", "betrag",
                        "preis", "kosten", "summe", "wert", "zahl", "steuer", "rechnung", "lieferung", "zahlung",
                        "menge", "stück", "artikel", "position", "bezeichnung", "beschreibung")
_ORG_KLEIN = {"und", "&", "für", "von", "der", "die", "des", "am", "im", "in", "an", "zu", "zur", "zum", "e.v.", "e.", "v.",
              "mbh", "co.", "co", "kg", "ohg", "gbr", "ag", "ug", "se", "gmbh", "gmbh.", "partner"}
# Typen, bei denen ein Modelltreffer ohne Ziffer kein echter Treffer sein kann
NUMERISCHE_TYPEN = {"KFZ", "DE_KFZ", "FUEHRERSCHEIN", "DE_FUEHRERSCHEIN", "VERSICHERUNGSNR", "KONTONUMMER", "AKTENZEICHEN",
                    "FIN", "IBAN_CODE", "TELEFON", "DE_TAX_ID", "DE_TAX_NUMBER", "DE_VAT_ID", "DE_SOCIAL_SECURITY",
                    "DE_HEALTH_INSURANCE", "DE_ID_CARD", "DE_PASSPORT", "DE_LANR", "DE_BSNR", "DE_HANDELSREGISTER",
                    "ADRESSE", "PLZ_ORT", "CREDIT_CARD"}
NER_ENTITIES = {"PERSON", "ORGANIZATION", "LOCATION"}

# Einrichtungen, die im Kanzlei-/Praxisalltag meist stehen bleiben sollen (Profil-Option keep_institutions).
# Lange Wörter als Wortbestandteil, kurze nur als ganzes Wort.
INSTITUTION_WORDS = {
    "gericht", "bußgeldstelle", "staatsanwaltschaft", "polizei", "finanzamt", "behörde", "ministerium", "kammer",
    "krankenhaus", "klinik", "klinikum", "hospital", "seniorenstift", "pflegeheim", "altenheim", "versicherung",
    "versicherer", "sparkasse", "volksbank", "raiffeisenbank", "commerzbank", "postbank", "bankhaus", "krankenkasse",
    "universität", "hochschule",
    "schule", "kirche", "gemeinde", "landkreis", "jobcenter", "agentur für arbeit", "rentenversicherung",
    "bundesamt", "landesamt", "ordnungsamt", "jugendamt", "standesamt", "nachlassgericht", "notariat",
    "caritas", "diakonie", "johanniter", "malteser", "huk-coburg", "allianz", "arag", "devk", "ergo", "signal iduna",
    "generali", "axa", "zurich", "württembergische", "debeka", "barmer", "techniker", "aok", "dak", "kkh", "ikk",
}
INSTITUTION_TOKENS = {"pi", "ag", "lg", "olg", "bgh", "bverfg", "stadt", "kreis", "amt", "bank", "stift", "heim",
                      "tk", "aok", "dak", "drk", "awo", "huk", "lvm", "r+v", "amtsgericht", "landgericht"}

TITLES = ("dr.", "prof.", "dr", "prof", "dipl.-ing.", "med.", "jur.", "rer.", "nat.", "h.c.")
SALUTATIONS = ("herr", "herrn", "frau", "hr.", "fr.")
ROLES = ("rechtsanwalt", "rechtsanwältin", "ra", "rain", "notar", "notarin", "hausarzt", "hausärztin", "arzt", "ärztin",
         "richter", "richterin", "steuerberater", "steuerberaterin")

PLACEHOLDER_RX = re.compile(r"\[([A-Z_]+_\d+)\]")

# Personen mit Titel/Anrede: "Dr. Michael Essen", "Herrn Jan Haverkamp", "Frau Dr. Lehmkuhl"
_NAME = r"[A-ZÄÖÜ][a-zäöüß\-]+(?:[ \t]+(?:von|van|de|zu|der)[ \t]+)?(?:[ \t]+[A-ZÄÖÜ][a-zäöüß\-]+){0,2}"
TITLE_NAME_RX = re.compile(
    r"(?:(?:Herrn?|Frau|Hr\.|Fr\.)[ \t]+)?"
    r"(?:(?:Rechtsanwalt|Rechtsanwältin|RAin?|Notar(?:in)?|Hausarzt|Hausärztin|Richter(?:in)?|Zeug(?:e|in)|"
    r"Kolleg(?:e|in)|Mandant(?:in)?)[ \t]+)?"
    r"((?:(?:Dr\.|Prof\.|Dipl\.-Ing\.|med\.|jur\.|rer\.\s?nat\.)[ \t]+)+" + _NAME + r")"
    r"|(?:Herrn?|Frau|Hr\.|Fr\.|Rechtsanwalt|Rechtsanwältin|RAin?|Notar(?:in)?|Kolleg(?:e|in)|Zeug(?:e|in)|"
    r"Richter(?:in)?|Sachverständige[rn]?)[ \t]+(" + _NAME + r")"
)
# Unterschriftszeile nach Grußformel: "Viele Grüße\nWolle"
SIGNATURE_RX = re.compile(
    r"(?:^|\n)[ \t]*(?:Viele|Liebe|Beste|Herzliche|Freundliche|Schöne|Mit freundlichen|Mit besten|Mit herzlichen|"
    r"Mit kollegialen)?[ \t]*(?:Grüße|Grüßen|Gruß|Grüsse|Gruss|LG|VG|MfG|Hochachtungsvoll)[ \t]*,?[ \t]*\n+[ \t]*"
    r"(?:(?:Rechtsanwalt|Rechtsanwältin|RAin?|Notar(?:in)?|Dein|Deine|Euer|Eure|Ihr|Ihre)[ \t]+)?"
    r"((?:(?:Dr\.|Prof\.)[ \t]+)*[A-ZÄÖÜ][a-zäöüß]+(?:[ \t]+[A-ZÄÖÜ][a-zäöüß\-]+){0,3})"
)
# Wörter, die in einem Namen nichts zu suchen haben (Feldbezeichner im NER-Treffer: "Schadennummer SN")
_LABEL_SUFFIXES = ("nummer", "-nr", "-nr.", "-id", "zeichen", "kennzeichen")
FIELD_LABEL_WORDS = {
    "iban", "bic", "tel", "telefon", "fax", "e-mail", "email", "mail", "mobil", "handy", "anschrift", "adresse",
    "betreff", "datum", "anlage", "anlagen", "fin", "vin", "az", "kto", "konto", "depot", "plz", "ort", "straße",
    "name", "vorname", "nachname", "geburtsdatum", "geb", "wohnort", "arbeitgeber", "versicherung", "police",
}
# Briefkopf-Datum "Essen, 21.10.2026" – Ort plus Komma unmittelbar davor
_DATELINE_RX = re.compile(r"[A-ZÄÖÜ][a-zäöüß\.\- ]{1,40},[ \t]*(?:den[ \t]+)?$")
_KFZ_RX = re.compile(r"[A-ZÄÖÜ]{1,3}[\s\-][A-Z]{1,2}[\s\-]?\d{1,4}[EH]?")
_FILENAME_RX = re.compile(r"[\w\-]+\.(?:py|md|txt|docx?|xlsx?|pptx?|pdf|csv|json|ya?ml|bat|exe|zip|png|jpe?g)", re.IGNORECASE)


@dataclass
class Finding:
    start: int
    end: int
    entity: str
    score: float
    text: str
    active: bool = True
    quelle: str = ""  # "modell", "regel", "liste", "wiederholung", "namensteil", "heuristik"


@dataclass
class Result:
    original: str
    findings: list[Finding]
    anonymized: str = ""
    mapping: dict[str, str] = field(default_factory=dict)  # Platzhalter -> Original


# Labels des GLiNER-PII-Modells (englisch, so wurde es trainiert) -> unsere Entitäten
GLINER_MAPPING = {
    "person": "PERSON",
    "organization": "ORGANIZATION",
    "company": "ORGANIZATION",
    "address": "ADRESSE",
    "phone number": "TELEFON",
    "email": "EMAIL_ADDRESS",
    "driver's license number": "FUEHRERSCHEIN",
    "license plate": "KFZ",
    "vehicle registration number": "KFZ",
    "vehicle identification number": "FIN",
    "insurance number": "VERSICHERUNGSNR",
    "health insurance number": "DE_HEALTH_INSURANCE",
    "bank account number": "KONTONUMMER",
    "iban": "IBAN_CODE",
    "tax identification number": "DE_TAX_ID",
    "passport number": "DE_PASSPORT",
    "identity card number": "DE_ID_CARD",
    "social security number": "DE_SOCIAL_SECURITY",
    "case number": "AKTENZEICHEN",
    "registration number": "AKTENZEICHEN",
    "land registry number": "GRUNDBUCH",
    "job title": "BERUF",
    "medical facility": "ORGANIZATION",
    "medical condition": "DIAGNOSE",
}


def build_analyzer(spacy_model: str = "de_core_news_lg", gliner_model: str | None = None,
                   gliner_threshold: float = 0.5, gliner_onnx_file: str = "") -> AnalyzerEngine:
    nlp_conf = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "de", "model_name": spacy_model}],
        "ner_model_configuration": {
            "model_to_presidio_entity_mapping": {
                "PER": "PERSON",
                "LOC": "LOCATION",
                "ORG": "ORGANIZATION",
            },
            "labels_to_ignore": ["MISC"],
        },
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_conf).create_engine()
    registry = RecognizerRegistry(supported_languages=["de"])
    registry.add_recognizer(
        SpacyRecognizer(supported_language="de", supported_entities=["PERSON", "LOCATION", "ORGANIZATION"])
    )
    for r in german_recognizers():
        registry.add_recognizer(r)
    if gliner_model:
        from presidio_analyzer.predefined_recognizers import GLiNERRecognizer

        # gliner_onnx_file leer = PyTorch-Gewichte (CPU). Der 4-Bit-ONNX-Export von hansa-institute liefert
        # keine Treffer (geprüft 28.10.2026), deshalb Standard PyTorch.
        registry.add_recognizer(GLiNERRecognizer(
            supported_language="de", model_name=gliner_model, entity_mapping=GLINER_MAPPING,
            threshold=gliner_threshold, load_onnx_model=bool(gliner_onnx_file),
            onnx_model_file=gliner_onnx_file or "model.onnx", map_location="cpu",
            chunk_size=1000, chunk_overlap=100,
        ))
    # Kontextwörter auch NACH dem Treffer berücksichtigen ("… ist am 02.09.2026 verstorben")
    enhancer = LemmaContextAwareEnhancer(context_prefix_count=5, context_suffix_count=6)
    return AnalyzerEngine(nlp_engine=nlp_engine, registry=registry, supported_languages=["de"],
                          context_aware_enhancer=enhancer)


# ---------------------------------------------------------------------------
# Hilfsfunktionen für die Bereinigung
# ---------------------------------------------------------------------------

def _norm_tokens(s: str) -> list[str]:
    """Kleinschreibung, Titel/Anreden/Initialen entfernt, Satzzeichen weg."""
    toks = []
    for t in re.split(r"[\s,;/()]+", s.lower()):
        t = t.strip(".:'\"„“»«")
        if not t or t in TITLES or t in SALUTATIONS or t in ROLES or t.rstrip(".") in TITLES:
            continue
        if len(t) <= 2 and t.isalpha() and t not in ("ag", "kg"):  # Initialen wie "A."
            continue
        toks.append(t)
    return toks


def make_allow_matcher(allow_list: list[str] | None):
    """Liefert eine Funktion text -> bool. Ein Begriff ist erlaubt, wenn er einem Allow-Eintrag
    entspricht, darin enthalten ist (Namensteil) oder ihn enthält (längere Schreibweise)."""
    entries = []
    for a in allow_list or []:
        a = a.strip()
        if a:
            entries.append((a.lower(), set(_norm_tokens(a))))

    def allowed(text: str) -> bool:
        t = text.lower().strip()
        toks = set(_norm_tokens(text))
        for raw, atoks in entries:
            if t == raw or (len(raw) >= 4 and raw in t):
                return True
            if toks and atoks and toks <= atoks:
                return True
        return False

    allowed.terms = [raw for raw, _ in entries]
    return allowed


def _is_institution(text: str) -> bool:
    t = text.lower()
    toks = set(re.split(r"[\s\-]+", t))
    return any(w in t for w in INSTITUTION_WORDS) or bool(toks & INSTITUTION_TOKENS)


def _term_findings(text: str, terms: list[str], entity: str, quelle: str = "liste") -> list[Finding]:
    """Alle Vorkommen der Begriffe als ganze Wörter. Bei Personen auch Genitiv ("Schultes Auto")."""
    out = []
    suffix = r"(?:s|es)?" if entity == "PERSON" else ""
    for t in {t.strip() for t in terms if t and t.strip()}:
        for m in re.finditer(rf"(?<!\w){re.escape(t)}{suffix}(?!\w)", text, flags=re.IGNORECASE):
            out.append(Finding(m.start(), m.end(), entity, 1.0, m.group(), quelle=quelle))
    return out


def _heuristic_persons(text: str) -> list[Finding]:
    """Personen, die das Modell oft übersieht: mit Titel/Anrede und in der Unterschriftszeile."""
    out = []
    for m in TITLE_NAME_RX.finditer(text):
        g = 1 if m.group(1) else 2
        name = m.group(g)
        if name and not all(w.lower().strip(".") in NER_STOPWORDS for w in name.split()):
            out.append(Finding(m.start(g), m.end(g), "PERSON", 0.5, name, quelle="heuristik"))
    for m in SIGNATURE_RX.finditer(text):
        name = m.group(1).strip()
        if name.lower() not in NER_STOPWORDS:
            out.append(Finding(m.start(1), m.start(1) + len(name), "PERSON", 0.45, name, quelle="heuristik"))
    return out


def _resolve_overlaps(findings: list[Finding]) -> list[Finding]:
    """Ein Treffer, der vollständig in einem anderen (Score >= 0.5) liegt, tritt hinter diesen zurück.
    Sonst gewinnt der höchste Score, bei Gleichstand der längere Treffer. Zurückgetretene Treffer rücken nach,
    wenn ihr Container selbst verdrängt wurde (sonst ginge z. B. "28195 Bremen" verloren, wenn der lange
    Adress-Treffer einem anderen weichen muss)."""
    def enthalten(f: Finding) -> bool:
        return any(o is not f and o.score >= 0.5 and o.start <= f.start and o.end >= f.end
                   and (o.end - o.start) > (f.end - f.start) for o in findings)

    frei = [f for f in findings if not enthalten(f)]
    zurueck = [f for f in findings if enthalten(f)]
    kept: list[Finding] = []
    for f in sorted(frei, key=lambda f: (-f.score, -(f.end - f.start))):
        if all(f.end <= k.start or f.start >= k.end for k in kept):
            kept.append(f)
    for f in sorted(zurueck, key=lambda f: (-f.score, -(f.end - f.start))):
        if all(f.end <= k.start or f.start >= k.end for k in kept):
            kept.append(f)
    return sorted(kept, key=lambda f: f.start)


def _clean_span(text: str, f: Finding) -> Finding | None:
    """Satzzeichen/Leerzeichen an den Rändern abschneiden; Anreden vor Personen entfernen."""
    s, e = f.start, f.end
    if f.entity == "ORGANIZATION" and "./." in text[s:e]:
        e = s + text[s:e].index("./.")  # "P+P Rental OHG ./. Günther" – Parteien nicht zusammen maskieren
    while s < e and text[s] in " \t\n,.;:()\"'„“»«*":
        s += 1
    while e > s and text[e - 1] in " \t\n,;:()\"'„“»«*/.":
        e -= 1
    if f.entity == "PERSON":
        # Anrede und Rollenwort vor dem Namen gehören nicht zum Namen ("Herrn Kollege Neuhaus" -> "Neuhaus")
        m = re.match(r"(?:(?:Herrn?|Frau|Hr\.|Fr\.|Kolleg(?:e|in)|Rechtsanwalt|Rechtsanwältin|RAin?|Zeug(?:e|in)|"
                     r"Mandant(?:in)?)[ \t]+)+", text[s:e])
        if m and e - (s + m.end()) >= 2:
            s += m.end()
            # Anrede/Rolle davor = starkes Indiz für einen Namen; die Wortart-Prüfung greift hier nicht mehr
            quelle = "heuristik" if f.quelle == "modell" else f.quelle
            if e - s < 2:
                return None
            return Finding(s, e, f.entity, f.score, text[s:e], f.active, quelle)
    if e - s < 2:
        return None
    return Finding(s, e, f.entity, f.score, text[s:e], f.active, f.quelle)


class _Wortarten:
    """Wortart-Nachschlag (spaCy) je Zeichenposition – für die Plausibilitätsprüfung von Modelltreffern."""

    def __init__(self, doc):
        self.tokens = list(doc) if doc is not None else []
        self.starts = [t.idx for t in self.tokens]

    def tokens_in(self, start: int, end: int):
        import bisect

        i = bisect.bisect_right(self.starts, start) - 1
        out = []
        while 0 <= i < len(self.tokens):
            t = self.tokens[i]
            if t.idx >= end:
                break
            if t.idx + len(t.text) > start:
                out.append(t)
            i += 1
        return out


def _plausible(text: str, f: Finding, wa: _Wortarten | None = None) -> bool:
    if f.entity not in NER_ENTITIES:
        if f.entity == "EMAIL_ADDRESS" and "@" not in f.text:
            return False  # "E-Mail-Anschrift"
        if f.quelle == "modell":
            if f.entity == "DATUM":
                # Modell-Daten nur mit Personenbezug im Umfeld (wie bei der Regel)
                umfeld = text[max(0, f.start - 60):f.end + 60].lower()
                return any(k in umfeld for k in DATUM_KONTEXT_KURZ)
            if f.entity in ("KFZ", "DE_KFZ") and not _KFZ_RX.fullmatch(f.text.strip()):
                return False  # "BMW 320d" ist kein Kennzeichen
            if f.entity in ("FUEHRERSCHEIN", "DE_FUEHRERSCHEIN") and not re.fullmatch(r"[A-Z0-9]{8,14}", f.text.strip()):
                return False  # "Frühjahr 2024" ist keine Führerscheinnummer
            if f.entity in NUMERISCHE_TYPEN:
                digits = sum(ch.isdigit() for ch in f.text)
                if digits == 0 or (f.entity == "KONTONUMMER" and digits < 7):
                    return False
        return True
    t = f.text.strip().lower()
    if t in NER_STOPWORDS or t.rstrip(".:") in NER_STOPWORDS or len(t) < 3:
        return False
    if "@" in t or "://" in t or t.startswith("www.") or _ROEMISCH_RX.fullmatch(t):
        return False  # E-Mail, URL, römische Gliederung sind nie Person/Firma
    toks_all = [w.strip(".,:").lower() for w in f.text.split()]
    if f.entity == "PERSON" and all(w in NER_STOPWORDS or w in FUNKTIONSWOERTER or w in TITLES for w in toks_all):
        return False  # "Der Erblasser", "Mutter", "Herr Dr.", "Ihr Mandant"
    # Rollen mit Bindestrich: "Beklagten-Vertreter", "Kläger-Vertreter"
    teile = [p.strip(".,:") for p in re.split(r"[\s\-]+", t) if p.strip(".,:")]
    if teile and all(p in NER_STOPWORDS or p in FUNKTIONSWOERTER or p.rstrip("n") in NER_STOPWORDS for p in teile):
        return False
    if any(ch.isdigit() for ch in t) or "\n" in f.text:
        return False
    if f.entity == "PERSON" and any(w.lower().endswith(_SUBSTANTIV_ENDUNGEN) for w in toks_all):
        return False  # "Planenfarbe", "Rechnungs", "Auftragsnummer" – zusammengesetzte Substantive
    if wa is not None and f.quelle == "modell":
        toks = wa.tokens_in(f.start, f.end)
        if f.entity == "PERSON" and toks:
            if len(toks_all) == 1:
                tok = toks[0]
                if tok.pos_ in _POS_KEIN_NAME:
                    return False  # "Ihres", "Uberweisen", "Sollte"
                if tok.pos_ == "NOUN" and tok.ent_type_ not in ("PER",):
                    return False  # "Anhänger", "Kunden"
            else:
                # Mehrteilige Namen bestehen aus Eigennamen (und Titeln/Adelspartikeln)
                for tk in toks:
                    w = tk.text.strip(".,").lower()
                    if w in TITLES or w in ("von", "van", "de", "zu", "der", "und"):
                        continue
                    if tk.pos_ in _POS_KEIN_NAME or (tk.pos_ in ("NOUN", "ADJ") and tk.ent_type_ != "PER"):
                        return False  # "Rechnungs Datüm", "Ihra Auftragsnummer", "Manuela und Hartmut"
        if f.entity == "ORGANIZATION" and toks:
            if any(tk.pos_ in ("VERB", "AUX", "PRON", "SCONJ") for tk in toks):
                return False  # "Endbetragen kann'es"
            if not any(w[:1].isupper() and len(w.strip(".,")) >= 3 for w in f.text.split()):
                return False
            if any("'" in tk.text or (tk.text[:1].islower() and tk.text.lower() not in _ORG_KLEIN) for tk in toks):
                return False  # Kleingeschriebene Wörter im Firmennamen: nur "und", "&", "für" u. ä.
            if len(toks) == 1 and toks[0].pos_ == "NOUN" and toks[0].ent_type_ not in ("ORG",):
                return False  # "Geschäftsstelle"
    # Feldbezeichner im Treffer ("Schadennummer SN", "Vorgangsnummer VU") oder als Treffer ("FIN:")
    toks = [w.strip(".,:") for w in t.split()]
    if any(w.endswith(_LABEL_SUFFIXES) or w in FIELD_LABEL_WORDS for w in toks):
        return False
    if " " not in t and text[f.end:f.end + 2].lstrip(".").startswith(":"):
        return False
    return True


def _mentions(text: str, allowed, keep_institutions: bool) -> list[tuple[int, int]]:
    """Stellen im Text, an denen eine erlaubte Stelle (eigene Kanzlei) oder eine Einrichtung genannt wird.
    Kontaktdaten in derselben Zeile danach gehören zu ihr und bleiben stehen."""
    spans = []
    if keep_institutions:
        words = sorted(INSTITUTION_WORDS | INSTITUTION_TOKENS, key=len, reverse=True)
        rx = re.compile(r"(?<![\wäöüß])(?:" + "|".join(re.escape(w) for w in words) + r")(?:[\wäöüß\-]*)",
                        re.IGNORECASE)
        spans += [(m.start(), m.end()) for m in rx.finditer(text) if len(m.group()) > 2]
    for term in getattr(allowed, "terms", []):
        if len(term) >= 4:
            spans += [(m.start(), m.end()) for m in re.finditer(re.escape(term), text, flags=re.IGNORECASE)]
    return spans


def _belongs_to_mention(text: str, f: Finding, mentions: list[tuple[int, int]], abstand: int = 80,
                        personen: list[tuple[int, int]] | None = None) -> bool:
    """Kontaktdatum (Adresse, PLZ+Ort, Telefon, E-Mail) kurz nach einer Einrichtung/erlaubten Stelle in derselben
    Zeile (höchstens `abstand` Zeichen dazwischen – sonst frisst eine lange OCR-Zeile alles).
    Steht zwischen der Einrichtung und dem Kontaktdatum ein Personenname ("… ./. Allianz AG … unser Mandant
    Moritz Günther, Violenstraße 13"), gehört das Kontaktdatum zur Person und wird maskiert."""
    if f.entity not in ("ADRESSE", "PLZ_ORT", "TELEFON", "EMAIL_ADDRESS", "URL"):
        return False
    line_start = text.rfind("\n", 0, f.start) + 1
    for ms, me in mentions:
        if line_start <= ms and me <= f.start and f.start - me <= abstand:
            if not any(me <= ps and pe <= f.start for ps, pe in (personen or [])):
                return True
    return False


# ---------------------------------------------------------------------------
# Erkennung
# ---------------------------------------------------------------------------

def detect(
    analyzer: AnalyzerEngine,
    text: str,
    entities: list[str],
    threshold: float = 0.4,
    allow_list: list[str] | None = None,
    deny_list: list[str] | None = None,
    manual_terms: list[str] | None = None,
    propagate_repeats: bool = True,
    include_name_parts: bool = True,
    mask_locations: bool = False,
    keep_institutions: bool = True,
    datum_modus: str = "kontext",
) -> list[Finding]:
    """Findet sensible Stellen.

    mask_locations: Ortsnamen ohne Adresse (z. B. "Mülheim" im Fließtext) maskieren.
    keep_institutions: Gerichte, Behörden, Versicherer, Kliniken stehen lassen.
    datum_modus: "kontext" = nur Daten mit Personenbezug (Geburt, Tod); "alle" = jedes Datum; "keine".
    """
    allowed = make_allow_matcher(allow_list)
    model_entities = [e for e in entities if e not in ("EIGENE_BEGRIFFE", "MANUELL")]
    if "PERSON" in model_entities and "LOCATION" not in model_entities:
        model_entities.append("LOCATION")  # brauchen wir für die Ort/Firma-Unterscheidung

    raw = analyzer.analyze(text=text, language="de", entities=model_entities, score_threshold=threshold)
    findings = []
    for r in raw:
        name = (r.recognition_metadata or {}).get("recognizer_name", "")
        quelle = "modell" if name in ("SpacyRecognizer", "GLiNERRecognizer") else "regel"
        findings.append(Finding(r.start, r.end, r.entity_type, r.score, text[r.start:r.end], quelle=quelle))
    findings += _heuristic_persons(text)
    findings = [c for f in findings if (c := _clean_span(text, f))]
    # Wortarten für die Plausibilitätsprüfung (spaCy-Modell aus dem Analyzer wiederverwenden)
    wa = None
    try:
        nlp = analyzer.nlp_engine.nlp["de"]
        wa = _Wortarten(nlp(text))
    except Exception:
        pass
    findings = [f for f in findings if _plausible(text, f, wa)]
    # Briefkopf-Datum ("Essen, 21.10.2026") ist kein Personenbezug
    findings = [f for f in findings if not (f.entity == "DATUM" and _DATELINE_RX.search(text[max(0, f.start - 50):f.start]))]
    if datum_modus == "keine":
        findings = [f for f in findings if f.entity != "DATUM"]
    elif datum_modus == "alle" and "DATUM" in entities:
        for m in re.finditer(DATUM_ALLE_RX, text):
            findings.append(Finding(m.start(), m.end(), "DATUM", 0.5, m.group(), quelle="regel"))

    # Ein Wort, das das Modell an anderer Stelle als Ort erkannt hat, ist auch hier ein Ort ("Essen")
    loc_texts = {f.text.lower() for f in findings if f.entity == "LOCATION"}
    for f in findings:
        if f.entity == "ORGANIZATION" and " " not in f.text and f.text.lower() in loc_texts:
            f.entity = "LOCATION"
    # Dateinamen sind keine URLs ("evaluate.py", "bericht.docx"; der URL-Erkenner schneidet oft "Brinkhoff.do" ab)
    def _ist_dateiname(f: Finding) -> bool:
        s, e = f.start, f.end
        while s > 0 and not text[s - 1].isspace():
            s -= 1
        while e < len(text) and not text[e].isspace():
            e += 1
        return bool(_FILENAME_RX.fullmatch(text[s:e].strip(",.;:()\"'")))
    findings = [f for f in findings if not (f.entity == "URL" and _ist_dateiname(f))]

    if not mask_locations or "LOCATION" not in entities:
        findings = [f for f in findings if f.entity != "LOCATION"]
    if keep_institutions:
        findings = [f for f in findings if not (f.entity in ("ORGANIZATION", "LOCATION") and _is_institution(f.text))]
    findings = [f for f in findings if not allowed(f.text)]
    # Adresse/Telefon des Gerichts oder der eigenen Kanzlei in derselben Zeile bleiben stehen
    mentions = _mentions(text, allowed, keep_institutions)
    personen = [(f.start, f.end) for f in findings if f.entity == "PERSON"]
    findings = [f for f in findings if not _belongs_to_mention(text, f, mentions, personen=personen)]

    findings += _term_findings(text, deny_list or [], "EIGENE_BEGRIFFE")
    findings += _term_findings(text, manual_terms or [], "MANUELL")
    findings = _resolve_overlaps(findings)

    if propagate_repeats:
        # Was einmal erkannt wurde, wird überall maskiert (das Modell übersieht oft Wiederholungen).
        # Ergänzungen haben niedrigen Score und füllen nur Lücken.
        terms = {(f.text, f.entity, "wiederholung") for f in findings}
        if include_name_parts:
            for f in [f for f in findings if f.entity == "PERSON"]:
                for part in f.text.split():
                    p = part.strip(".,")
                    # Namensteile, die im Dokument auch Ortsnamen sind ("Essen"), nicht einzeln propagieren
                    if (len(p) >= 3 and p[0].isupper() and p.lower() not in NER_STOPWORDS
                            and p.lower() not in FUNKTIONSWOERTER and p.lower() not in TITLES
                            and p.lower() not in loc_texts and not allowed(p)):
                        terms.add((p, "PERSON", "namensteil"))
        extra = []
        for term, ent, quelle in terms:
            if len(term) >= 3:
                extra += [Finding(x.start, x.end, ent, 0.01, x.text, quelle=quelle)
                          for x in _term_findings(text, [term], ent)]
        # Bewusst KEINE Ausnahme für Einrichtungen: Was einmal als sensibel gilt, wird überall maskiert
        # (sonst bliebe z. B. die PLZ des Mandanten an der Gerichtsadresse lesbar).
        findings = _resolve_overlaps(findings + extra)

    return findings


def namensteile(text: str, allowed=None) -> list[str]:
    """Einzelne Namensteile eines Personennamens, die separat maskiert werden dürfen."""
    out = []
    for part in text.split():
        p = part.strip(".,")
        if (len(p) >= 3 and p[0].isupper() and p.lower() not in NER_STOPWORDS and p.lower() not in FUNKTIONSWOERTER
                and p.lower() not in TITLES and not (allowed and allowed(p))):
            out.append(p)
    return out


def propagate_vorgang(texte: list[str], findings_list: list[list[Finding]], allow_list: list[str] | None = None,
                      include_name_parts: bool = True) -> list[list[Finding]]:
    """Vorgangsweite Wiederholungen: Was in EINER Datei als Treffer gilt (inkl. Namensteile), wird in ALLEN Dateien
    des Vorgangs gesucht. Ein Nachname, der in Datei A zu „Moritz Günther“ gehört, wird so auch in Datei B maskiert,
    wo das Modell ihn übersehen hat. Nur aktive Treffer werden übernommen; Ergänzungen bekommen Score 0.01."""
    allowed = make_allow_matcher(allow_list)
    terms: set[tuple[str, str]] = set()
    for fs in findings_list:
        for f in fs:
            if not f.active or len(f.text.strip()) < 3 or f.entity in ("MANUELL",):
                continue
            terms.add((f.text, f.entity))
            if include_name_parts and f.entity == "PERSON":
                for p in namensteile(f.text, allowed):
                    terms.add((p, "PERSON"))
    out = []
    for text, fs in zip(texte, findings_list):
        vorhanden = {(f.text.lower(), f.entity) for f in fs}
        extra = []
        for term, ent in terms:
            if (term.lower(), ent) in vorhanden and ent != "PERSON":
                continue  # schon per Dokument-Propagation abgedeckt
            quelle = "namensteil" if ent == "PERSON" and " " not in term else "vorgang"
            extra += [Finding(x.start, x.end, ent, 0.01, x.text, quelle=quelle) for x in _term_findings(text, [term], ent)]
        out.append(_resolve_overlaps(fs + extra) if extra else fs)
    return out


# ---------------------------------------------------------------------------
# Pseudonymisierung und Rückübersetzung
# ---------------------------------------------------------------------------

def anzeige_platzhalter(ph: str, bezeichnungen: dict[str, str] | None = None) -> str:
    """Platzhalter-Text, wie er in den Ausgaben steht: "[PERSON_1]" oder mit eigener Bezeichnung "[MANDANT]"."""
    if bezeichnungen and ph in bezeichnungen and bezeichnungen[ph].strip():
        return f"[{bezeichnung_normieren(bezeichnungen[ph])}]"
    return f"[{ph}]"


def bezeichnung_normieren(s: str) -> str:
    """Eigene Bezeichnung -> Platzhalter-Form: Großbuchstaben, Umlaute ersetzt, Leerzeichen zu Unterstrich.
    "Mandant" -> "MANDANT", "Zeuge Günther" -> "ZEUGE_GUENTHER"."""
    s = s.strip()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "AE"), ("Ö", "OE"), ("Ü", "UE"), ("ß", "ss")):
        s = s.replace(a, b)
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").upper()
    return s or "BEGRIFF"


def pseudonymize(text: str, findings: list[Finding], mapping: dict[str, str] | None = None,
                 bezeichnungen: dict[str, str] | None = None) -> Result:
    """Ersetzt aktive Treffer durch [LABEL_n] bzw. die eigene Bezeichnung. Gleiches Original -> gleicher Platzhalter.

    Namensteile ("Müller" aus "Hans Müller") bekommen denselben Platzhalter wie der volle Name.
    Ein vorhandenes mapping (aus demselben Vorgang) wird fortgeführt. bezeichnungen: {"PERSON_1": "Mandant"}.
    """
    mapping = dict(mapping or {})
    reverse = {v.lower(): k for k, v in mapping.items()}
    counters: dict[str, int] = {}
    for ph in mapping:
        lab, n = ph.rsplit("_", 1)
        counters[lab] = max(counters.get(lab, 0), int(n))

    active = [f for f in findings if f.active]
    # Volle Namen zuerst, damit Teile darauf zeigen können (auch Namen aus dem bestehenden mapping).
    # Teilen sich zwei Personen einen Nachnamen ("Moritz Günther", "Cornelia Günther"), gehört der nackte
    # Nachname zur häufiger genannten Person.
    from collections import Counter

    haeufigkeit: Counter = Counter(f.text for f in active if f.entity == "PERSON")
    for k, v in mapping.items():
        if k.startswith("PERSON_"):
            haeufigkeit[v] += 1
    persons = sorted(haeufigkeit, key=lambda p: (-len(p.split()), -haeufigkeit[p], -len(p)))
    part_owner = {}
    for full in persons:
        for part in full.split():
            part_owner.setdefault(part.lower().strip(".,"), full)

    def placeholder(f: Finding) -> str:
        key = f.text.lower()
        owner = part_owner.get(key)
        if f.entity == "PERSON" and (owner is None or owner.lower() == key) and key not in reverse:
            # Genitiv: "Brinkhoffs" -> "Brinkhoff", "Hans Müllers" -> "Hans Müller"
            for suffix in ("s", "es"):
                base = key[: -len(suffix)]
                if key.endswith(suffix) and base and (base in reverse or
                                                      (base in part_owner and part_owner[base].lower() != base)):
                    key = base
                    break
        if f.entity == "PERSON" and key in part_owner and part_owner[key].lower() != key:
            orig = part_owner[key]
            key = orig.lower()
        elif key in reverse:
            orig = mapping[reverse[key]]
        else:
            orig = f.text
        if key in reverse:
            return reverse[key]
        lab = LABELS.get(f.entity, f.entity)
        counters[lab] = counters.get(lab, 0) + 1
        ph = f"{lab}_{counters[lab]}"
        mapping[ph] = orig
        reverse[key] = ph
        return ph

    # Platzhalter in Textreihenfolge vergeben, dann von hinten ersetzen
    phs = [(f, placeholder(f)) for f in active]
    out = text
    for f, ph in sorted(phs, key=lambda x: x[0].start, reverse=True):
        out = out[: f.start] + anzeige_platzhalter(ph, bezeichnungen) + out[f.end :]
    return Result(original=text, findings=findings, anonymized=out, mapping=mapping)


def deanonymize(text: str, mapping: dict[str, str], bezeichnungen: dict[str, str] | None = None) -> str:
    """Setzt Platzhalter zurück. Tolerant gegenüber Varianten, die KI-Antworten erzeugen:
    [PERSON_1], PERSON_1, Person 1, [Person-1], «PERSON_1», [PERSON_1]s (Genitiv bleibt erhalten).
    Eigene Bezeichnungen ([MANDANT], Mandant in Klammern) werden ebenfalls erkannt."""
    if not mapping:
        return text
    # Eigene Bezeichnungen zuerst (längste zuerst), nur in Klammern oder als exaktes Großwort
    if bezeichnungen:
        eigene = sorted(((bezeichnung_normieren(b), ph) for ph, b in bezeichnungen.items() if b.strip() and ph in mapping),
                        key=lambda x: -len(x[0]))
        for norm, ph in eigene:
            rx_b = re.compile(r"(?P<open>[\[«<{(]\s*)?\b" + re.escape(norm).replace("_", r"[\s_\-]*") + r"\b"
                              r"(?(open)\s*[\]»>})]?|)", re.IGNORECASE)
            text = rx_b.sub(lambda m, ph=ph: mapping[ph], text)
    labels = sorted({k.rsplit("_", 1)[0] for k in mapping}, key=len, reverse=True)
    rx = re.compile(
        r"(?P<open>[\[«<{(]\s*)?\b(?P<lab>" + "|".join(re.escape(l) for l in labels) + r")[\s_\-]*(?P<num>\d+)(?!\d)"
        r"(?(open)\s*[\]»>})]?|)",
        re.IGNORECASE,
    )

    def repl(m: re.Match) -> str:
        key = f"{m.group('lab').upper()}_{m.group('num')}"
        return mapping.get(key, m.group(0))

    return rx.sub(repl, text)


def replacement_pairs(text: str, findings: list[Finding], mapping: dict[str, str],
                      bezeichnungen: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """Original-Strings -> Platzhalter (für das Ersetzen in DOCX/XLSX/PDF), längste zuerst."""
    reverse = {v.lower(): k for k, v in mapping.items()}
    pairs = {}
    for f in findings:
        if not f.active or len(f.text.strip()) < 3:
            continue
        key = f.text.lower()
        ph = reverse.get(key)
        if ph is None and f.entity == "PERSON":
            for suffix in ("s", "es"):  # Genitiv
                if key.endswith(suffix) and key[: -len(suffix)] in reverse:
                    ph = reverse[key[: -len(suffix)]]
                    break
        if ph is None:
            # Namensteil: über den Platzhalter des vollen Namens herausfinden
            for full_lower, p in reverse.items():
                if key in [w.strip(".,") for w in full_lower.split()]:
                    ph = p
                    break
        if ph:
            pairs[f.text] = anzeige_platzhalter(ph, bezeichnungen)
    return sorted(pairs.items(), key=lambda kv: len(kv[0]), reverse=True)
