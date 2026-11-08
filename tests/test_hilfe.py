"""Wächter für die Regel „Hilfe und Tour wachsen mit“ (docs/entwicklung/hilfe-mitpflegen.md), ohne Browser:
- jedes Ziel im Drehbuch der Einführung ist ein data-tour-Anker der Oberfläche,
- jeder Anker der Oberfläche steht im Drehbuch oder im Hilfe-Inventar als „ohne Tour“,
- jeder benutzte Hilfetext existiert, und jeder Hilfetext wird benutzt,
- gibt es eine Release-Notiz zur aktuellen Version, hat das Drehbuch Schritte für die Tour „Neu in …“.
Den Durchlauf im Browser prüft LokanonTour.selbsttest() (siehe docs/entwicklung/hilfe-mitpflegen.md)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ui"
APP = (UI / "app.js").read_text(encoding="utf-8") + (UI / "index.html").read_text(encoding="utf-8")
DREHBUCH = (UI / "einfuehrung" / "drehbuch.js").read_text(encoding="utf-8")
HILFE = (UI / "einfuehrung" / "hilfetexte.js").read_text(encoding="utf-8")
INVENTAR = (ROOT / "docs" / "hilfe-inventar.md").read_text(encoding="utf-8")


def anker_der_oberflaeche() -> set[str]:
    anker = set(re.findall(r'data-tour="([a-z][a-z\-]*)"', APP))
    anker |= set(re.findall(r'\btour: "([a-z][a-z\-]*)"', APP))             # Menüeinträge, Dialoge
    anker |= set(re.findall(r'leisteZeigen\([^;]*?, "([a-z][a-z\-]*)"\)', APP))  # Markierfenster
    anker |= {"nav-" + n for n in re.findall(r'navi\("([a-z]+)"', APP)}     # Navigation
    return anker


def ziele_im_drehbuch() -> set[str]:
    """Ziele der Schritte und Anker, die „Zeig es mir“ bedient ([data-tour="…"] in den Selektoren)."""
    return set(re.findall(r'\bziel: "([a-z][a-z\-]*)"', DREHBUCH)) | set(re.findall(r'data-tour="([a-z][a-z\-]*)"', DREHBUCH))


def test_drehbuch_ziele_existieren():
    fehlt = ziele_im_drehbuch() - anker_der_oberflaeche()
    assert not fehlt, f"Ziele ohne data-tour-Anker in ui/app.js: {sorted(fehlt)}"


def test_anker_sind_im_drehbuch_oder_inventar():
    ohne = set(re.findall(r"^\| `([a-z][a-z\-]*)` \|.*\| ohne Tour", INVENTAR, flags=re.M))
    rest = anker_der_oberflaeche() - ziele_im_drehbuch() - ohne
    assert not rest, f"Anker weder im Drehbuch noch im Inventar (docs/hilfe-inventar.md) als „ohne Tour“: {sorted(rest)}"


def test_hilfetexte_benutzt_und_vorhanden():
    vorhanden = set(re.findall(r"^  ([a-z_]+): \{", HILFE, flags=re.M))
    benutzt = set(re.findall(r'hilfeKnopf\("([a-z_]+)"', APP)) | set(re.findall(r'data-hilfe="([a-z_]+)"', APP))
    benutzt |= set(re.findall(r'\bhilfe: "([a-z_]+)"', DREHBUCH))
    assert benutzt <= vorhanden, f"Hilfetexte fehlen: {sorted(benutzt - vorhanden)}"
    assert vorhanden <= benutzt, f"Hilfetexte werden nirgends benutzt: {sorted(vorhanden - benutzt)}"
    kapitel = set(re.findall(r'\{ id: "([a-z]+)", nr:', DREHBUCH))
    verweise = set(re.findall(r'kapitel: "([a-z]+)"', HILFE))
    assert verweise <= kapitel, f"Hilfetexte verweisen auf unbekannte Kapitel: {sorted(verweise - kapitel)}"


def test_neu_in_version_hat_tourschritte():
    version = (ROOT / "build" / "VERSION").read_text(encoding="utf-8").strip()
    if (ROOT / "docs" / "pilot" / f"Neu-in-{version}.md").exists():
        assert f'seit: "{version}"' in DREHBUCH, f"Release-Notiz {version} ohne Tourschritte mit seit: \"{version}\""


def test_anleitung_verweist_auf_kapitel():
    anleitung = (ROOT / "static" / "anleitung" / "index.html").read_text(encoding="utf-8")
    kapitel = set(re.findall(r'\{ id: "([a-z]+)", nr:', DREHBUCH))
    links = set(re.findall(r'#einfuehrung/([a-z]+)', anleitung))
    assert links and links <= kapitel, f"Anleitung verweist auf unbekannte Kapitel: {sorted(links - kapitel)}"
