"""Erzeugt die Testsammlung für die Erkennung: 16 erfundene Dokumente in vier Familien plus 6 Scan-Varianten,
dazu die Referenzmarkierungen (referenz.jsonl) für evaluate.py und tests/test_korpus.py.

Aufruf (aus dem Projektordner, im venv):  python testdaten/korpus/generate.py

Markup im Text: «LABEL|Wert». Wert ist sensibel und muss maskiert werden. Sonderfälle:
  OPTIONAL  darf maskiert werden, muss aber nicht (Behörden-IBAN, Tatort, Rechnungsnummer …)
  INDIREKT  Umschreibung einer Person, wird nicht mitgezählt
Alle Personen, Firmen, Kontakte, Konten und Nummern sind erfunden (Prüfziffern gültig).
Echt sind nur Straßennamen, Städte, Gerichte, Behörden, Kliniken und Versicherer.
Die Goldspannen werden im gelesenen Text gesucht (wie ihn Lokanon sieht); bei Scans also im OCR-Text.
Nicht auffindbare Werte landen unter "fehlend" und zählen als übersehen.
"""
import io
import json
import random
import re
import sys
from pathlib import Path

import docx
import numpy as np
import openpyxl
import pymupdf
from docx.shared import Pt
from openpyxl.styles import Font
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from anonymizer.files import read_document  # noqa: E402

OUT = Path(__file__).resolve().parent
MARK = re.compile(r"«([A-Z_]+)\|([^»]+)»")
faelle = []


# ================================================================== Prüfziffern
def iban(blz, konto):
    bban = f"{blz}{konto:010d}"
    check = 98 - int(bban + "131400") % 97
    raw = f"DE{check:02d}{bban}"
    return " ".join(raw[i:i + 4] for i in range(0, len(raw), 4))


def _mod11_10(ziffern):
    produkt = 10
    for z in ziffern:
        summe = (int(z) + produkt) % 10 or 10
        produkt = (2 * summe) % 11
    p = 11 - produkt
    return "0" if p == 10 else str(p)


def steuer_id(zehn):
    s = zehn + _mod11_10(zehn)
    return f"{s[:2]} {s[2:5]} {s[5:8]} {s[8:]}"


def ust_id(acht):
    return "DE" + acht + _mod11_10(acht)


def rvnr(bereich, geburt, buchstabe, serie):
    """Rentenversicherungsnummer "12 150380 B 123" mit Prüfziffer."""
    z = f"{bereich}{geburt}{ord(buchstabe) - 64:02d}{serie}"
    gew = [2, 1, 2, 5, 7, 1, 2, 1, 2, 1, 2, 1]
    p = sum(sum(divmod(int(a) * g, 10)) for a, g in zip(z, gew)) % 10
    return f"{bereich} {geburt} {buchstabe} {serie}{p}"


def kvnr(buchstabe, acht):
    z = f"{ord(buchstabe) - 64:02d}{acht}"
    p = sum(sum(divmod(int(a) * (1 if i % 2 == 0 else 2), 10)) for i, a in enumerate(z)) % 10
    return f"{buchstabe}{acht}{p}"


def lanr(sechs, fach):
    p = (10 - sum(int(a) * (4 if i % 2 == 0 else 9) for i, a in enumerate(sechs)) % 10) % 10
    return f"{sechs}{p}{fach}"


# ================================================================== Markup
def render(tpl):
    out, pos = [], 0
    for m in MARK.finditer(tpl):
        out.append(tpl[pos:m.start()])
        out.append(m.group(2))
        pos = m.end()
    out.append(tpl[pos:])
    return "".join(out)


def _muster(wert, ocr):
    teile = []
    for ch in wert:
        if ch.isspace():
            teile.append(r"\s*" if ocr else r"\s+")
        else:
            teile.append(re.escape(ch) + (r"\s?" if ocr else ""))
    muster = "".join(teile).removesuffix(r"\s?")
    # PDF-Schriften setzen "ff", "fi", "fl" oft als ein Ligatur-Zeichen ("Hoﬀmann")
    for paar, lig in (("ff", "ﬀ"), ("fi", "ﬁ"), ("fl", "ﬂ")):
        muster = muster.replace(paar, f"(?:{paar}|{lig})")
    return muster


def gold_spans(text, templates, ocr=False):
    werte = {(m.group(1), m.group(2)) for t in templates for m in MARK.finditer(t)}
    spans, fehlend = [], []
    for lab, wert in sorted(werte):
        treffer = list(re.finditer(rf"(?<![\w-]){_muster(wert, ocr)}(?![\w-])", text))
        if not treffer and lab not in ("OPTIONAL", "INDIREKT"):
            fehlend.append([lab, wert])
        spans += [[m.start(), m.end(), lab] for m in treffer]
    # Teiltreffer innerhalb längerer Markierungen entfernen ("Engel" in "Sabine Engel")
    spans = [s for s in spans if not any(o != s and o[0] <= s[0] and o[1] >= s[1] for o in spans)]
    return sorted(spans), fehlend


def _alle_texte(blocks):
    for b in blocks:
        if b[0] == "tabelle":
            yield from (c for row in b[1] for c in row if isinstance(c, str))
        else:
            yield b[1]


def registrieren(datei, familie, data, blocks, ocr=False):
    text, info = read_document(datei, data)
    spans, fehlend = gold_spans(text, list(_alle_texte(blocks)), ocr=ocr)
    seiten = info.get("seiten") or max(1, round(len(text) / 2800))
    faelle.append({"datei": datei, "familie": familie, "seiten": seiten, "text": text, "spans": spans,
                   "fehlend": fehlend})
    print(f"  {datei:<48} {len(spans):>3} Stellen" + (f", {len(fehlend)} nicht lesbar" if fehlend else ""))


# ================================================================== Ausgabeformate
def als_docx(datei, familie, blocks):
    d = docx.Document()
    d.styles["Normal"].font.name = "Calibri"
    d.styles["Normal"].font.size = Pt(10.5)
    for b in blocks:
        if b[0] == "h":
            d.add_heading(render(b[1]), level=2)
        elif b[0] in ("p", "klein"):
            for zeile in render(b[1]).split("\n"):
                d.add_paragraph(zeile)
        else:
            rows = b[1]
            t = d.add_table(rows=len(rows), cols=max(len(r) for r in rows))
            t.style = "Table Grid"
            for r, row in enumerate(rows):
                for c, val in enumerate(row):
                    t.cell(r, c).text = render(str(val))
    buf = io.BytesIO()
    d.save(buf)
    (OUT / datei).write_bytes(buf.getvalue())
    registrieren(datei, familie, buf.getvalue(), blocks)


CSS = """
* { font-family: sans-serif; font-size: 9.5pt; }
h2 { font-size: 13pt; font-weight: bold; margin-bottom: 6pt; }
p { margin-bottom: 6pt; }
table { border-collapse: collapse; margin-bottom: 8pt; }
td { border: 0.5pt solid #888; padding: 2pt 4pt; }
tr.kopf td { font-weight: bold; background: #ddd; }
.klein { font-size: 7.5pt; }
"""


def _html(blocks):
    def esc(s):
        return render(s).replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br/>")

    teile = []
    for b in blocks:
        if b[0] == "h":
            teile.append(f"<h2>{esc(b[1])}</h2>")
        elif b[0] in ("p", "klein"):
            teile.append(f'<p class="{b[0]}">{esc(b[1])}</p>')
        else:
            rows = b[1]
            kopf = len(b) < 3 or b[2]
            zeilen = []
            for i, row in enumerate(rows):
                cls = ' class="kopf"' if kopf and i == 0 else ""
                zeilen.append(f"<tr{cls}>" + "".join(f"<td>{esc(str(c))}</td>" for c in row) + "</tr>")
            teile.append("<table>" + "".join(zeilen) + "</table>")
    return "".join(teile)


def pdf_bytes(blocks):
    story = pymupdf.Story(_html(blocks), user_css=CSS)
    buf = io.BytesIO()
    writer = pymupdf.DocumentWriter(buf)
    seite, rand = pymupdf.paper_rect("a4"), 50
    where = pymupdf.Rect(seite.x0 + rand, seite.y0 + rand, seite.x1 - rand, seite.y1 - rand)
    mehr = True
    while mehr:
        dev = writer.begin_page(seite)
        mehr, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()
    return buf.getvalue()


def als_pdf(datei, familie, blocks):
    data = pdf_bytes(blocks)
    (OUT / datei).write_bytes(data)
    registrieren(datei, familie, data, blocks)
    return data


def als_xlsx(datei, familie, blocks):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Abrechnung"
    r = 1
    for b in blocks:
        rows = b[1] if b[0] == "tabelle" else [[b[1]]]
        for i, row in enumerate(rows):
            for c, val in enumerate(row, 1):
                v = render(val) if isinstance(val, str) else val
                if isinstance(v, str) and re.fullmatch(r"-?\d{1,3}(\.\d{3})*,\d{2}", v):
                    v = float(v.replace(".", "").replace(",", "."))
                cell = ws.cell(r, c, v)
                if b[0] == "h" or (b[0] == "tabelle" and i == 0):
                    cell.font = Font(bold=True)
            r += 1
        r += 1
    buf = io.BytesIO()
    wb.save(buf)
    (OUT / datei).write_bytes(buf.getvalue())
    registrieren(datei, familie, buf.getvalue(), blocks)


def als_scan(datei, pdf_data, blocks, textebene, drehung, seed):
    """PDF rendern → leicht gedreht und verrauscht als Bild; optional unsichtbare Textebene wie beim Kopierer."""
    rnd = np.random.default_rng(seed)
    src = pymupdf.open(stream=pdf_data, filetype="pdf")
    scan = pymupdf.open()
    for page in src:
        pix = page.get_pixmap(dpi=200, colorspace=pymupdf.csGRAY)
        img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
        img = img.rotate(drehung, resample=Image.BICUBIC, fillcolor=255)
        a = np.asarray(img).astype(np.int16) + rnd.normal(0, 10, (img.height, img.width)).astype(np.int16)
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=70)
        sp = scan.new_page(width=page.rect.width, height=page.rect.height)
        sp.insert_image(sp.rect, stream=buf.getvalue())
        if textebene:
            for b in page.get_text("dict")["blocks"]:
                for line in b.get("lines", []):
                    for s in line["spans"]:
                        if s["text"].strip():
                            sp.insert_text(s["origin"], s["text"], fontsize=s["size"], render_mode=3)
    data = scan.tobytes(garbage=4, deflate=True)
    (OUT / "scan").mkdir(exist_ok=True)
    (OUT / "scan" / datei).write_bytes(data)
    registrieren(datei, "scans", data, blocks, ocr=True)


# ================================================================== Kanzlei und gemeinsame Figuren
KANZLEI = "Lehmkuhl & Partner Rechtsanwälte · Rüttenscheider Straße 120 · 45130 Essen"
KANZLEI_KONTAKT = "Tel. 0201 8945120 · kanzlei@lehmkuhl-partner.example"
IBAN_FISCHER = iban("36050105", 4471120)
IBAN_BECKER = iban("36250000", 1188204)
IBAN_WOLF = iban("36050105", 7730115)
IBAN_HOFFMANN = iban("36010043", 902211)
IBAN_ENGEL = iban("35060190", 1520033)
IBAN_KLEIN = iban("36050105", 5560042)
IBAN_STADTKASSE = iban("36050105", 207)

# ================================================================== Familie 1: Schriftsätze, Briefe, E-Mails
S1 = [
    ("p", f"{KANZLEI}\n{KANZLEI_KONTAKT}"),
    ("p", "Amtsgericht Essen\nZweigertstraße 52\n45130 Essen"),
    ("p", "Essen, 03.11.2026"),
    ("h", "Klage"),
    ("p", "des Herrn «PERSON|Andreas Fischer», «ADRESSE|Frohnhauser Straße 212», «PLZ_ORT|45144 Essen»,\n"
          "– Kläger –\nProzessbevollmächtigte: Lehmkuhl & Partner Rechtsanwälte, Rüttenscheider Straße 120, 45130 Essen"),
    ("p", "gegen\n1. Herrn «PERSON|Dennis Hahn», «ADRESSE|Gemarkenstraße 77», «PLZ_ORT|45147 Essen»,\n"
          "2. Allianz Versicherungs-AG, vertreten durch den Vorstand, Königinstraße 28, 80802 München,\n"
          "– Beklagte –"),
    ("p", "wegen Schadensersatz aus Verkehrsunfall\nStreitwert: 4.812,37 EUR"),
    ("p", "Namens und in Vollmacht des Klägers erheben wir Klage und werden beantragen:\n"
          "1. Die Beklagten werden als Gesamtschuldner verurteilt, an den Kläger 4.812,37 EUR nebst Zinsen in Höhe "
          "von fünf Prozentpunkten über dem Basiszinssatz seit dem 15.09.2026 zu zahlen.\n"
          "2. Die Beklagten tragen die Kosten des Rechtsstreits."),
    ("h", "Begründung"),
    ("p", "Am 21.08.2026 gegen 16:40 Uhr befuhr der Kläger mit seinem Pkw Skoda Octavia, amtliches Kennzeichen "
          "«KFZ|E-AF 2187», die «OPTIONAL|Hans-Böckler-Straße» in Essen. Der Beklagte zu 1. fuhr mit dem bei der "
          "Beklagten zu 2. haftpflichtversicherten Pkw, Kennzeichen «KFZ|E-DH 904», aus einer Grundstückseinfahrt "
          "heraus und missachtete die Vorfahrt des Klägers (§ 10 StVO)."),
    ("p", "Beweis: Zeugnis der Frau «PERSON|Lea Vogel», «ADRESSE|Kahrstraße 49», «PLZ_ORT|45128 Essen»\n"
          "Beweis: Sachverständigengutachten des Dipl.-Ing. «PERSON|Holger Brandt» vom 28.08.2026 (Anlage K 2)"),
    ("p", "Die Beklagte zu 2. hat unter der Schadennummer «VERSICHERUNGSNR|KH-2026-0815-4471» lediglich 50 % "
          "reguliert und beruft sich auf eine Haftungsquote. Der Kläger macht den restlichen Schaden geltend: "
          "Reparaturkosten 3.912,37 EUR, Wertminderung 450,00 EUR, Nutzungsausfallentschädigung für 9 Tage "
          "425,00 EUR, Kostenpauschale 25,00 EUR."),
    ("p", "Herr «PERSON|Fischer» ist auf das Fahrzeug angewiesen, weil er als «INDIREKT|einziger Hufschmied im "
          "Essener Süden» täglich Höfe anfährt."),
    ("p", "Rechtsanwältin Dr. Annette Lehmkuhl"),
]

S2 = [
    ("p", "«ORGANIZATION|Brüggemann Rechtsanwälte PartG mbB»\n«ADRESSE|Kettwiger Straße 20» · «PLZ_ORT|45127 Essen»\n"
          "Telefon «TELEFON|0201 7712430» · Telefax «TELEFON|0201 7712439»\n«EMAIL_ADDRESS|f.brueggemann@brueggemann-ra.example»"),
    ("p", "Lehmkuhl & Partner Rechtsanwälte\nRüttenscheider Straße 120\n45130 Essen"),
    ("p", "Unser Zeichen: «AKTENZEICHEN|112/26 FB/kl»\nIhr Zeichen: «AKTENZEICHEN|LP-2026/0533»\nEssen, 29.10.2026"),
    ("p", "Ihr Mandant «PERSON|Fischer» ./. «PERSON|Hahn»\nVerkehrsunfall vom 21.08.2026"),
    ("p", "Sehr geehrte Frau Kollegin Dr. Lehmkuhl,"),
    ("p", "wir zeigen an, dass wir Herrn «PERSON|Dennis Hahn» vertreten. Ihr Schreiben vom 12.10.2026 liegt uns vor. "
          "Unser Mandant bestreitet, die Vorfahrt missachtet zu haben. Er war bereits auf die Fahrbahn eingefahren, "
          "als Ihr Mandant mit überhöhter Geschwindigkeit herankam. Die Zeugin «PERSON|Vogel» konnte den Unfallhergang "
          "von ihrem Standort aus nicht einsehen."),
    ("p", "Eine Haftung über die bereits regulierte Quote hinaus lehnen wir ab. Zur Vermeidung eines Rechtsstreits "
          "wäre unser Mandant bereit, weitere 500,00 EUR ohne Anerkennung einer Rechtspflicht zu zahlen."),
    ("p", "Mit freundlichen kollegialen Grüßen\n\nDr. «PERSON|Felix Brüggemann»\nRechtsanwalt\n"
          "Fachanwalt für Verkehrsrecht"),
]

S3 = [
    ("p", """Von: Sabine Engel <«EMAIL_ADDRESS|sabine.engel@posteo.example»>
Gesendet: Montag, 2. November 2026 21:14
An: kanzlei@lehmkuhl-partner.example
Betreff: WG: Kündigung – bitte um Rückruf

Sehr geehrte Frau Dr. Lehmkuhl,

anbei die Mail meines Arbeitgebers. Ich bin seit 2014 dort im Lager beschäftigt und habe am Freitag die Kündigung
bekommen. Mein Mann «PERSON|Thomas Engel» meint, das sei wegen meiner Krankmeldungen. Sie erreichen mich mobil unter
«TELEFON|0157 39942817», tagsüber bitte nicht über die Firma.

Viele Grüße
«PERSON|Sabine Engel»
«ADRESSE|Bochumer Straße 18», «PLZ_ORT|45276 Essen»

-------- Weitergeleitete Nachricht --------
Von: Markus Brenner <«EMAIL_ADDRESS|m.brenner@rrl-kessler.example»>
Datum: Freitag, 30. Oktober 2026 14:02
An: «EMAIL_ADDRESS|s.engel@rrl-kessler.example»
Betreff: Ihr Arbeitsverhältnis

Sehr geehrte Frau «PERSON|Engel»,

wie heute im Gespräch mit Herrn «PERSON|Kessler» besprochen, erhalten Sie die Kündigung zum 31.01.2027 per Boten.
Ihre Personalnummer «PERSONALNR|004417» bleibt bis dahin aktiv. Resturlaub und Überstunden werden mit der
Abrechnung Januar ausgezahlt.

Mit freundlichen Grüßen

«PERSON|Markus Brenner»
Leitung Personalabteilung
«ORGANIZATION|Rhein-Ruhr Logistik Kessler GmbH»
«ADRESSE|Weseler Straße 301» | «PLZ_ORT|45478 Mülheim an der Ruhr»
Tel. «TELEFON|+49 208 445566-12» | Mobil «TELEFON|0171 2233445»
Geschäftsführer: «PERSON|Jürgen Kessler» | Amtsgericht Duisburg «AKTENZEICHEN|HRB 31877»

Diese E-Mail enthält vertrauliche Informationen. Wenn Sie nicht der richtige Adressat sind, informieren Sie bitte
den Absender und löschen Sie diese Nachricht."""),
]

S4 = [
    ("h", "Vollmacht"),
    ("p", "Hiermit wird der Kanzlei Lehmkuhl & Partner Rechtsanwälte, Rüttenscheider Straße 120, 45130 Essen,"),
    ("p", "in Sachen «PERSON|Engel» ./. «ORGANIZATION|Rhein-Ruhr Logistik Kessler GmbH»\n"
          "wegen Kündigungsschutz"),
    ("p", "Vollmacht erteilt zur Prozessführung (u. a. nach §§ 81 ff. ZPO) einschließlich der Befugnis zur Erhebung "
          "und Zurücknahme von Widerklagen, zur außergerichtlichen Verhandlung, zum Abschluss eines Vergleichs, zur "
          "Entgegennahme von Zahlungen und zur Akteneinsicht."),
    ("tabelle", [["Vollmachtgeberin", "«PERSON|Sabine Engel»"],
                 ["geboren am", "«DATUM|17.02.1981»"],
                 ["Anschrift", "«ADRESSE|Bochumer Straße 18», «PLZ_ORT|45276 Essen»"],
                 ["Telefon", "«TELEFON|0157 39942817»"],
                 ["Rechtsschutzversicherung", "ARAG SE, Versicherungsschein «VERSICHERUNGSNR|RS-7720-114932»"]],
     False),
    ("p", "Essen, den 03.11.2026\n\n______________________________\n(Unterschrift)"),
]

# ================================================================== Familie 2: Bescheide und Formulare
B1 = [
    ("p", "Stadt Essen · Der Oberbürgermeister · Bußgeldstelle · 45121 Essen"),
    ("p", "Herrn\n«PERSON|Kevin Bauer»\n«ADRESSE|Altendorfer Straße 402»\n«PLZ_ORT|45143 Essen»"),
    ("tabelle", [["Aktenzeichen", "«AKTENZEICHEN|7.1-618204/26»"],
                 ["Kassenzeichen", "«KENNNUMMER|5.2026.4418.0731»"],
                 ["Sachbearbeitung", "Frau «PERSON|Kowalski», Zimmer 2.14"],
                 ["Datum", "27.10.2026"]], False),
    ("h", "Bußgeldbescheid"),
    ("p", "Gegen Sie, geboren am «DATUM|08.04.1996» in «OPTIONAL|Bottrop», wird wegen der folgenden "
          "Ordnungswidrigkeit eine Geldbuße festgesetzt:"),
    ("p", "Sie überschritten am 12.09.2026 um 22:17 Uhr in Essen, «OPTIONAL|Alfredstraße 120», Fahrtrichtung Süd, "
          "als Führer des Pkw Ford Focus, amtliches Kennzeichen «KFZ|E-KB 4096», die zulässige Höchstgeschwindigkeit "
          "innerhalb geschlossener Ortschaften um 24 km/h. Zulässige Geschwindigkeit: 50 km/h. Festgestellte "
          "Geschwindigkeit (nach Toleranzabzug): 74 km/h. § 41 Abs. 1 i. V. m. Anlage 2, § 49 StVO; § 24 StVG; "
          "11.3.4 BKat."),
    ("p", "Beweismittel: Messung mit PoliScan Speed, Messbeamter POK «PERSON|Wagner», Lichtbild"),
    ("tabelle", [["Geldbuße", "150,00 EUR"], ["Gebühren", "28,50 EUR"], ["Auslagen", "3,50 EUR"],
                 ["Gesamtbetrag", "182,00 EUR"]]),
    ("p", "Im Fahreignungsregister wird 1 Punkt eingetragen. Zahlen Sie bitte unter Angabe des Kassenzeichens an "
          "die Stadtkasse Essen, IBAN «OPTIONAL|" + IBAN_STADTKASSE + "»."),
    ("klein", "Rechtsbehelfsbelehrung: Gegen diesen Bescheid können Sie innerhalb von zwei Wochen nach Zustellung "
              "Einspruch bei der oben genannten Behörde einlegen."),
]

B2 = [
    ("h", "Schadenmeldung Kfz-Haftpflicht / Kasko"),
    ("p", "HUK-COBURG · Bahnhofsplatz · 96444 Coburg"),
    ("tabelle", [["Versicherungsnehmer", ""],
                 ["Name", "«PERSON|Schneider»"],
                 ["Vorname", "«PERSON|Monika»"],
                 ["Geburtsdatum", "«DATUM|23.11.1968»"],
                 ["Straße, Hausnr.", "«ADRESSE|Hingbergstraße 112»"],
                 ["PLZ, Ort", "«PLZ_ORT|45472 Mülheim an der Ruhr»"],
                 ["Telefon", "«TELEFON|0208 4419273»"],
                 ["E-Mail", "«EMAIL_ADDRESS|monika.schneider@web.example»"],
                 ["Versicherungsschein-Nr.", "«VERSICHERUNGSNR|KF 772-410933-2»"],
                 ["Schadennummer", "«VERSICHERUNGSNR|26-41-118730-5»"],
                 ["Amtl. Kennzeichen", "«KFZ|MH-MS 1123»"],
                 ["Fahrzeug-Ident.-Nr.", "«FIN|WVWZZZAUZLW508812»"]], True),
    ("tabelle", [["Schadentag", "Uhrzeit", "Schadenort"],
                 ["30.10.2026", "07:50", "«OPTIONAL|Mülheim, Parkplatz Kaufland Dümptener Straße»"]]),
    ("p", "Schadenhergang: Beim Ausparken bin ich rückwärts gegen den geparkten Pkw von Herrn «PERSON|Peter Krause» "
          "gestoßen (Stoßfänger hinten links). Herr «PERSON|Krause» war vor Ort, wir haben die Daten ausgetauscht. "
          "Ein Polizeibericht wurde nicht aufgenommen. Personenschaden: keiner."),
    ("tabelle", [["Zeuge", "Anschrift", "Telefon"],
                 ["«PERSON|Ayşe Demir»", "«ADRESSE|Aktienstraße 88», «PLZ_ORT|45473 Mülheim an der Ruhr»",
                  "«TELEFON|0176 55120983»"]]),
    ("tabelle", [["Bankverbindung für die Regulierung", ""],
                 ["Kontoinhaber", "«PERSON|Monika Schneider»"],
                 ["IBAN", "«IBAN_CODE|" + iban("36250000", 6612090) + "»"],
                 ["Kreditinstitut", "Sparkasse Mülheim an der Ruhr"]], True),
    ("p", "Ich versichere, die Angaben wahrheitsgemäß gemacht zu haben.\nMülheim, 31.10.2026   Unterschrift"),
]

B3 = [
    ("h", "Europäischer Unfallbericht"),
    ("p", "1. Datum des Unfalls: 18.10.2026   Uhrzeit: 11:25   2. Ort: «OPTIONAL|Essen, Kreuzung Rüttenscheider "
          "Straße / Martinstraße»   3. Verletzte: nein"),
    ("tabelle", [["", "Fahrzeug A", "Fahrzeug B"],
                 ["Versicherungsnehmer Name", "«PERSON|Koch»", "«PERSON|Wolf»"],
                 ["Vorname", "«PERSON|Stefanie»", "«PERSON|Michael»"],
                 ["Anschrift", "«ADRESSE|Moltkestraße 41», «PLZ_ORT|45138 Essen»",
                  "«ADRESSE|Ruhrallee 155», «PLZ_ORT|45136 Essen»"],
                 ["Telefon oder E-Mail", "«TELEFON|0201 2271904»", "«EMAIL_ADDRESS|m.wolf@gmx.example»"],
                 ["Marke, Typ", "Opel Corsa", "Mercedes-Benz C 200"],
                 ["Amtl. Kennzeichen", "«KFZ|E-SK 3318»", "«KFZ|E-MW 710»"],
                 ["Versicherer", "DEVK", "R+V Allgemeine Versicherung AG"],
                 ["Versicherungsschein-Nr.", "«VERSICHERUNGSNR|9017-3312-55»", "«VERSICHERUNGSNR|KH 4471 0092 31»"],
                 ["Fahrer Name, Vorname", "«PERSON|Koch, Stefanie»", "«PERSON|Wolf, Lukas»"],
                 ["Geburtsdatum Fahrer", "«DATUM|02.07.1990»", "«DATUM|19.12.2003»"],
                 ["Führerschein-Nr.", "«FUEHRERSCHEIN|B072K4LM913»", "«FUEHRERSCHEIN|J221P8QR405»"],
                 ["Sichtbare Schäden", "Kotflügel vorne rechts", "Stoßfänger hinten, Heckklappe"]]),
    ("p", "Bemerkungen: Fahrzeug B bremste wegen eines Fußgängers stark ab, Fahrzeug A fuhr auf. "
          "Fahrer B ist der Sohn des Versicherungsnehmers."),
]

B4 = [
    ("p", "Deutsche Rentenversicherung Westfalen · 48125 Münster"),
    ("p", "Frau\n«PERSON|Renate Hoffmann»\n«ADRESSE|Sandstraße 14»\n«PLZ_ORT|45478 Mülheim an der Ruhr»"),
    ("tabelle", [["Versicherungsnummer", "«DE_SOCIAL_SECURITY|" + rvnr("12", "250361", "H", "50") + "»"],
                 ["Datum", "20.10.2026"]], False),
    ("h", "Rentenbescheid – Rente wegen voller Erwerbsminderung"),
    ("p", "Sehr geehrte Frau «PERSON|Hoffmann», auf Ihren Antrag vom 04.05.2026 erhalten Sie Rente wegen voller "
          "Erwerbsminderung. Die Rente beginnt am 01.06.2026 und ist befristet bis zum 31.05.2029."),
    ("tabelle", [["Berechnungsgrundlage", "Wert"],
                 ["Summe der Entgeltpunkte", "31,4527"], ["Zugangsfaktor", "0,8920"],
                 ["Persönliche Entgeltpunkte", "28,0558"], ["Rentenartfaktor", "1,0"],
                 ["Aktueller Rentenwert", "40,79 EUR"], ["Monatliche Rente", "1.144,40 EUR"],
                 ["Beitragsanteil Krankenversicherung", "-83,54 EUR"],
                 ["Beitragsanteil Pflegeversicherung", "-41,20 EUR"], ["Zahlbetrag", "1.019,66 EUR"]]),
    ("p", "Versicherungsverlauf (Auszug):"),
    ("tabelle", [["Zeitraum", "Art", "Arbeitgeber"],
                 ["01.09.1977 – 31.08.1980", "Berufsausbildung", "«ORGANIZATION|Bäckerei Overmann KG»"],
                 ["01.09.1980 – 30.06.2004", "Pflichtbeiträge", "«ORGANIZATION|Stahlbau Kerkhoff GmbH»"],
                 ["01.07.2004 – 31.03.2026", "Pflichtbeiträge", "«ORGANIZATION|Seniorenzentrum Haus am Kahlenberg gGmbH»"]]),
    ("p", "Die Rente wird auf das Konto IBAN «IBAN_CODE|" + iban("36050105", 3304187) + "» überwiesen. "
          "Kranken- und Pflegeversicherung: BARMER."),
    ("klein", "Gegen diesen Bescheid können Sie innerhalb eines Monats nach Bekanntgabe Widerspruch erheben."),
]

# ================================================================== Familie 3: Lohn, Konto, Rechnung
L1 = [
    ("p", "«ORGANIZATION|Rhein-Ruhr Logistik Kessler GmbH» · «ADRESSE|Weseler Straße 301» · "
          "«PLZ_ORT|45478 Mülheim an der Ruhr»"),
    ("p", "Herrn\n«PERSON|Jan Becker»\n«ADRESSE|Lindenstraße 7»\n«PLZ_ORT|46045 Oberhausen»"),
    ("h", "Abrechnung der Brutto/Netto-Bezüge für Oktober 2026"),
    ("tabelle", [["Personalnummer", "Steuerklasse", "Kinderfreibetrag", "Konfession", "Eintritt"],
                 ["«PERSONALNR|004711»", "1", "0,0", "rk", "«OPTIONAL|01.04.2015»"]]),
    ("tabelle", [["Steuer-ID", "SV-Nummer", "Krankenkasse", "Geburtsdatum"],
                 ["«STEUER_ID|" + steuer_id("5728146395") + "»",
                  "«DE_SOCIAL_SECURITY|" + rvnr("13", "150380", "B", "12") + "»", "AOK Rheinland/Hamburg",
                  "«DATUM|15.03.1980»"]]),
    ("tabelle", [["Entgeltbestandteile", "Menge", "Betrag", "Jahressumme"],
                 ["Grundvergütung", "", "3.412,50", "34.125,00"],
                 ["Schichtzulage", "12,00", "212,00", "2.120,00"],
                 ["Krankengeldzuschuss ges.", "", "846,10", "846,10"],
                 ["Vermögenswirksame Leistungen", "", "40,00", "400,00"],
                 ["Gesamtbrutto", "", "4.510,60", "37.491,10"],
                 ["Steuer-Brutto", "", "4.510,60", "37.491,10"],
                 ["SV-Brutto KV/PV", "", "4.510,60", "36.645,00"],
                 ["SV-Brutto RV/AV", "", "4.510,60", "36.645,00"],
                 ["AVmG-Brutto", "", "846,10", "846,10"]]),
    ("tabelle", [["Abzüge", "Betrag"],
                 ["Lohnsteuer", "612,33"], ["Solidaritätszuschlag", "0,00"], ["Kirchensteuer", "49,00"],
                 ["Krankenversicherung AN-Anteil", "394,68"], ["Rentenversicherung AN-Anteil", "419,49"],
                 ["Arbeitslosenversicherung AN-Anteil", "58,64"], ["Pflegeversicherung AN-Anteil", "81,19"],
                 ["VWL-Überweisung", "40,00"], ["Auszahlungsbetrag", "2.855,27"]]),
    ("p", "Überweisung auf IBAN «IBAN_CODE|" + IBAN_BECKER + "» bei der Sparkasse Oberhausen."),
    ("klein", "Rückfragen: Personalabteilung, Herr «PERSON|Brenner», Durchwahl «TELEFON|0208 445566-12»"),
]

L2 = [
    ("p", "Sparkasse Essen · Kontoauszug 10/2026 · Blatt 1"),
    ("tabelle", [["Kontoinhaber", "«PERSON|Petra Wolf» und «PERSON|Michael Wolf»"],
                 ["Anschrift", "«ADRESSE|Ruhrallee 155», «PLZ_ORT|45136 Essen»"],
                 ["IBAN", "«IBAN_CODE|" + IBAN_WOLF + "»"], ["BIC", "SPESDE3EXXX"],
                 ["Kontostand alt 30.09.2026", "1.742,18 Haben"]], False),
    ("tabelle", [["Buchungstag", "Wertstellung", "Vorgang / Verwendungszweck", "Betrag"],
                 ["01.10.", "01.10.", "Dauerauftrag Miete Oktober an «PERSON|Sabine Engel» IBAN «IBAN_CODE|" +
                  IBAN_ENGEL + "»", "-980,00"],
                 ["02.10.", "02.10.", "Lastschrift «OPTIONAL|Stadtwerke Essen AG» Abschlag Strom Kd-Nr. "
                  "«KENNNUMMER|300-4471-882»", "-96,00"],
                 ["05.10.", "05.10.", "Kartenzahlung «OPTIONAL|REWE Markt GmbH» Essen-Rüttenscheid", "-63,41"],
                 ["15.10.", "15.10.", "Lastschrift Allianz Lebensversicherungs-AG Vertrag «KENNNUMMER|4711-3392-01» "
                  "Mandatsref. «OPTIONAL|MR-2019-0044712»", "-112,50"],
                 ["28.10.", "28.10.", "Gutschrift Lohn/Gehalt «ORGANIZATION|Ingenieurbüro Fuchs & Lange GbR» "
                  "Okt. 2026", "3.188,40"],
                 ["29.10.", "29.10.", "Überweisung an «PERSON|Lukas Wolf» Taschengeld", "-150,00"],
                 ["30.10.", "30.10.", "Entgelt Kontoführung", "-6,90"]]),
    ("p", "Kontostand neu 31.10.2026: 3.521,77 Haben. Dispositionskredit: 2.000,00 EUR."),
]

L3 = [
    ("p", "«ORGANIZATION|Sanitär Hoffmann GmbH & Co. KG» · Meisterbetrieb\n«ADRESSE|Gerlingstraße 33» · "
          "«PLZ_ORT|45127 Essen» · Tel. «TELEFON|0201 236611» · «EMAIL_ADDRESS|info@sanitaer-hoffmann.example»"),
    ("p", "Frau\n«PERSON|Monika Klein»\n«ADRESSE|Zweigertstraße 8»\n«PLZ_ORT|45130 Essen»"),
    ("tabelle", [["Rechnung Nr.", "Kundennummer", "Datum", "Leistungszeitraum"],
                 ["«OPTIONAL|RE-2026-1187»", "«KENNNUMMER|K-20419»", "02.11.2026", "27.10. – 28.10.2026"]]),
    ("h", "Rechnung"),
    ("p", "Austausch Heizkörperventile und Spülkasten, Objekt: «ADRESSE|Zweigertstraße 8», Erdgeschoss rechts"),
    ("tabelle", [["Pos.", "Bezeichnung", "Menge", "Einzelpreis", "Gesamt"],
                 ["1", "Arbeitszeit Monteur (Herr «PERSON|Yılmaz»)", "6,5 Std.", "68,00", "442,00"],
                 ["2", "Anfahrtspauschale", "2", "39,00", "78,00"],
                 ["3", "Thermostatkopf Danfoss RA 2000", "4", "24,90", "99,60"],
                 ["4", "Kugelhahn 1/2 Zoll", "2", "12,40", "24,80"],
                 ["5", "Unterputz-Spülkasten Geberit Sigma 01", "1", "189,00", "189,00"],
                 ["", "Nettobetrag", "", "", "833,40"], ["", "zzgl. 19 % MwSt.", "", "", "158,35"],
                 ["", "Rechnungsbetrag", "", "", "991,75"]]),
    ("p", "Zahlbar innerhalb von 14 Tagen ohne Abzug auf IBAN «IBAN_CODE|" + IBAN_HOFFMANN + "» "
          "(Commerzbank Essen)."),
    ("klein", "Geschäftsführer: «PERSON|Uwe Hoffmann» · Amtsgericht Essen «AKTENZEICHEN|HRA 9921» · "
              "USt-IdNr. «DE_VAT_ID|" + ust_id("31277804") + "» · Steuernummer «STEUERNUMMER|112/5741/0386»"),
]

L4 = [
    ("h", "Betriebskostenabrechnung 2025"),
    ("tabelle", [["Vermieter", "«ORGANIZATION|Hausverwaltung Sommer & Lange GbR»"],
                 ["Mieter", "Familie «PERSON|Kaiser»"],
                 ["Objekt", "«ADRESSE|Holsterhauser Straße 31», «PLZ_ORT|45147 Essen»"],
                 ["Wohnung", "«OPTIONAL|3. OG links, Nr. 7»"],
                 ["Abrechnungszeitraum", "01.01.2025 – 31.12.2025"]]),
    ("tabelle", [["Kostenart", "Gesamtkosten", "Umlageschlüssel", "Ihr Anteil"],
                 ["Grundsteuer", "2.140,00", "Wohnfläche 74/612", "258,76"],
                 ["Wasser/Abwasser", "3.880,50", "Verbrauch", "512,20"],
                 ["Müllabfuhr", "1.611,20", "Personen 3/21", "230,17"],
                 ["Hausmeister", "4.200,00", "Wohnfläche 74/612", "507,84"],
                 ["Gartenpflege", "980,00", "Wohnfläche 74/612", "118,50"],
                 ["Allgemeinstrom", "622,40", "Wohnfläche 74/612", "75,26"],
                 ["Schornsteinfeger", "310,00", "Einheiten 1/8", "38,75"],
                 ["Gebäudeversicherung", "2.455,00", "Wohnfläche 74/612", "296,85"],
                 ["Summe Betriebskosten", "", "", "2.038,33"],
                 ["Vorauszahlungen", "", "", "1.920,00"],
                 ["Nachzahlung", "", "", "118,33"]]),
    ("p", "Hausmeister: Herr «PERSON|Dieter Krause», Tel. «TELEFON|0201 4410982»"),
    ("p", "Bitte überweisen Sie die Nachzahlung bis 15.12.2026 auf IBAN «IBAN_CODE|" + IBAN_KLEIN + "»."),
]

# ================================================================== Familie 4: Arztbriefe, Gutachten
KV_FUCHS = kvnr("F", "70381552")
A1 = [
    ("p", "Evangelisches Krankenhaus Mülheim an der Ruhr · Klinik für Gastroenterologie\n"
          "Chefarzt Prof. Dr. med. «PERSON|Rainer Hollmann»"),
    ("p", "Frau Dr. med. «PERSON|Ulrike Hahn»\nFachärztin für Allgemeinmedizin\n«ADRESSE|Leineweberstraße 22»\n"
          "«PLZ_ORT|45468 Mülheim an der Ruhr»"),
    ("p", "Mülheim, 30.10.2026"),
    ("h", "Entlassungsbericht"),
    ("p", "Patient: Herr «PERSON|Werner Fuchs», geb. «DATUM|14.03.1958», wohnhaft «ADRESSE|Mellinghofer Straße 64», "
          "«PLZ_ORT|45473 Mülheim an der Ruhr»\nVersichertennr.: «DE_HEALTH_INSURANCE|" + KV_FUCHS + "»   "
          "Fallnummer: «KENNNUMMER|2026-118044»\nstationär vom 21.10.2026 bis 30.10.2026, Station 4B"),
    ("p", "Diagnosen:\n- Morbus Crohn mit Ileitis terminalis, akuter Schub (K50.0)\n"
          "- Hashimoto-Thyreoiditis, substituiert (E06.3)\n- Z. n. Appendektomie 1994\n"
          "- Arterielle Hypertonie (I10.90)"),
    ("p", "Anamnese: Herr «PERSON|Fuchs» stellte sich mit seit zehn Tagen bestehenden Diarrhöen und Schmerzen im "
          "rechten Unterbauch vor. Die Ehefrau «PERSON|Gisela Fuchs» berichtet über Gewichtsverlust von 4 kg."),
    ("p", "Befunde: CRP 48 mg/l, Leukozyten 11,2 /nl, Hb 12,1 g/dl. Calprotectin deutlich erhöht. "
          "Ileokoloskopie (Dr. «PERSON|Vogel»): aphthöse Läsionen im terminalen Ileum. MRT-Sellink: Wandverdickung "
          "über 15 cm. Murphy-Zeichen negativ, Lasègue negativ."),
    ("tabelle", [["Medikation bei Entlassung", "Dosierung"],
                 ["Prednisolon 40 mg", "1-0-0, wöchentlich um 5 mg reduzieren"],
                 ["Mesalazin 1 g", "2-0-2"], ["L-Thyroxin 75 µg", "1-0-0"],
                 ["Pantoprazol 40 mg", "1-0-0"], ["Ramipril 5 mg", "1-0-0"]]),
    ("p", "Wir bitten um Kontrolle der Entzündungswerte in zwei Wochen. Wiedervorstellung in unserer "
          "CED-Ambulanz bei Dr. «PERSON|Katrin Vogel» am 26.11.2026."),
    ("p", "Mit freundlichen kollegialen Grüßen\nProf. Dr. med. «PERSON|R. Hollmann»   Dr. med. «PERSON|K. Vogel»   "
          "«PERSON|Jonas Brenner», Assistenzarzt"),
]

A2 = [
    ("p", "«ORGANIZATION|Kfz-Sachverständigenbüro Brandt GmbH» · «ADRESSE|Bredeneyer Straße 101» · "
          "«PLZ_ORT|45133 Essen» · Tel. «TELEFON|0201 8421770»"),
    ("h", "Gutachten Nr. «OPTIONAL|G-26-08-1442» – Haftpflichtschaden"),
    ("tabelle", [["Auftraggeber", "Herr «PERSON|Andreas Fischer», «ADRESSE|Frohnhauser Straße 212», «PLZ_ORT|45144 Essen»"],
                 ["Anspruchsgegner", "Allianz Versicherungs-AG, Schaden-Nr. «VERSICHERUNGSNR|KH-2026-0815-4471»"],
                 ["Fahrzeug", "Skoda Octavia Combi 2.0 TDI"],
                 ["Amtl. Kennzeichen", "«KFZ|E-AF 2187»"],
                 ["FIN", "«FIN|TMBJR7NE3L0233871»"],
                 ["Erstzulassung", "14.05.2020"], ["Laufleistung", "68.412 km"],
                 ["Besichtigung", "25.08.2026 in der Werkstatt «ORGANIZATION|Autohaus Rehbein & Söhne»"]], False),
    ("p", "Schadenbeschreibung: Anstoß vorne links, Stoßfänger, Kotflügel und Scheinwerfer links beschädigt, "
          "Radlauf verformt. Vorschäden: keine erkennbar."),
    ("tabelle", [["Kalkulation", "Betrag"],
                 ["Reparaturkosten netto", "3.912,37 EUR"], ["Wertminderung (merkantiler Minderwert)", "450,00 EUR"],
                 ["Wiederbeschaffungswert", "18.900,00 EUR"], ["Restwert", "11.200,00 EUR"],
                 ["Reparaturdauer", "5 Arbeitstage"], ["Nutzungsausfall Gruppe D", "47,00 EUR/Tag"]]),
    ("p", "Das Gutachten wurde unparteiisch und nach bestem Wissen erstellt.\n"
          "Essen, 28.08.2026\nDipl.-Ing. «PERSON|Holger Brandt», öffentlich bestellter und vereidigter "
          "Sachverständiger"),
]

A3 = [
    ("h", "Arbeitsunfähigkeitsbescheinigung"),
    ("tabelle", [["Krankenkasse bzw. Kostenträger", "AOK Rheinland/Hamburg"],
                 ["Name, Vorname des Versicherten", "«PERSON|Engel», «PERSON|Sabine»"],
                 ["geb. am", "«DATUM|17.02.1981»"],
                 ["Kostenträgerkennung", "«OPTIONAL|104212505»"],
                 ["Versicherten-Nr.", "«DE_HEALTH_INSURANCE|" + kvnr("E", "44120837") + "»"],
                 ["Status", "1000000"],
                 ["Betriebsstätten-Nr.", "«DE_BSNR|381144500»"],
                 ["Arzt-Nr.", "«DE_LANR|" + lanr("771203", "01") + "»"],
                 ["Datum", "28.10.2026"]], False),
    ("tabelle", [["Erstbescheinigung", "arbeitsunfähig seit", "voraussichtlich bis", "festgestellt am"],
                 ["X", "28.10.2026", "06.11.2026", "28.10.2026"]]),
    ("p", "AU-begründende Diagnose(n) (ICD-10): M54.5 G (Kreuzschmerz), F43.2 G (Anpassungsstörung)"),
    ("p", "Praxis Dr. med. «PERSON|Christoph Lange» · Facharzt für Innere Medizin · «OPTIONAL|Rüttenscheider "
          "Straße 66, 45130 Essen» · Tel. «OPTIONAL|0201 779910»"),
]

A4 = [
    ("h", "Familienpsychologisches Gutachten"),
    ("p", "im Verfahren «AKTENZEICHEN|3 F 211/26» beim Amtsgericht Mülheim an der Ruhr – Familiengericht –\n"
          "betreffend das Kind «PERSON|Mia Schneider», geb. «DATUM|11.05.2017»"),
    ("p", "Beteiligte: Kindesmutter «PERSON|Sandra Schneider», «ADRESSE|Eppinghofer Straße 141», "
          "«PLZ_ORT|45468 Mülheim an der Ruhr»; Kindesvater «PERSON|Marco Bauer», «ADRESSE|Kölner Straße 52», "
          "«PLZ_ORT|47053 Duisburg»; Verfahrensbeiständin «PERSON|Birgit Engel»"),
    ("p", "Fragestellung: Welche Umgangsregelung entspricht dem Kindeswohl am besten?"),
    ("p", "Untersuchungen: drei Explorationen der Mutter, zwei des Vaters, Interaktionsbeobachtungen, Gespräch mit "
          "der Klassenlehrerin Frau «PERSON|Neumann» der «OPTIONAL|Grundschule am Dichterviertel». Eingesetzt wurden "
          "der Familien-System-Test (FAST), die Child Behavior Checklist (CBCL) und der Satzergänzungstest."),
    ("p", "Befund: Mia zeigt eine sichere Bindung zur Mutter und eine ambivalente Bindung zum Vater (Bindungstheorie "
          "nach «OPTIONAL|Bowlby»). Hinweise auf ein Asperger-Syndrom ergaben sich nicht. Der Vater lebt mit seiner "
          "neuen Partnerin «PERSON|Jasmin Hahn» zusammen; Mia beschreibt sie als „nett, aber streng“. Die Großmutter "
          "mütterlicherseits, Frau «PERSON|Elke Schneider», betreut Mia an zwei Nachmittagen."),
    ("p", "Empfehlung: Umgang des Vaters an jedem zweiten Wochenende von Freitag 15 Uhr bis Sonntag 18 Uhr sowie "
          "hälftige Ferienregelung. Übergaben über die Großmutter."),
    ("p", "Mülheim, 02.11.2026\nDipl.-Psych. «PERSON|Dr. Ralf Overbeck», Fachpsychologe für Rechtspsychologie"),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    random.seed(7)
    print("Dokumente:")
    als_docx("S1_Klage_Verkehrsunfall_Fischer.docx", "schriftsatz", S1)
    s2 = als_pdf("S2_Schreiben_Gegenseite.pdf", "schriftsatz", S2)
    (OUT / "S3_EMail_Kuendigung_Engel.txt").write_text(render(S3[0][1]), encoding="utf-8")
    registrieren("S3_EMail_Kuendigung_Engel.txt", "schriftsatz", render(S3[0][1]).encode("utf-8"), S3)
    als_docx("S4_Vollmacht_Engel.docx", "schriftsatz", S4)
    b1 = als_pdf("B1_Bussgeldbescheid_Bauer.pdf", "bescheid_formular", B1)
    als_docx("B2_Schadenmeldung_Schneider.docx", "bescheid_formular", B2)
    als_pdf("B3_Unfallbericht_Koch_Wolf.pdf", "bescheid_formular", B3)
    als_pdf("B4_Rentenbescheid_Hoffmann.pdf", "bescheid_formular", B4)
    l1 = als_pdf("L1_Lohnabrechnung_Becker.pdf", "lohn_konto_rechnung", L1)
    l2 = als_pdf("L2_Kontoauszug_Wolf.pdf", "lohn_konto_rechnung", L2)
    als_docx("L3_Rechnung_Sanitaer.docx", "lohn_konto_rechnung", L3)
    als_xlsx("L4_Betriebskosten_Kaiser.xlsx", "lohn_konto_rechnung", L4)
    als_docx("A1_Arztbrief_Fuchs.docx", "arzt_gutachten", A1)
    a2 = als_pdf("A2_Kfz_Gutachten_Fischer.pdf", "arzt_gutachten", A2)
    a3 = als_pdf("A3_AU_Bescheinigung_Engel.pdf", "arzt_gutachten", A3)
    als_docx("A4_Familiengutachten_Schneider.docx", "arzt_gutachten", A4)
    print("Scans (Texterkennung läuft, ca. 1 min):")
    als_scan("L1_Lohnabrechnung_Becker_scan.pdf", l1, L1, textebene=True, drehung=0.6, seed=1)
    als_scan("L2_Kontoauszug_Wolf_scan.pdf", l2, L2, textebene=False, drehung=-0.4, seed=2)
    als_scan("B1_Bussgeldbescheid_Bauer_scan.pdf", b1, B1, textebene=False, drehung=0.8, seed=3)
    als_scan("A3_AU_Bescheinigung_Engel_scan.pdf", a3, A3, textebene=True, drehung=-0.7, seed=4)
    als_scan("A2_Kfz_Gutachten_Fischer_scan.pdf", a2, A2, textebene=False, drehung=0.3, seed=5)
    als_scan("S2_Schreiben_Gegenseite_scan.pdf", s2, S2, textebene=True, drehung=-0.5, seed=6)
    with open(OUT / "referenz.jsonl", "w", encoding="utf-8") as fh:
        for f in faelle:
            fh.write(json.dumps(f, ensure_ascii=False) + "\n")
    print(f"{len(faelle)} Fälle, {sum(len(f['spans']) for f in faelle)} markierte Stellen → referenz.jsonl")


if __name__ == "__main__":
    main()
