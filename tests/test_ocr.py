"""OCR: gescannte PDF-Seiten lesen und schwärzen (RapidOCR, offline).

testdaten/scan/Fall4_scan.pdf ist Fall 4 als reines Bild (200 dpi, keine Textebene).
"""
import sys
from pathlib import Path

import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from anonymizer import files as fio
from anonymizer.ocr import erkenne_seite, finde_treffer, ist_scan

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "testdaten/scan/Fall4_scan.pdf"
TEXT_PDF = ROOT / "testdaten/kanzlei/Fall4_Verkehrsrecht_Einspruch_Bussgeld_Engel.pdf"
PAIRS = [("Dr. Claudia Engel", "[PERSON_1]"), ("Claudia Engel", "[PERSON_1]"), ("Engel", "[PERSON_1]"),
         ("Markus Engel", "[PERSON_2]"), ("J010B7XY351", "[FUEHRERSCHEIN_1]"), ("E-CE 511", "[KFZ_1]"),
         ("Moltkestraße 15", "[ADRESSE_1]"), ("45138 Essen", "[ORT_1]"), ("05.11.1979", "[DATUM_1]"),
         ("7.1-552318/26", "[AZ_1]")]


@pytest.fixture(scope="module")
def scan_pdf():
    if not SCAN.exists():
        SCAN.parent.mkdir(parents=True, exist_ok=True)
        src = pymupdf.open(TEXT_PDF)
        pix = src[0].get_pixmap(dpi=200)
        out = pymupdf.open()
        page = out.new_page(width=src[0].rect.width, height=src[0].rect.height)
        page.insert_image(page.rect, pixmap=pix)
        out.save(SCAN, garbage=4, deflate=True)
    return SCAN.read_bytes()


def test_ist_scan(scan_pdf):
    assert ist_scan(pymupdf.open(stream=scan_pdf, filetype="pdf")[0])
    assert not ist_scan(pymupdf.open(TEXT_PDF)[0])


def test_ocr_liest_deutschen_text(scan_pdf):
    text, info = fio.read_document("Fall4_scan.pdf", scan_pdf)
    assert info == {"seiten": 1, "ocr_seiten": 1}
    for muss in ("Bußgeldbescheid", "Dr. Claudia Engel", "J010B7XY351", "E-CE 511", "Moltkestraße 15", "45138 Essen",
                 "05.11.1979", "7.1-552318/26", "Rechtsanwälte"):
        assert muss in text, muss


def test_wortboxen_treffer(scan_pdf):
    seite = erkenne_seite(pymupdf.open(stream=scan_pdf, filetype="pdf")[0])
    hits = finde_treffer(seite, PAIRS)
    phs = {ph for ph, _ in hits}
    assert {"[PERSON_1]", "[FUEHRERSCHEIN_1]", "[KFZ_1]", "[ADRESSE_1]", "[ORT_1]", "[DATUM_1]", "[AZ_1]"} <= phs
    for _, (x0, y0, x1, y1) in hits:
        assert 0 <= x0 < x1 <= 600 and 0 <= y0 < y1 <= 850


def test_scan_schwaerzen_und_gegenpruefung(scan_pdf):
    out = fio.write_pdf(scan_pdf, PAIRS)
    doc = pymupdf.open(stream=out, filetype="pdf")
    assert doc.metadata.get("author", "") == ""
    textebene = doc[0].get_text()
    for ph in ("[PERSON_1]", "[FUEHRERSCHEIN_1]", "[KFZ_1]", "[ADRESSE_1]", "[AZ_1]"):
        assert ph in textebene, ph
    # Was das Auge sieht: erneut per OCR lesen – kein Original mehr, Platzhalter erkennbar
    seite = erkenne_seite(doc[0])
    low = seite.text.lower()
    for orig, _ in PAIRS:
        assert orig.lower() not in low, orig
    assert "fuehrerschein_1" in low.replace("[", "").replace("]", "")
    assert fio.verify_pdf(out, [o for o, _ in PAIRS]) == []
