"""Beispiel für die Einführung im Programm (Anforderung docs/anforderungen/lernen-und-loeschfristen.md, Abschnitt 9).

Alle Namen, Adressen und Nummern sind erfunden. Die Treffer sind vorberechnet: Die Einführung läuft damit sofort,
auch während die Sprachmodelle noch laden, und sieht bei jedem gleich aus. Bewusst eingebaut:
- ein Fehlalarm zum Abwählen („Morbus Crohn“ als Person),
- ein übersehener Begriff zum Selbstmarkieren („Falkenhorst“, in beiden Dateien),
- eine Bezeichnung mit Wert („Mandantennr.: 48213“) für das Lernen einer Regel,
- ein Aktenzeichen, das als Fall vorgeschlagen wird.
"""
from __future__ import annotations

from datetime import timedelta

from server import gedaechtnis as gm

SCHREIBEN = """Lehmkuhl & Partner Rechtsanwälte · Dr. Annette Lehmkuhl
An das Amtsgericht Mülheim an der Ruhr
Aktenzeichen: 14 C 512/26
Mandantennr.: 48213

Klageerwiderung

In dem Rechtsstreit
Sabine Winter, Eppinghofer Straße 47, 45468 Mülheim an der Ruhr – Klägerin –
gegen
Thomas Brandt, Duisburger Straße 112, 45479 Mülheim an der Ruhr – Beklagter –

zeigen wir an, dass wir die Klägerin vertreten. Frau Winter parkte am 12. März 2026 ihr Fahrzeug mit dem Kennzeichen MH-SW 214 ordnungsgemäß vor dem Haus. Herr Brandt fuhr beim Rangieren gegen die Fahrerseite. Der Zeuge Jonas Keller hat den Vorgang beobachtet.

Frau Winter leidet seit Jahren an Morbus Crohn und war deshalb auf das Fahrzeug angewiesen. Das Projekt Falkenhorst, für das sie als Bauleiterin tätig ist, verzögerte sich um drei Wochen.

Die Reparaturkosten von 3.480,00 Euro sind auf das Konto der Klägerin, IBAN DE44 3625 0000 0175 3381 20, zu überweisen. Frau Winter ist unter 0208 3391574 erreichbar.

Mit freundlichen Grüßen
Dr. Annette Lehmkuhl
Rechtsanwältin"""

MAIL = """Hallo Frau Lehmkuhl,

anbei die Rechnung der Werkstatt. Beim Projekt Falkenhorst hat sich durch den Unfall alles verschoben.

Viele Grüße
Sabine Winter"""

_TREFFER = [
    {"text": "Sabine Winter", "entity": "PERSON", "quelle": "modell", "score": 0.95},
    {"text": "Winter", "entity": "PERSON", "quelle": "wiederholung", "score": 0.9},
    {"text": "Thomas Brandt", "entity": "PERSON", "quelle": "modell", "score": 0.95},
    {"text": "Brandt", "entity": "PERSON", "quelle": "wiederholung", "score": 0.9},
    {"text": "Jonas Keller", "entity": "PERSON", "quelle": "heuristik", "score": 0.85, "grund": "nach „Zeuge“"},
    {"text": "Morbus Crohn", "entity": "PERSON", "quelle": "modell", "score": 0.52},
    {"text": "Eppinghofer Straße 47, 45468 Mülheim an der Ruhr", "entity": "ADRESSE", "quelle": "regel", "score": 0.9},
    {"text": "Duisburger Straße 112, 45479 Mülheim an der Ruhr", "entity": "ADRESSE", "quelle": "regel", "score": 0.9},
    {"text": "14 C 512/26", "entity": "AKTENZEICHEN", "quelle": "regel", "score": 0.9},
    {"text": "MH-SW 214", "entity": "DE_KFZ", "quelle": "regel", "score": 0.9},
    {"text": "DE44 3625 0000 0175 3381 20", "entity": "IBAN_CODE", "quelle": "regel", "score": 1.0,
     "grund": "Muster IBAN, Prüfziffer stimmt"},
    {"text": "0208 3391574", "entity": "TELEFON", "quelle": "regel", "score": 0.9},
]

BEISPIEL = [{"name": "Klageerwiderung Winter.txt", "text": SCHREIBEN, "treffer": _TREFFER},
            {"name": "Mail Mandantin.txt", "text": MAIL, "treffer": _TREFFER}]

ALLOW = ["Lehmkuhl & Partner", "Annette Lehmkuhl", "Lehmkuhl"]


def beispielfaelle(gd: gm.Gedaechtnis, cfg: dict) -> None:
    """Drei erfundene Fälle für das Kapitel „Gespeicherte Angaben“: ein laufender, einer kurz vor dem Löschen,
    einer abgeschlossen."""
    gd.merken("3 O 1120/26", [{"text": "Martin Ochs", "art": "PERSON"}, {"text": "Ochs Haustechnik GmbH",
                                                                         "art": "ORGANIZATION"}])
    gd.merken("9 O 88/25", [{"text": "Lena Brinkhoff", "art": "PERSON"}, {"text": "Hof Brinkhoff", "art": "ADRESSE"}])
    gd.merken("2 O 77/25", [{"text": "Petra Rosen", "art": "PERSON"}])
    d = gd.laden()
    fr = gm.fristen(cfg)
    for f in d["faelle"].values():
        if f["name"] == "9 O 88/25":  # Frist endet in 20 Tagen
            ende = gm.heute() + timedelta(days=20)
            f["zuletzt"] = gm._plus_monate(ende, -int(fr["personen_monate"])).isoformat()
            f["angelegt"] = f["zuletzt"]
        if f["name"] == "2 O 77/25":
            f["status"], f["abgeschlossen_am"] = "abgeschlossen", (gm.heute() - timedelta(days=30)).isoformat()
    gd.speichern(d)
