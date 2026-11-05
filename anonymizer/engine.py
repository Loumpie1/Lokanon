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

from . import lexikon
from .felder import feld_treffer
from .struktur import struktur_treffer
from .recognizers_de import DATUM_ALLE_RX, DATUM_KONTEXT, RECHTSFORMEN, german_recognizers

DATUM_KONTEXT_KURZ = ["geb", "geburt", "verstorb", "versterb", "gestorb", "sterb", "tod"]

# Entity -> Platzhalter-Label
LABELS = {
    "PERSON": "Person",
    "ORGANIZATION": "Firma",
    "LOCATION": "Ort",
    "EMAIL_ADDRESS": "Email",
    "TELEFON": "Telefon",
    "ADRESSE": "Adresse",
    "PLZ_ORT": "Ort",
    "AKTENZEICHEN": "Aktenzeichen",
    "DIKTATZEICHEN": "Zeichen",
    "GRUNDBUCH": "Grundbuch",
    "IBAN_CODE": "IBAN",
    "KONTONUMMER": "Konto",
    "CREDIT_CARD": "Karte",
    "VERSICHERUNGSNR": "VersNr",
    "DE_TAX_ID": "SteuerID",
    "DE_TAX_NUMBER": "Steuernr",
    "DE_VAT_ID": "UStID",
    "DE_SOCIAL_SECURITY": "SVNr",
    "DE_HEALTH_INSURANCE": "KVNr",
    "DE_ID_CARD": "Ausweis",
    "DE_PASSPORT": "Pass",
    "DE_FUEHRERSCHEIN": "Fuehrerschein",
    "FUEHRERSCHEIN": "Fuehrerschein",
    "DE_LANR": "LANR",
    "DE_BSNR": "BSNR",
    "PERSONALNR": "PersNr",
    "KENNNUMMER": "Nummer",
    "DE_HANDELSREGISTER": "HRB",
    "DE_KFZ": "Kennzeichen",
    "KFZ": "Kennzeichen",
    "FIN": "FIN",
    "DATUM": "Datum",
    "IP_ADDRESS": "IP",
    "URL": "URL",
    "BERUF": "Beruf",
    "DIAGNOSE": "Diagnose",
    "EIGENE_BEGRIFFE": "Begriff",
    "MANUELL": "Begriff",
}

# Gruppen für die Oberfläche (Reihenfolge = Anzeige)
GRUPPEN = {
    "Personen und Firmen": ["PERSON", "ORGANIZATION"],
    "Kontakt und Anschrift": ["EMAIL_ADDRESS", "TELEFON", "ADRESSE", "PLZ_ORT", "LOCATION", "URL", "IP_ADDRESS"],
    "Akten und Verträge": ["AKTENZEICHEN", "DIKTATZEICHEN", "GRUNDBUCH", "VERSICHERUNGSNR", "DE_HANDELSREGISTER"],
    "Konto und Steuer": ["IBAN_CODE", "KONTONUMMER", "CREDIT_CARD", "DE_TAX_ID", "DE_TAX_NUMBER", "DE_VAT_ID"],
    "Ausweise und Nummern": ["DE_ID_CARD", "DE_PASSPORT", "DE_FUEHRERSCHEIN", "FUEHRERSCHEIN", "DE_SOCIAL_SECURITY",
                             "DE_HEALTH_INSURANCE", "DE_LANR", "DE_BSNR", "PERSONALNR", "KENNNUMMER"],
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
    # Abkürzungen in Befunden und Arztbriefen
    "pat", "pat.", "pt", "pt.", "st.p", "st.p.", "z.n", "z.n.", "v.a", "v.a.", "o.g", "o.g.", "o.b", "o.b.", "amb", "stat",
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
    # Kopfzeilen weitergeleiteter E-Mails ("Weitergeleitete Nachricht", "Ursprüngliche Nachricht")
    "weitergeleitete", "weitergeleitet", "ursprüngliche", "nachricht",
    # Lohn- und Gehaltsabrechnung
    "avmg", "sv", "kv", "rv", "av", "pv", "kv/pv", "ges", "monat", "jahressummen", "steuerklasse", "konfession",
    "personalnummer", "personalabteilung", "abrechnung", "entgeltabrechnung", "berechnungsgrundlage",
    "entgeltbestandteile", "solidaritätszuschlag", "kirchensteuer", "lohnsteuer", "kinderfreibetrag",
}
# Wortteile aus Lohn- und Gehaltsabrechnungen: ein Name/eine Firma, die so beginnt oder endet, ist ein Fachbegriff
# ("Gesamtbrutto", "SV-Brutto", "Krankengeldzuschuss", "AVmG-Brutto", "AN-Anteil", "Schichtzulage")
_LOHN_ENDUNGEN = ("brutto", "netto", "zuschuss", "zuschüsse", "zuschlag", "zulage", "umlage", "entgelt", "bezüge",
                  "vergütung", "lohn", "gehalt", "abzug", "abzüge", "auszahlung", "freibetrag", "beitrag", "beiträge",
                  "anteil", "steuer", "summen", "pflichtig")
_LOHN_ANFAENGE = ("brutto", "netto", "lohnsteuer", "lohnart", "entgelt", "gehalt", "zuschuss", "zulage", "umlage",
                  "beitrag", "auszahlung", "steuerbrutto", "sozialversicherung")
# Geldbetrag, auch aus OCR mit Leerzeichen ("846, 10", "33. 081, 83") – nie eine Kennnummer
_BETRAG_RX = re.compile(r"-?\d{1,3}(?:[.\s]\s?\d{3})*\s?,\s?\d{2}\s?(?:€|EUR)?")
_KVNR_RX = re.compile(r"[A-Za-z]\s?(?:\d\s?){9}")
_RECHTSFORM_RX = re.compile(rf"(?<!\w)(?:{RECHTSFORMEN})(?!\w)")
# Rechtsform am Anfang eines Modelltreffers (ohne "AG", "SE", "Stiftung": "AG Essen", "Stiftung Warentest")
_RECHTSFORM_ANFANG_RX = re.compile(r"(?:gGmbH|GmbH|mbH|KGaA|KG|OHG|GbR|UG|e\.\s?V\.|eG|Inc\.|Ltd\.)(?!\w)")
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
              "mbh", "mbb", "co.", "co", "kg", "ohg", "gbr", "ag", "ug", "se", "gmbh", "gmbh.", "partner"}
# Typen, bei denen ein Modelltreffer ohne Ziffer kein echter Treffer sein kann
NUMERISCHE_TYPEN = {"KFZ", "DE_KFZ", "FUEHRERSCHEIN", "DE_FUEHRERSCHEIN", "VERSICHERUNGSNR", "KONTONUMMER", "AKTENZEICHEN",
                    "FIN", "IBAN_CODE", "TELEFON", "DE_TAX_ID", "DE_TAX_NUMBER", "DE_VAT_ID", "DE_SOCIAL_SECURITY",
                    "DE_HEALTH_INSURANCE", "DE_ID_CARD", "DE_PASSPORT", "DE_LANR", "DE_BSNR", "PERSONALNR", "KENNNUMMER", "DE_HANDELSREGISTER",
                    "ADRESSE", "PLZ_ORT", "CREDIT_CARD"}
NER_ENTITIES = {"PERSON", "ORGANIZATION", "LOCATION"}
# Numerische Typen, die auch mit wenigen Ziffern echt sind ("E-MW 710", "Kaiserstraße 9", "HRA 9921")
_KURZE_NUMMERN = {"KFZ", "DE_KFZ", "ADRESSE", "PLZ_ORT", "AKTENZEICHEN", "DE_HANDELSREGISTER", "TELEFON"}

# Einrichtungen, die im Kanzlei-/Praxisalltag meist stehen bleiben sollen (Profil-Option keep_institutions).
# Lange Wörter als Wortbestandteil, kurze nur als ganzes Wort.
INSTITUTION_WORDS = {
    "gericht", "bußgeldstelle", "staatsanwaltschaft", "polizei", "finanzamt", "behörde", "ministerium", "kammer",
    "krankenhaus", "klinik", "klinikum", "hospital", "seniorenstift", "pflegeheim", "altenheim", "versicherung",
    "versicherer", "sparkasse", "volksbank", "raiffeisenbank", "commerzbank", "postbank", "bankhaus", "krankenkasse",
    "universität", "hochschule", "spital", "ambulanz", "abteilung für", "institut für", "zentrum für", "department",
    "konsil", "lehrkrankenhaus",
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
def _kfz_kuerzen(f: Finding) -> Finding:
    """Kennzeichen aus dem Modell, das zu viel mitnimmt ("BO-SR 618 W0LBF6EC3JG019754"), auf das Kennzeichen
    kürzen. Sonst verdrängt der lange Treffer den richtigen aus der Regel und fällt danach selbst durch."""
    if f.entity in ("KFZ", "DE_KFZ") and f.quelle == "modell":
        m = _KFZ_RX.match(f.text)
        if m and m.end() < len(f.text) and not f.text[m.end()].isalnum():
            return Finding(f.start, f.start + m.end(), f.entity, f.score, m.group(), quelle=f.quelle, grund=f.grund)
    return f


_FILENAME_RX = re.compile(r"[\w\-]+\.(?:py|md|txt|docx?|xlsx?|pptx?|pdf|csv|json|ya?ml|bat|exe|zip|png|jpe?g)", re.IGNORECASE)


@dataclass
class Finding:
    start: int
    end: int
    entity: str
    score: float
    text: str
    active: bool = True
    quelle: str = ""  # "modell", "regel", "liste", "wiederholung", "namensteil", "heuristik", "feld"
    grund: str = ""   # Begründung in Worten für "Prüfen" ("Formularfeld „Vorname“", "bekannter Vorname")


@dataclass
class Result:
    original: str
    findings: list[Finding]
    anonymized: str = ""
    mapping: dict[str, str] = field(default_factory=dict)  # Platzhalter -> Original
    zuordnung: dict[str, str] = field(default_factory=dict)  # Treffer-Text (klein) -> Platzhalter-Schlüssel


# Labels des GLiNER-PII-Modells (englisch, so wurde es trainiert) -> unsere Entitäten
GLINER_NUR_BEKANNTE = True  # nur diese Labels abfragen (False = altes Verhalten mit Rohlabels, nur zum Messen)
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


class _KontextEnhancer(LemmaContextAwareEnhancer):
    """Kontextwörter zählen nur als ganzes Wort, als Wortanfang oder als Ende eines zusammengesetzten Wortes
    ("Geburtsdatum", "Kfz-Versicherung"), kurze (bis 3 Zeichen: "geb", "tel", "az") nur als ganzes Wort.
    Presidios Teilwortsuche wertete "Arbeitgeber" als "geb." und machte Daten im Versicherungsverlauf zu
    Geburtsdaten."""

    @staticmethod
    def _find_supportive_word_in_context(context_list, recognizer_context_list, matching_mode="substring"):
        for kw in recognizer_context_list or []:
            k = kw.lower().strip(".:")
            for w in context_list or []:
                w = w.lower().strip(".:,;()")
                if w == k or (len(k) >= 4 and (w.startswith(k) or w.endswith(k))):
                    return kw
        return ""


def build_analyzer(spacy_model: str = "de_core_news_lg", gliner_model: str | None = None,
                   gliner_threshold: float = 0.5, gliner_onnx_file: str = "", ner_modell: str = "",
                   ner_schwelle: float = 0.5) -> AnalyzerEngine:
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
        gl = GLiNERRecognizer(
            supported_language="de", model_name=gliner_model, entity_mapping=GLINER_MAPPING,
            threshold=gliner_threshold, load_onnx_model=bool(gliner_onnx_file),
            onnx_model_file=gliner_onnx_file or "model.onnx", map_location="cpu",
            chunk_size=1000, chunk_overlap=100,
        )
        if GLINER_NUR_BEKANNTE:
            # Presidio hängt jede angefragte Entität ohne Zuordnung als Rohlabel an ("DIKTATZEICHEN",
            # "EIGENE_BEGRIFFE", "KENNNUMMER" …). Damit kann das Modell nichts anfangen und markiert Laborwerte und
            # Befundsätze. Nur die englischen Labels aus GLINER_MAPPING abfragen.
            gl._GLiNERRecognizer__create_input_labels = lambda _entities: list(gl.gliner_labels)
        registry.add_recognizer(gl)
    if ner_modell:
        from .eigenes_modell import LokanonNER

        registry.add_recognizer(LokanonNER(ner_modell, ner_schwelle))
    # Kontextwörter auch NACH dem Treffer berücksichtigen ("… ist am 02.09.2026 verstorben")
    enhancer = _KontextEnhancer(context_prefix_count=5, context_suffix_count=6)
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


# Produktnamen, die in Kanzleitexten vorkommen und nie eine Person sind (immer erlaubt)
PRODUKTNAMEN = ("Claude", "ChatGPT", "Copilot", "Gemini", "Lokanon")


def make_allow_matcher(allow_list: list[str] | None):
    """Liefert eine Funktion text -> bool. Ein Begriff ist erlaubt, wenn er einem Allow-Eintrag
    entspricht, darin enthalten ist (Namensteil) oder ihn enthält (längere Schreibweise)."""
    entries = []
    for a in [*PRODUKTNAMEN, *(allow_list or [])]:
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


# Gerichtskürzel zählen nur am Anfang ("AG Essen", "LG Duisburg"); "Siemens AG" ist eine Aktiengesellschaft
_GERICHT_KUERZEL = {"ag", "lg", "olg", "pi", "bgh", "bverfg"}


def _is_institution(text: str) -> bool:
    t = text.lower()
    toks = [w for w in re.split(r"[\s\-]+", t) if w]
    if toks and toks[0] in _GERICHT_KUERZEL and len(toks) > 1:
        return True
    return any(w in t for w in INSTITUTION_WORDS) or bool(set(toks) & (INSTITUTION_TOKENS - _GERICHT_KUERZEL))


def _term_findings(text: str, terms: list[str], entity: str, quelle: str = "liste") -> list[Finding]:
    """Alle Vorkommen der Begriffe als ganze Wörter. Bei Personen auch Genitiv ("Schultes Auto")."""
    out = []
    suffix = r"(?:s|es)?" if entity == "PERSON" else ""
    for t in {t.strip() for t in terms if t and t.strip()}:
        for m in re.finditer(rf"(?<!\w){re.escape(t)}{suffix}(?!\w)", text, flags=re.IGNORECASE):
            out.append(Finding(m.start(), m.end(), entity, 1.0, m.group(), quelle=quelle))
    return out


# Automarken: "Skoda Octavia", "Opel Corsa" sind keine Personen oder Firmen im Sinne der Anonymisierung
AUTOMARKEN = {"audi", "bmw", "mercedes", "mercedes-benz", "vw", "volkswagen", "skoda", "škoda", "opel", "ford", "seat",
              "cupra", "toyota", "honda", "mazda", "nissan", "hyundai", "kia", "renault", "peugeot", "citroën", "citroen",
              "fiat", "volvo", "tesla", "porsche", "mini", "smart", "dacia", "suzuki", "mitsubishi", "jeep", "land",
              "jaguar", "alfa", "lexus", "subaru", "byd", "polestar", "lancia", "chevrolet", "ssangyong", "mg"}
_PARTIKEL_KLEIN = {"von", "van", "de", "del", "della", "di", "da", "du", "la", "le", "zu", "zur", "der", "den", "vom",
                   "zum", "und", "ter", "ten", "el", "al", "bin", "ibn"}
_VORNAME_RX = re.compile(r"(?<![\wäöüß\-])([A-ZÄÖÜ][a-zäöüßéèçñşğı]+(?:-[A-ZÄÖÜ][a-zäöüßéèçñşğı]+)?)[ \t]+"
                         r"([A-ZÄÖÜ][a-zäöüßéèçñşğı]+(?:-[A-ZÄÖÜ][a-zäöüßéèçñşğı]+)?)(?![\wäöüß\-])")
_STRASSEN_ENDEN = ("straße", "strasse", "str.", "weg", "allee", "platz", "ring", "gasse", "ufer", "damm", "chaussee")


_ADRESSE_ANKER_RX = re.compile(
    r"(?i)(?:stra(?:ß|ss)e|str\.|weg|allee|platz|ring|gasse|damm|ufer|chaussee|pfad|steig|markt|wall|graben|"
    r"kamp|hof|berg|feld|garten|park|postfach)\b|\b\d{5}\b")
# Parteien "Fischer ./. Hahn": bekannte Namen links und rechts vom Gegen-Zeichen
_PARTEIEN_RX = re.compile(r"(?<![\wäöüß\-])([A-ZÄÖÜ][\wäöüß\-]+)[ \t]+\./\.[ \t]+([A-ZÄÖÜ][\wäöüß\-]+)(?![\wäöüß\-])")


def _parteien(text: str) -> list[Finding]:
    out = []
    for m in _PARTEIEN_RX.finditer(text):
        for g in (1, 2):
            if lexikon.ist_name(m.group(g)):
                out.append(Finding(m.start(g), m.end(g), "PERSON", 0.5, m.group(g), quelle="heuristik",
                                   grund="Partei („… ./. …“)"))
    return out


def _vorname_personen(text: str) -> list[Finding]:
    """Bekannter Vorname + großgeschriebener Nachname ("Monika Klein", "Werner Fuchs"), auch ohne Anrede."""
    out = []
    for m in _VORNAME_RX.finditer(text):
        vor, nach = m.group(1), m.group(2)
        if not lexikon.ist_vorname(vor) or nach.lower().endswith(_STRASSEN_ENDEN):
            continue
        if text[m.end():m.end() + 12].lstrip(" -").lower().startswith(_STRASSEN_ENDEN):
            continue  # "Martin Luther Straße"
        if lexikon.gewoehnlich(nach) or (lexikon.ist_wort(vor) and not lexikon.ist_nachname(nach)):
            continue  # "Rosa Kleid", "Engel Gabriel"
        out.append(Finding(m.start(), m.end(), "PERSON", 0.5, m.group(), quelle="heuristik",
                           grund="bekannter Vorname"))
    return out


def _lexikon_plausibel(f: Finding) -> bool:
    """Wörterbuch-Prüfung für Modelltreffer ohne weiteres Signal (Anrede, Feld, Rechtsform)."""
    woerter = [w.strip(".,:;()\"'„“") for w in f.text.split()]
    kern = [w for w in woerter if w and w.lower() not in TITLES and w.lower() not in _PARTIKEL_KLEIN and w != "&"]
    if not kern:
        return True
    if kern[0].lower() in AUTOMARKEN:
        return False  # "Skoda Octavia"
    if f.entity == "PERSON":
        if len(kern) == 1:
            if kern[0][:1].islower():
                return False  # "insusp", "venöse": Namen sind großgeschrieben
            w = kern[0].capitalize() if kern[0].isupper() and len(kern[0]) > 3 else kern[0]
            return not lexikon.gewoehnlich(w)  # "Gespräch", "Vaters", "Ferienregelung"
        if any(w[:1].islower() for w in kern):
            return False  # "Ileitis terminalis": Namen bestehen aus großgeschriebenen Wörtern
        return any(lexikon.ist_name(w) for w in kern) or not all(lexikon.gewoehnlich(w) for w in kern)
    if f.entity == "ORGANIZATION" and not _RECHTSFORM_RX.search(f.text):
        if len(kern) == 1:
            w = kern[0]
            if w.isupper() and len(w) <= 5:
                return False  # "FAST", "CBCL": Abkürzungen von Testverfahren
            if w.isupper():
                w = w.capitalize()  # "ONKOLOGIE", "DEKURS" (Überschriften in Großbuchstaben)
            return not lexikon.gewoehnlich(w)
        # "Fahrzeug A", "Stadtkasse Essen" – nur gewöhnliche Wörter und einzelne Buchstaben
        return not all(len(w) == 1 or lexikon.gewoehnlich(w) for w in kern)
    return True


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
            return Finding(s, e, f.entity, f.score, text[s:e], f.active, quelle, f.grund)
    if e - s < 2:
        return None
    return Finding(s, e, f.entity, f.score, text[s:e], f.active, f.quelle, f.grund)


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


# Tarifverträge, Betriebsvereinbarungen, Ordnungen: Regelwerke, keine Firmen
_REGELWERK_RX = re.compile(
    r"^(?:G?K?BV|MTV|E?TV|RTV|TVöD|TV-L|TVÜ|DVO|VO|AVR|EntgO|BAT|GBV|KBV|ETV|MTV)(?:[\s.\-]|$)|"
    r"(?i:tarifvertrag|betriebsvereinbarung|dienstvereinbarung|richtlinien?$|verordnung|ordnung$|satzung$)|"
    # Gesetzeskürzel als ein Wort: "SGB", "BetrVG", "EStG", "StPO", "DGL-VO"
    r"^[A-ZÄÖÜ][A-Za-zÄÖÜäöü\-]{0,8}(?:G|GB|VO|PO)$")


# Häufige Endungen von Domains; "A.me", "c.et", "Neurolog.St" in Befunden sind Abkürzungen, keine Adressen
_TLD = {"de", "at", "ch", "li", "lu", "eu", "com", "net", "org", "info", "biz", "io", "me", "tv", "co", "uk", "fr", "it",
        "nl", "be", "dk", "se", "no", "fi", "pl", "cz", "es", "pt", "gov", "edu", "online", "shop", "app", "dev", "berlin",
        "nrw", "bayern", "hamburg", "koeln", "ruhr", "email", "law", "legal", "health", "med", "jobs", "us"}


def _url_plausibel(t: str) -> bool:
    t = t.strip()
    if "://" in t or t.lower().startswith("www."):
        return True
    host = re.split(r"[/:?#]", t, maxsplit=1)[0]
    teile = host.split(".")
    return host == host.lower() and len(teile) >= 2 and teile[-1] in _TLD and len(teile[-2]) >= 2


# Medizinische Endungen (Diagnosen, Eingriffe, Untersuchungen); Namen aus der Namensliste sind ausgenommen
_MEDIZIN_ENDUNGEN = ("itis", "ose", "ämie", "aemie", "algie", "ektomie", "tomie", "skopie", "graphie", "grafie", "plastik",
                     "pathie", "urie", "penie", "zytose", "ismus", "ödem", "oedem", "insuffizienz", "punktion", "resektion",
                     "anamnese", "sonographie", "sonografie", "therapie", "syndrom")
# Dosierung hinter einem Wort: dann ist es ein Medikament ("Concor 5 MG 1-0-0", "Fucidine Salbe", "Novalgin Trpf")
_DOSIS_RX = re.compile(r"[ \t]*(?:\d+(?:[.,]\d+)?[ \t]?(?:mg|µg|ug|mcg|g|ml|IE|I\.E\.|%|mmol|Hub|Trpf|Tbl)(?![\w])|"
                       r"\d[ \t]?-[ \t]?\d[ \t]?-[ \t]?\d|"
                       r"(?:Tbl|Tabl|Tabletten?|Trpf|Tropfen|Salbe|Creme|AT|AS|Drg|Dragees?|Supp|Amp|Kps|Kapseln?|Inj|Gel|"
                       r"Spray|retard|ret\.|forte|comp\.?|Prolong|Depot|Perfusor|s\.c\.|i\.v\.|p\.o\.)(?![\w]))",
                       re.IGNORECASE)


_DARREICHUNG = {"salbe", "creme", "at", "as", "drg", "trpf", "tbl", "tabl", "supp", "amp", "kps", "gel", "spray", "retard",
                "forte", "comp", "prolong", "depot", "perfusor", "tropfen", "tabletten", "kapseln", "lösung", "saft",
                "pflaster", "zäpfchen", "ampullen", "injektion", "infusion"}


def _medizinisch(text: str, f: Finding) -> bool:
    """Medikament, Fachbegriff oder abgekürztes Wort statt Name (nur für Modelltreffer ohne weiteres Signal)."""
    if _DOSIS_RX.match(text, f.end):
        return True
    woerter = [w.strip(",:;()\"'„“") for w in f.text.split()]
    woerter = [w for w in woerter if w and w.lower() not in TITLES]
    if woerter and woerter[-1].lower().rstrip(".") in _DARREICHUNG:
        return True  # "Fucidine Salbe", "Reparil Drg", "Brimonidin AT"
    if len(woerter) > 1 and f.entity == "PERSON" and woerter[0][:1].isupper() and not lexikon.ist_name(woerter[0])             and woerter[0].lower() in lexikon._liste("adjektive"):
        return True  # "Venöse Ekatsie", "Konstitutioneller Zwerchfellhochstand": Namen beginnen nicht mit Adjektiven
    if len(woerter) != 1:
        return bool(woerter) and all(lexikon.ist_medizin(w) or lexikon.gewoehnlich(w.capitalize()) for w in woerter) \
            and any(lexikon.ist_medizin(w) for w in woerter)
    w = woerter[0].rstrip(".")
    if lexikon.ist_name(w) or lexikon.ist_name(w.capitalize()):
        return False
    if lexikon.ist_medizin(w) or w.lower().endswith(_MEDIZIN_ENDUNGEN) or (len(w) >= 7 and w.lower().endswith(("om", "oms"))):
        return True
    abgekuerzt = text[f.end:f.end + 1] == "." or f.text.endswith(".")
    return abgekuerzt and lexikon.ist_abkuerzung(w) and not lexikon.ist_wort(w)


def _plausible(text: str, f: Finding, wa: _Wortarten | None = None) -> bool:
    if f.entity == "URL" and not _url_plausibel(f.text):
        return False
    if f.entity not in NER_ENTITIES:
        if f.entity == "EMAIL_ADDRESS" and "@" not in f.text:
            return False  # "E-Mail-Anschrift"
        if f.entity == "DATUM" and f.quelle in ("modell", "regel"):
            # Daten aus Modell oder Muster nur mit Personenbezug im Umfeld derselben Zeile, als Wortanfang
            # ("geboren", nicht "Arbeitgeber"). Presidios Kontextwörter reichen über Zeilen hinweg ("Datum |
            # 27.10.2026⏎Bußgeldbescheid⏎… geboren am …"), deshalb hier noch einmal enger.
            zs = max(text.rfind("\n", 0, f.start) + 1, f.start - 60)
            ze = text.find("\n", f.end)
            if ze >= 0:  # danach auch die Folgezeile ("ist am 02.09.2026\nim Stift verstorben")
                ze = text.find("\n", ze + 1)
            umfeld = text[zs:min(ze if ze >= 0 else len(text), f.end + 60)].lower()
            return bool(re.search(r"(?<![\wäöüß])(?:" + "|".join(DATUM_KONTEXT_KURZ) + ")", umfeld))
        if f.quelle == "modell":
            if f.entity == "ADRESSE" and not _ADRESSE_ANKER_RX.search(f.text):
                return False  # "Zimmer 2.14": eine Anschrift hat ein Straßenwort, eine Postleitzahl oder "Postfach"
            if f.entity in ("KFZ", "DE_KFZ") and not _KFZ_RX.fullmatch(f.text.strip()):
                return False  # "BMW 320d" ist kein Kennzeichen
            if f.entity in ("FUEHRERSCHEIN", "DE_FUEHRERSCHEIN") and not re.fullmatch(r"[A-Z0-9]{8,14}", f.text.strip()):
                return False  # "Frühjahr 2024" ist keine Führerscheinnummer
            if f.entity in NUMERISCHE_TYPEN:
                digits = sum(ch.isdigit() for ch in f.text)
                if digits == 0 or (f.entity == "KONTONUMMER" and digits < 7):
                    return False
                if digits < 5 and f.entity not in _KURZE_NUMMERN:
                    return False  # "2140", "2455" in einer Tabelle sind keine Steuer-/Versicherungsnummern
                if re.fullmatch(r"-?\d+,\d+", f.text.strip()):
                    return False  # "28,0558" (Entgeltpunkte) ist eine Dezimalzahl
            if f.entity == "DE_HEALTH_INSURANCE" and not _KVNR_RX.fullmatch(f.text.strip()):
                return False  # Krankenversichertennummer = Buchstabe + 9 Ziffern
        if f.entity in NUMERISCHE_TYPEN and f.quelle != "liste" and _BETRAG_RX.fullmatch(f.text.strip()):
            return False  # "846, 10" ist ein Betrag
        return True
    t = f.text.strip().lower()
    if t in NER_STOPWORDS or t.rstrip(".:") in NER_STOPWORDS or len(t) < 3:
        return False
    if not any(ch.isalpha() for ch in t):
        return False  # "__________" (Ausfüllzeile in Formularen) ist kein Name
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
    if f.quelle == "modell" and not _lexikon_plausibel(f):
        return False
    if f.quelle == "modell" and f.entity in ("PERSON", "ORGANIZATION") and not _RECHTSFORM_RX.search(f.text) \
            and _medizinisch(text, f):
        return False
    if any(p.endswith(_LOHN_ENDUNGEN) or p.startswith(_LOHN_ANFAENGE) for p in teile) and not (
            f.entity == "ORGANIZATION" and _RECHTSFORM_RX.search(f.text)):
        return False  # "Gesamtbrutto", "SV-Brutto", "Krankengeldzuschuss" – Fachbegriffe der Lohnabrechnung
    if f.entity == "ORGANIZATION" and _REGELWERK_RX.search(f.text):
        return False  # "MTV Systemgastronomie", "BV Soziale Richtlinien", "DVO.EKD": Tarifverträge und Regelwerke
    if f.entity == "ORGANIZATION" and f.quelle == "modell" and _RECHTSFORM_ANFANG_RX.match(f.text):
        return False  # "GmbH · Postfach": Rechtsform steht am Ende eines Firmennamens, nicht am Anfang
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
        # Lange Wörter auch als Wortanfang ("Amtsgerichts"), Kürzel nur als ganzes Wort ("PI", nicht "PIZ")
        words = sorted(INSTITUTION_WORDS, key=len, reverse=True)
        toks = sorted(INSTITUTION_TOKENS - _GERICHT_KUERZEL - {"stadt", "kreis", "amt", "bank", "stift", "heim"}, key=len,
                      reverse=True)
        rx = re.compile(r"(?<![\wäöüß])(?:(?:" + "|".join(re.escape(w) for w in words) + r")[\wäöüß\-]*|(?:"
                        + "|".join(re.escape(w) for w in toks) + r"|(?:" + "|".join(sorted(_GERICHT_KUERZEL))
                        + r")(?=[ \t]+[A-ZÄÖÜ]))(?![\wäöüß]))", re.IGNORECASE)
        spans += [(m.start(), m.end()) for m in rx.finditer(text) if len(m.group()) > 2]
    for term in getattr(allowed, "terms", []):
        if len(term) >= 4:
            spans += [(m.start(), m.end()) for m in re.finditer(re.escape(term), text, flags=re.IGNORECASE)]
    return spans


def _belongs_to_mention(text: str, f: Finding, mentions: list[tuple[int, int]], abstand: int = 80,
                        personen: list[tuple[int, int]] | None = None,
                        kontakte: list[tuple[int, int]] | None = None) -> bool:
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
    # Anschriftblock unter der Einrichtung ("Amtsgericht Essen\nZweigertstraße 52\n45130 Essen"): Die Zeilen
    # dazwischen dürfen nur aus Kontaktdaten bestehen, sonst gehört die Anschrift zu jemand anderem.
    for _ in range(3):
        if line_start == 0:
            return False
        vor_start = text.rfind("\n", 0, line_start - 1) + 1
        vor_ende = line_start - 1
        if any(vor_start <= ms < vor_ende for ms, _me in mentions):
            return not any(vor_start <= ps and pe <= f.start for ps, pe in (personen or []))
        rest = text[vor_start:vor_ende]
        for ks, ke in sorted(kontakte or [], reverse=True):
            if vor_start <= ks and ke <= vor_ende:
                rest = rest[:ks - vor_start] + rest[ke - vor_start:]
        if re.sub(r"(?i)tel(?:efon|efax|\.)?|fax|e-?mail|[\W\d_]", "", rest).strip():
            return False
        line_start = vor_start
    return False


def _an_spalten_teilen(f: Finding) -> list[Finding]:
    """Ein Treffer über eine Tabellenspalte hinweg ("Koch | Stefanie") wird in Teile zerlegt, Namen und Firmen auch am
    Zeilenumbruch: Ein Modelltreffer "Brüggemann PartG mbB\\nKettwiger Straße" verdrängt sonst in Presidio den
    richtigen kürzeren Regeltreffer und fiele danach selbst durch die Prüfung."""
    trenner = r"[^|\n]+" if f.entity in NER_ENTITIES else r"[^|]+"
    if "|" not in f.text and not (f.entity in NER_ENTITIES and "\n" in f.text):
        return [f]
    return [Finding(f.start + m.start(), f.start + m.end(), f.entity, f.score, m.group(), f.active, f.quelle,
                    f.grund) for m in re.finditer(trenner, f.text) if m.group().strip()]


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
        quelle = "modell" if name in ("SpacyRecognizer", "GLiNERRecognizer", "LokanonNER") else "regel"
        findings.append(Finding(r.start, r.end, r.entity_type, r.score, text[r.start:r.end], quelle=quelle))
    findings += _heuristic_persons(text)
    findings += _vorname_personen(text)
    findings += _parteien(text)
    findings += [f for f in struktur_treffer(text) if f.entity in entities]
    findings += feld_treffer(text, entities)
    findings = [t for f in findings for t in _an_spalten_teilen(f)]
    findings = [c for f in findings if (c := _clean_span(text, f))]
    findings = [_kfz_kuerzen(f) for f in findings]
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
    kontakte = [(f.start, f.end) for f in findings if f.entity in ("ADRESSE", "PLZ_ORT", "TELEFON", "EMAIL_ADDRESS",
                                                                   "URL")]
    findings = [f for f in findings if not _belongs_to_mention(text, f, mentions, personen=personen,
                                                               kontakte=kontakte)]

    findings = _firmenteile_umdeuten(text, findings)
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
        if include_name_parts:
            # Unterscheidendes Wort eines Firmennamens allein ("bei Brandauer" zu "Parfümerie Brandauer GmbH")
            for f in [f for f in findings if f.entity == "ORGANIZATION"]:
                for teil in firmenteile(f.text, allowed):
                    if teil.lower() not in loc_texts:
                        extra += _firmenteil_findings(text, teil, f.text)
        # Bewusst KEINE Ausnahme für Einrichtungen: Was einmal als sensibel gilt, wird überall maskiert
        # (sonst bliebe z. B. die PLZ des Mandanten an der Gerichtsadresse lesbar).
        findings = _resolve_overlaps(findings + extra)

    return findings


def _firmenteile_umdeuten(text: str, findings: list[Finding]) -> list[Finding]:
    """Ein einzelnes Wort, das zu einem erkannten Firmennamen gehört, ist die Firma und keine Person:
    "(Martin Auftragsnummer)" neben "Modehaus Martin GmbH & Co. KG". Mit Anrede oder Titel davor ("Herr Martin")
    und als Teil eines mehrteiligen Personennamens bleibt es eine Person."""
    teile: dict[str, str] = {}
    for o in findings:
        if o.entity == "ORGANIZATION":
            for w in re.findall(r"[A-Za-zÄÖÜäöüß]{3,}", o.text):
                teile.setdefault(w.lower(), o.text)
    if not teile:
        return findings
    in_personen = {w.strip(".,").lower() for f in findings if f.entity == "PERSON" and len(f.text.split()) > 1
                   for w in f.text.split()}
    for f in findings:
        w = f.text.strip()
        if f.entity != "PERSON" or " " in w or w.lower() not in teile or w.lower() in in_personen:
            continue
        davor = text[max(0, f.start - 20):f.start].split()
        if davor and davor[-1].lower().rstrip(".") in {s.rstrip(".") for s in SALUTATIONS + TITLES}:
            continue
        f.entity, f.grund = "ORGANIZATION", f"Teil der Firma „{teile[w.lower()]}“"
    return findings


_FIRMEN_KLEINWORT = {"gmbh", "ggmbh", "mbh", "co", "kg", "kgaa", "ohg", "gbr", "ug", "partg", "mbb", "inc", "ltd",
                     "und", "der", "die", "das", "von", "für", "haftungsbeschränkt"}
_FIRMEN_BRANCHENENDEN = ("bau", "werk", "markt", "haus", "hof", "service", "handel", "technik", "zentrum", "büro")


def _gewoehnliches_firmenwort(w: str) -> bool:
    """Branchen- oder Allerweltswort in einem Firmennamen ("Bäckerei", "Autoservice", "Stahlbau", "Verwaltungs").
    Strenger als lexikon.ist_wort: Zusammensetzungen zählen nur mit einem Grundwort ab 5 Buchstaben, damit
    Nachnamen wie "Brandauer" (Brand+auer) nicht als gewöhnliches Wort gelten."""
    from . import lexikon as L

    if L._einfach(w) or (w.endswith("s") and L._einfach(w[:-1])):
        return True
    low = w.lower()
    if len(low) > 6 and low.endswith(_FIRMEN_BRANCHENENDEN):
        return True
    for i in range(3, len(low) - 4):
        kopf, rest = low[:i], low[i:]
        if not L._einfach(rest):
            continue
        for fuge in L._FUGEN:
            if kopf.endswith(fuge) and len(kopf) - len(fuge) >= 4 and L._einfach(kopf[:len(kopf) - len(fuge)]):
                return True
    return False


def firmenteile(org: str, allowed=None) -> list[str]:
    """Unterscheidende Wörter eines mehrteiligen Firmennamens, die allein für die Firma stehen können:
    "PARFÜMERIE BRANDAUER GMBH & Co. KG" -> ["BRANDAUER"]. Nicht: Rechtsformen, Branchen- und Allerweltswörter
    ("Bäckerei", "Lange", "Sommer"), Bindestrich-Wörter wie "Rhein-Ruhr", Automarken, erlaubte Begriffe."""
    from . import lexikon as L

    woerter = re.findall(r"[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß-]*", org)
    if len(woerter) < 2:
        return []
    out = []
    for w in woerter:
        n = w[0] + w[1:].lower() if w.isupper() else w
        low = n.lower()
        if (len(n) < 4 or not n[0].isupper() or "-" in n or low in _FIRMEN_KLEINWORT or low in NER_STOPWORDS
                or low in FUNKTIONSWOERTER or low in AUTOMARKEN or _gewoehnliches_firmenwort(n)
                or (allowed and allowed(w))):
            continue
        if not L.ist_name(n) and L.ist_wort(n) and L._einfach(n):
            continue
        out.append(w)
    return out


def _firmenteil_findings(text: str, teil: str, org: str) -> list[Finding]:
    """Vorkommen eines Firmenteils als ganzes Wort, in der Schreibweise wie im Firmennamen, groß oder in
    Großbuchstaben ("Brandauer", "BRANDAUER"), nicht klein ("lange")."""
    formen = {teil, teil.upper(), teil[0] + teil[1:].lower()}
    rx = re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(f) for f in sorted(formen, key=len, reverse=True)) + r")(?![\w-])")
    return [Finding(m.start(), m.end(), "ORGANIZATION", 0.01, m.group(), quelle="firmenteil",
                    grund=f"Teil der Firma „{org}“") for m in rx.finditer(text)]


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
    teile = {(t, f.text) for fs in findings_list for f in fs
             if include_name_parts and f.active and f.entity == "ORGANIZATION" and f.quelle != "firmenteil"
             for t in firmenteile(f.text, allowed)}
    out = []
    for text, fs in zip(texte, findings_list):
        vorhanden = {(f.text.lower(), f.entity) for f in fs}
        extra = [x for t, org in teile for x in _firmenteil_findings(text, t, org)]
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
    """Platzhalter-Text, wie er in den Ausgaben steht: "[Person_1]" oder mit eigener Bezeichnung "[Mandant]"."""
    if bezeichnungen and ph in bezeichnungen and bezeichnungen[ph].strip():
        return f"[{bezeichnung_normieren(bezeichnungen[ph])}]"
    return f"[{ph}]"


def bezeichnung_normieren(s: str) -> str:
    """Eigene Bezeichnung -> Platzhalter-Form: Umlaute ersetzt, Leerzeichen zu Unterstrich, Schreibweise bleibt.
    "Mandant" -> "Mandant", "Zeuge Günther" -> "Zeuge_Guenther"."""
    s = s.strip()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss")):
        s = s.replace(a, b)
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s or "Begriff"


def _ph_fuer(text: str, entity: str, reverse: dict[str, str], aliases: dict[str, str] | None = None) -> str | None:
    """Platzhalter-Schlüssel (z. B. "Person_1") für einen Treffer-Text, über Zuordnung, Genitiv und Namensteile."""
    key = text.lower()
    if aliases and key in aliases:
        return reverse.get(aliases[key].lower())
    ph = reverse.get(key)
    if ph is None and entity == "PERSON":
        for suffix in ("s", "es"):  # Genitiv
            if key.endswith(suffix) and key[: -len(suffix)] in reverse:
                return reverse[key[: -len(suffix)]]
        for full_lower, p in reverse.items():  # Namensteil über den vollen Namen
            if key in [w.strip(".,") for w in full_lower.split()]:
                return p
    if ph is None and entity == "ORGANIZATION":
        for full_lower, p in reverse.items():  # Firmenteil über den vollen Firmennamen
            if p.startswith(LABELS["ORGANIZATION"] + "_") and key in re.findall(r"[\wäöüß-]+", full_lower):
                return p
    return ph


def pseudonymize(text: str, findings: list[Finding], mapping: dict[str, str] | None = None,
                 bezeichnungen: dict[str, str] | None = None, aliases: dict[str, str] | None = None,
                 getrennt: set[str] | None = None) -> Result:
    """Ersetzt aktive Treffer durch [Label_n] bzw. die eigene Bezeichnung. Gleiches Original -> gleicher Platzhalter.

    Namensteile ("Müller" aus "Hans Müller") bekommen denselben Platzhalter wie der volle Name.
    Ein vorhandenes mapping (aus demselben Vorgang) wird fortgeführt. bezeichnungen: {"Person_1": "Mandant"}.
    aliases: vom Nutzer zugeordnete Schreibweisen {"günther": "Cornelia Günther"} (klein -> Hauptname).
    getrennt: Schreibweisen (klein), die eine eigene Identität bleiben sollen.
    """
    mapping = dict(mapping or {})
    aliases = {k.lower(): v for k, v in (aliases or {}).items()}
    getrennt = {g.lower() for g in (getrennt or set())}
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

    person_label = LABELS["PERSON"] + "_"
    haeufigkeit: Counter = Counter(f.text for f in active if f.entity == "PERSON")
    for k, v in mapping.items():
        if k.startswith(person_label):
            haeufigkeit[v] += 1
    persons = sorted(haeufigkeit, key=lambda p: (-len(p.split()), -haeufigkeit[p], -len(p)))
    org_label = LABELS["ORGANIZATION"] + "_"
    firmen = {f.text for f in active if f.entity == "ORGANIZATION" and f.quelle != "firmenteil"}
    firmen |= {v for k, v in mapping.items() if k.startswith(org_label)}
    firma_von: dict[str, str] = {}
    for full in sorted(firmen, key=len, reverse=True):
        for t in firmenteile(full):
            firma_von.setdefault(t.lower(), full)
    part_owner = {}
    for full in persons:
        if full.lower() in getrennt and " " not in full:
            continue
        for part in full.split():
            part_owner.setdefault(part.lower().strip(".,"), full)

    def placeholder(f: Finding) -> str:
        key = f.text.lower()
        orig = f.text
        if key in aliases:  # vom Nutzer zugeordnet ("gehört zu …")
            orig = aliases[key]
            key = orig.lower()
            if key in reverse:
                return reverse[key]
        elif key in getrennt:  # vom Nutzer getrennt: eigene Identität
            if key in reverse:
                return reverse[key]
        else:
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
            elif f.entity == "ORGANIZATION" and key in firma_von and firma_von[key].lower() != key:
                orig = firma_von[key]
                key = orig.lower()
            elif key in reverse:
                orig = mapping[reverse[key]]
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
    zuordnung = {f.text.lower(): ph for f, ph in phs}
    out = text
    for f, ph in sorted(phs, key=lambda x: x[0].start, reverse=True):
        out = out[: f.start] + anzeige_platzhalter(ph, bezeichnungen) + out[f.end :]
    return Result(original=text, findings=findings, anonymized=out, mapping=mapping, zuordnung=zuordnung)


def deanonymize(text: str, mapping: dict[str, str], bezeichnungen: dict[str, str] | None = None) -> str:
    """Setzt Platzhalter zurück. Tolerant gegenüber Varianten, die KI-Antworten erzeugen:
    [Person_1], PERSON_1, Person 1, [Person-1], «Person_1», [Person_1]s (Genitiv bleibt erhalten).
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

    gross = {k.upper(): k for k in mapping}  # Schlüssel sind "Person_1"; die KI schreibt auch PERSON_1 / person 1

    def repl(m: re.Match) -> str:
        key = gross.get(f"{m.group('lab').upper()}_{m.group('num')}")
        return mapping[key] if key else m.group(0)

    return rx.sub(repl, text)


def platzhalter_schluessel(findings: list[Finding], mapping: dict[str, str],
                           zuordnung: dict[str, str] | None = None) -> dict[int, str]:
    """Je Treffer (Index in findings) der Platzhalter-Schlüssel ("Person_1"), auch für inaktive Treffer.
    `zuordnung` stammt aus pseudonymize() und hat Vorrang (dieselbe Entscheidung wie in der Ausgabe)."""
    reverse = {v.lower(): k for k, v in mapping.items()}
    out = {}
    for i, f in enumerate(findings):
        ph = (zuordnung or {}).get(f.text.lower()) or _ph_fuer(f.text, f.entity, reverse)
        if ph:
            out[i] = ph
    return out


def replacement_pairs(text: str, findings: list[Finding], mapping: dict[str, str],
                      bezeichnungen: dict[str, str] | None = None,
                      zuordnung: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """Original-Strings -> Platzhalter (für das Ersetzen in DOCX/XLSX/PDF), längste zuerst.
    `zuordnung` aus pseudonymize() hat Vorrang, damit Ausgabe und Anzeige dieselbe Person meinen."""
    reverse = {v.lower(): k for k, v in mapping.items()}
    pairs = {}
    for f in findings:
        if not f.active or len(f.text.strip()) < 3:
            continue
        ph = (zuordnung or {}).get(f.text.lower()) or _ph_fuer(f.text, f.entity, reverse)
        if ph:
            pairs[f.text] = anzeige_platzhalter(ph, bezeichnungen)
    return sorted(pairs.items(), key=lambda kv: len(kv[0]), reverse=True)
