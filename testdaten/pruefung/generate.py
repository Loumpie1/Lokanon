"""Unabhängige Prüfsammlung: 8 erfundene Dokumente (2 je Familie) plus 2 Scans, die bei der Entwicklung der
Erkennung v3 NICHT benutzt wurden. Sie misst, wie gut die Erkennung auf neuen Dokumenten ist – an ihr wird nicht
nachgebessert, sonst verliert sie ihren Wert (dann neue Prüfdokumente anlegen).

Aufruf (aus dem Projektordner, im venv):  python testdaten/pruefung/generate.py
Markup und Regeln wie testdaten/korpus/generate.py (dessen Hilfsfunktionen werden wiederverwendet).
"""
import importlib.util
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("korpus_generate", HIER.parent / "korpus" / "generate.py")
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)
G.OUT = HIER

KANZLEI = G.KANZLEI

# ------------------------------------------------------------------ Schriftsätze
P1 = [
    ("p", f"{KANZLEI}\n{G.KANZLEI_KONTAKT}"),
    ("p", "Landgericht Duisburg\n– Zivilkammer –\nKönig-Heinrich-Platz 1\n47051 Duisburg"),
    ("p", "Essen, 02.11.2026\nAz.: «AKTENZEICHEN|7 S 88/26»"),
    ("h", "Berufungsbegründung"),
    ("p", "In dem Rechtsstreit\nder Frau «PERSON|Helga Nowak», «ADRESSE|Mülheimer Straße 141», «PLZ_ORT|47058 Duisburg»,\n"
          "– Klägerin und Berufungsklägerin –\ngegen\n«ORGANIZATION|Wohnbau Rheinpark Verwaltungs GmbH», vertreten durch "
          "den Geschäftsführer «PERSON|Torsten Reinholz», «ADRESSE|Sonnenwall 64», «PLZ_ORT|47051 Duisburg»,\n"
          "– Beklagte und Berufungsbeklagte –"),
    ("p", "begründen wir die Berufung gegen das Urteil des Amtsgerichts Duisburg vom 18.08.2026. Das Amtsgericht hat "
          "die Mietminderung wegen Schimmelbefalls im Schlafzimmer zu Unrecht abgelehnt. Der Sachverständige "
          "Dipl.-Ing. «PERSON|Uwe Strothmann» hat festgestellt, dass die Feuchtigkeit von einer undichten Fallleitung "
          "ausgeht und nicht auf das Lüftungsverhalten der Klägerin zurückzuführen ist."),
    ("p", "Die Nachbarin, Frau «PERSON|Renata Zielinski», wohnhaft im selben Haus, 2. OG rechts, hat den Wasserschaden "
          "bereits im Februar 2026 der Hausmeisterin Frau «PERSON|Gül» gemeldet. Beweis: Zeugnis der Frau "
          "«PERSON|Zielinski», zu laden über die Klägerin."),
    ("p", "Die Minderungsquote von 20 % der Bruttowarmmiete (Grundmiete 612,00 EUR, Betriebskostenvorauszahlung "
          "190,00 EUR, Heizkostenvorauszahlung 95,00 EUR) ist angemessen."),
    ("p", "Rechtsanwältin Dr. Annette Lehmkuhl"),
]

P2 = [
    ("p", """Von: Dr. Annette Lehmkuhl <kanzlei@lehmkuhl-partner.example>
An: «EMAIL_ADDRESS|schaden.leistung@provinzial-test.example»
Betreff: Ihr Versicherungsnehmer «PERSON|Brandes» – Schaden vom 14.09.2026 – Ihre Schaden-Nr. «VERSICHERUNGSNR|51-2026-339817»

Sehr geehrte Damen und Herren,

wir vertreten Herrn «PERSON|Matthias Oberhaus», «ADRESSE|Gladbecker Straße 77», «PLZ_ORT|45141 Essen». Ihr
Versicherungsnehmer, Herr «PERSON|Felix Brandes», hat am 14.09.2026 beim Rangieren auf dem Parkplatz des Baumarkts
das Fahrzeug unseres Mandanten (VW Passat, «KFZ|E-MO 3471») beschädigt. Die Reparaturkosten belaufen sich laut
Kostenvoranschlag der Firma «ORGANIZATION|Karosseriebau Wessel GmbH» auf 2.940,18 EUR.

Bitte überweisen Sie den Betrag bis zum 20.11.2026 auf das Konto unseres Mandanten,
IBAN «IBAN_CODE|""" + G.iban("36050105", 6603471) + """», Kontoinhaber «PERSON|Matthias Oberhaus».

Mit freundlichen Grüßen

Dr. Annette Lehmkuhl
Rechtsanwältin
Lehmkuhl & Partner Rechtsanwälte"""),
]

# ------------------------------------------------------------------ Bescheide und Formulare
F1 = [
    ("p", "Kreis Recklinghausen · Fachdienst Straßenverkehr · Bußgeldstelle · 45655 Recklinghausen"),
    ("h", "Anhörungsbogen – Verwarnungsgeldverfahren"),
    ("tabelle", [["Aktenzeichen", "«AKTENZEICHEN|36.2-77104/26»"],
                 ["Tattag / Tatzeit", "03.10.2026, 08:12 Uhr"],
                 ["Tatort", "«OPTIONAL|Marl, Bergstraße, Höhe Hausnr. 12»"],
                 ["Kennzeichen", "«KFZ|RE-LT 228»"]], False),
    ("p", "Angaben zur Person (bitte vollständig ausfüllen):"),
    ("tabelle", [["Familienname", "«PERSON|Tiedemann»"],
                 ["Vorname", "«PERSON|Lars»"],
                 ["Geburtsname", "«PERSON|Tiedemann»"],
                 ["Geburtsdatum", "«DATUM|21.06.1987»"],
                 ["Geburtsort", "«OPTIONAL|Herten»"],
                 ["Anschrift", "«ADRESSE|Hülsstraße 19», «PLZ_ORT|45772 Marl»"],
                 ["Beruf", "«OPTIONAL|Elektriker»"]], False),
    ("p", "Ihnen wird vorgeworfen, als Führer des Pkw das Halteverbot missachtet zu haben (§ 12 Abs. 1, § 49 StVO). "
          "Verwarnungsgeld: 25,00 EUR. Sie können sich zur Sache äußern; Sie müssen es nicht."),
    ("p", "Sachbearbeiter: Herr «PERSON|Pohlmann», Durchwahl «OPTIONAL|02361 53-4417»"),
]

F2 = [
    ("h", "Erklärung über die persönlichen und wirtschaftlichen Verhältnisse (Prozesskostenhilfe)"),
    ("tabelle", [["A", "Angaben zu Ihrer Person", ""],
                 ["Name, Vorname, ggf. Geburtsname", "«PERSON|Kurz, Melanie», geb. «PERSON|Hölscher»", ""],
                 ["Geburtsdatum", "«DATUM|09.12.1991»", ""],
                 ["Familienstand", "getrennt lebend", ""],
                 ["Anschrift", "«ADRESSE|Altenessener Straße 312», «PLZ_ORT|45326 Essen»", ""],
                 ["Tagsüber erreichbar unter", "«TELEFON|0162 7730914»", ""]]),
    ("tabelle", [["B", "Unterhaltsberechtigte Angehörige", "Geburtsdatum"],
                 ["Kind", "«PERSON|Noah Kurz»", "«DATUM|14.03.2016»"],
                 ["Kind", "«PERSON|Emilia Kurz»", "«DATUM|30.07.2019»"]]),
    ("tabelle", [["C", "Einnahmen", "monatlich netto"],
                 ["Arbeitgeber", "«ORGANIZATION|Bäckerei Kamphues GmbH & Co. KG»", "1.384,20 EUR"],
                 ["Kindergeld", "Familienkasse NRW", "518,00 EUR"],
                 ["Unterhaltsvorschuss", "Jugendamt Essen", "227,00 EUR"]]),
    ("tabelle", [["D", "Bankverbindung", ""],
                 ["Kontoinhaber", "«PERSON|Melanie Kurz»", ""],
                 ["IBAN", "«IBAN_CODE|" + G.iban("36050105", 8814402) + "»", ""]]),
    ("p", "Ich versichere, dass meine Angaben vollständig und wahr sind."),
]

# ------------------------------------------------------------------ Lohn, Konto, Rechnung
R1 = [
    ("p", "«ORGANIZATION|Autoservice Kalthoff GmbH» · Meisterwerkstatt · «ADRESSE|Hattinger Straße 220» · "
          "«PLZ_ORT|44795 Bochum» · Tel. «TELEFON|0234 4519901»"),
    ("p", "Herrn\n«PERSON|Sebastian Rotthaus»\n«ADRESSE|Wittener Straße 98»\n«PLZ_ORT|44789 Bochum»"),
    ("tabelle", [["Rechnungsnr.", "Kunden-Nr.", "Auftrag", "Datum"],
                 ["«OPTIONAL|W-26-04418»", "«KENNNUMMER|K 77013»", "«OPTIONAL|A-9921»", "29.10.2026"]]),
    ("tabelle", [["Fahrzeug", "Kennzeichen", "Fahrgestell-Nr.", "km-Stand"],
                 ["Opel Astra K 1.4", "«KFZ|BO-SR 618»", "«FIN|W0LBF6EC3JG019754»", "88.410"]]),
    ("h", "Rechnung"),
    ("tabelle", [["Pos.", "Arbeiten / Teile", "Menge", "Preis", "Betrag"],
                 ["1", "Inspektion nach Herstellervorgabe", "1", "189,00", "189,00"],
                 ["2", "Bremsscheiben und Beläge vorne erneuert", "1", "312,40", "312,40"],
                 ["3", "Motoröl 5W-30", "4,5 l", "14,90", "67,05"],
                 ["4", "Hauptuntersuchung (Prüfgebühr TÜV)", "1", "138,00", "138,00"],
                 ["", "Summe netto", "", "", "706,45"], ["", "Umsatzsteuer 19 %", "", "", "134,23"],
                 ["", "Gesamtbetrag", "", "", "840,68"]]),
    ("p", "Betrag dankend per EC-Karte erhalten. Ihr Kundenberater: «PERSON|Dennis Kalthoff»"),
]

R2 = [
    ("h", "Lohnabrechnung Minijob – Oktober 2026"),
    ("tabelle", [["Arbeitgeber", "«PERSON|Ingrid Möllmann», Privathaushalt"],
                 ["Arbeitnehmerin", "«PERSON|Swetlana Bauer»"],
                 ["Anschrift", "«ADRESSE|Krayer Straße 55», «PLZ_ORT|45307 Essen»"],
                 ["Rentenversicherungsnummer", "«DE_SOCIAL_SECURITY|" + G.rvnr("17", "080274", "B", "61") + "»"],
                 ["Steuer-ID", "«STEUER_ID|" + G.steuer_id("8361904275") + "»"],
                 ["Betriebsnummer Haushaltsscheck", "«OPTIONAL|98765432»"]]),
    ("tabelle", [["Lohnart", "Stunden", "Stundenlohn", "Betrag"],
                 ["Haushaltshilfe", "40,00", "13,90", "556,00"],
                 ["Pauschalabgaben (trägt Arbeitgeberin)", "", "", "0,00"],
                 ["Auszahlung", "", "", "556,00"]]),
    ("p", "Auszahlung auf IBAN «IBAN_CODE|" + G.iban("36050105", 2290817) + "» am 30.10.2026."),
]

# ------------------------------------------------------------------ Arzt, Gutachten
M1 = [
    ("p", "Orthopädische Gemeinschaftspraxis Dr. med. «PERSON|Jens Hagemeister» und Dr. med. «PERSON|Aylin Kaya»\n"
          "«ADRESSE|Hauptstraße 31» · «PLZ_ORT|45219 Essen» · Tel. «TELEFON|02054 87120»"),
    ("h", "Befundbericht"),
    ("p", "Patient: «PERSON|Karl-Heinz Wittbrodt», geb. «DATUM|02.02.1954», «ADRESSE|Kirchstraße 6», "
          "«PLZ_ORT|45219 Essen»\nVersichert bei: TK, Vers.-Nr. «DE_HEALTH_INSURANCE|" + G.kvnr("W", "91827364") + "»"),
    ("p", "Diagnosen: Gonarthrose beidseits, rechts betont (M17.0); Z. n. Meniskusteilresektion rechts 2019; "
          "Morbus Dupuytren links (M72.0); Osteoporose ohne pathologische Fraktur (M81.9)."),
    ("p", "Befund: Hinkfreies Gangbild, Kniegelenk rechts mit Erguss, Beugung 0-5-110°, Zohlen-Zeichen positiv, "
          "Bandstabilität erhalten. Röntgen: Gelenkspaltverschmälerung medial, Kellgren-Lawrence Grad III."),
    ("p", "Empfehlung: Physiotherapie 2× wöchentlich, Diclofenac-Gel, Kontrolle in 6 Wochen. Eine Knie-TEP ist mittel"
          "fristig zu erwägen. Der Patient wurde gemeinsam mit seiner Tochter, Frau «PERSON|Sandra Wittbrodt», "
          "aufgeklärt."),
    ("p", "Dr. med. «PERSON|J. Hagemeister»"),
]

M2 = [
    ("h", "Gutachten zur Feuchtigkeitsursache"),
    ("p", "Auftraggeber: Amtsgericht Duisburg, Az. «AKTENZEICHEN|52 C 1190/26»\nObjekt: «ADRESSE|Mülheimer Straße 141», "
          "«PLZ_ORT|47058 Duisburg», Wohnung 2. OG links\nMieterin: Frau «PERSON|Helga Nowak»\n"
          "Eigentümerin: «ORGANIZATION|Wohnbau Rheinpark Verwaltungs GmbH»"),
    ("p", "Ortstermin am 06.10.2026 in Anwesenheit der Mieterin, des Hausmeisters Herrn «PERSON|Dragan Petrović» "
          "und des Vertreters der Eigentümerin, Herrn «PERSON|Reinholz»."),
    ("tabelle", [["Messpunkt", "Raum", "Materialfeuchte", "Oberflächentemperatur"],
                 ["MP 1", "Schlafzimmer, Außenwand Nord", "4,8 %", "13,1 °C"],
                 ["MP 2", "Schlafzimmer, Installationsschacht", "9,6 %", "15,4 °C"],
                 ["MP 3", "Wohnzimmer, Innenwand", "1,2 %", "19,0 °C"]]),
    ("p", "Ergebnis: Die erhöhte Feuchte am Installationsschacht beruht auf einer undichten Fallleitung (Muffe "
          "DN 100). Ein Zusammenhang mit dem Lüftungs- und Heizverhalten der Mieterin besteht nicht. "
          "Schimmelpilzbefall der Gattung Aspergillus und Penicillium auf ca. 1,5 m²."),
    ("p", "Duisburg, 21.10.2026\nDipl.-Ing. «PERSON|Uwe Strothmann»\nÖffentlich bestellter und vereidigter "
          "Sachverständiger für Schäden an Gebäuden"),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    G.faelle.clear()
    print("Prüfdokumente:")
    G.als_docx("P1_Berufung_Nowak.docx", "schriftsatz", P1)
    txt = G.render(P2[0][1])
    (HIER / "P2_EMail_Versicherung_Oberhaus.txt").write_text(txt, encoding="utf-8")
    G.registrieren("P2_EMail_Versicherung_Oberhaus.txt", "schriftsatz", txt.encode("utf-8"), P2)
    f1 = G.als_pdf("F1_Anhoerungsbogen_Tiedemann.pdf", "bescheid_formular", F1)
    G.als_docx("F2_PKH_Erklaerung_Kurz.docx", "bescheid_formular", F2)
    r1 = G.als_pdf("R1_Werkstattrechnung_Rotthaus.pdf", "lohn_konto_rechnung", R1)
    G.als_xlsx("R2_Minijob_Bauer.xlsx", "lohn_konto_rechnung", R2)
    G.als_pdf("M1_Befundbericht_Wittbrodt.pdf", "arzt_gutachten", M1)
    G.als_docx("M2_Feuchtegutachten_Nowak.docx", "arzt_gutachten", M2)
    print("Scans:")
    G.als_scan("F1_Anhoerungsbogen_Tiedemann_scan.pdf", f1, F1, textebene=False, drehung=0.5, seed=11)
    G.als_scan("R1_Werkstattrechnung_Rotthaus_scan.pdf", r1, R1, textebene=True, drehung=-0.6, seed=12)
    with open(HIER / "referenz.jsonl", "w", encoding="utf-8") as fh:
        for f in G.faelle:
            fh.write(json.dumps(f, ensure_ascii=False) + "\n")
    print(f"{len(G.faelle)} Fälle, {sum(len(f['spans']) for f in G.faelle)} markierte Stellen → referenz.jsonl")


if __name__ == "__main__":
    main()
