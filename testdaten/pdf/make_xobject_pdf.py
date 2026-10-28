"""Erzeugt testdaten/pdf/xobject_test.pdf: Seite 1 trägt den Text direkt, Seite 2 zeigt
Seite 1 als Form-XObject (show_pdf_page) und hat zusätzlich eine Zeile direkten Text,
ein Bild unter einem Namen, ein Formularfeld mit Namen als Wert, ein Lesezeichen,
einen Link, versteckten Text und Metadaten mit Namen. Aufruf mit dem venv-Interpreter."""
from pathlib import Path

import pymupdf

HERE = Path(__file__).parent

TEXT = (
    "Mandantin Dr. Claudia Engel wohnt in der Moltkestraße 15 in 45138 Essen. "
    "Ihr Ehemann Markus Engel fährt den Wagen mit dem Kennzeichen E-CE 511. "
    "Aktenzeichen 7.1-552318/26."
)


def build() -> Path:
    src = pymupdf.open()
    p = src.new_page()
    p.insert_textbox(pymupdf.Rect(50, 50, 420, 200), TEXT, fontname="helv", fontsize=11)
    p.insert_text((50, 250), "Chefärztin der Kinderklinik am Elisabeth-Krankenhaus",
                  fontname="helv", fontsize=9)

    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_textbox(pymupdf.Rect(50, 50, 420, 200), TEXT, fontname="helv", fontsize=11)
    p2 = doc.new_page()
    p2.show_pdf_page(p2.rect, src, 0)                       # Form-XObject
    # Direkter Text auf Seite 2 absichtlich in "tiro" (Times): "helv" gibt es auf dieser
    # Seite nur im XObject. PyMuPDF würde bei insert_text(fontname="helv") die XObject-
    # Schrift finden und keine Seitenressource anlegen (ungültiges PDF, Ersatzschrift).
    p2.insert_text((50, 400), "Direkt: Dr. Claudia Engel", fontname="tiro", fontsize=11)
    p2.insert_text((50, 430), "Versteckt: Markus Engel", fontname="tiro", fontsize=11,
                   render_mode=3)                            # unsichtbarer Text
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 60, 20), 0)
    pix.clear_with(90)
    p2.insert_image(pymupdf.Rect(45, 390, 180, 410), pixmap=pix)   # Bild unter dem Namen
    p2.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(50, 390, 200, 410),
                    "uri": "https://example.invalid/Claudia-Engel"})
    w = pymupdf.Widget()
    w.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    w.field_name = "mandant"
    w.field_value = "Dr. Claudia Engel"
    w.rect = pymupdf.Rect(50, 500, 300, 520)
    p2.add_widget(w)
    p2.add_text_annot((400, 500), "Notiz: Markus Engel")
    doc.set_toc([[1, "Akte Dr. Claudia Engel", 1]])
    doc.set_metadata({"title": "Akte Engel", "author": "Dr. Annette Lehmkuhl",
                      "subject": "Markus Engel", "keywords": "Engel"})
    doc.set_xml_metadata("<x:xmpmeta xmlns:x='adobe:ns:meta/'><dc:creator>Dr. Annette Lehmkuhl"
                         "</dc:creator></x:xmpmeta>")
    doc.embfile_add("anhang.txt", b"Anhang: Dr. Claudia Engel", filename="anhang.txt")
    out = HERE / "xobject_test.pdf"
    doc.save(out, garbage=0, deflate=False)
    return out


if __name__ == "__main__":
    print(build())
