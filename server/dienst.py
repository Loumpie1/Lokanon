"""Sitzungsdienst: Dateien ablegen, erkennen, Identitäten prüfen, anonymisieren. Die Oberfläche spricht nur mit
diesem Dienst. Eine Sitzung ist ein Durchlauf: Dateien oder ein Ordner, eine Prüfung, eine Ausgabe.

Erweiterte Funktionen (Rückübersetzung mit Schlüssel, KI-Anweisung, Vorgangsordner mit Prüfbericht) sind in den
Einstellungen abschaltbar und greifen nur, wenn sie eingeschaltet sind.
"""
from __future__ import annotations

import html
import io
import threading
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from anonymizer import ausgabe as aus
from anonymizer import files as fio
from anonymizer.engine import (LABELS, Finding, anzeige_platzhalter, build_analyzer, deanonymize, detect,
                               platzhalter_schluessel, propagate_vorgang, pseudonymize, replacement_pairs)
from anonymizer.vault import decrypt_mapping, encrypt_mapping
from anonymizer.vorgang import (LESBARE_TYPEN, Vorgang, dateien_im_ordner, mapping_aus_schluessel, markiert_html,
                                pruefbericht_html, sicherer_name)
from server import einstellungen as est
from server import markieren as mk
from server import testfaelle as tf
from server.protokoll import Protokoll

APP_DIR = Path(__file__).resolve().parents[1]
ANWEISUNG_PATH = APP_DIR / "ki-anweisung" / "projekt-anweisung.md"
SKILL_DIR = APP_DIR / "ki-anweisung" / "lokanon-pseudonyme"

# Anzeige-Gruppen der Prüfliste (Reihenfolge = Anzeige), in Alltagssprache
GRUPPEN_ANZEIGE = {
    "Personen": ["PERSON"],
    "Firmen und Einrichtungen": ["ORGANIZATION"],
    "Adressen und Kontakt": ["ADRESSE", "PLZ_ORT", "LOCATION", "EMAIL_ADDRESS", "TELEFON", "URL", "IP_ADDRESS"],
    "Nummern und Kennzeichen": ["AKTENZEICHEN", "DIKTATZEICHEN", "GRUNDBUCH", "VERSICHERUNGSNR", "DE_HANDELSREGISTER",
                                "IBAN_CODE", "KONTONUMMER", "CREDIT_CARD", "DE_TAX_ID", "DE_TAX_NUMBER", "DE_VAT_ID",
                                "DE_ID_CARD", "DE_PASSPORT", "DE_FUEHRERSCHEIN", "FUEHRERSCHEIN", "DE_SOCIAL_SECURITY",
                                "DE_HEALTH_INSURANCE", "DE_LANR", "DE_BSNR", "PERSONALNR", "KENNNUMMER", "DE_KFZ", "KFZ",
                                "FIN"],
    "Daten und Sonstiges": ["DATUM", "BERUF", "DIAGNOSE", "EIGENE_BEGRIFFE", "MANUELL"],
}
QUELLE_TEXT = {"modell": "Sprachmodell", "regel": "Muster", "heuristik": "Anrede oder Unterschrift", "feld": "Formularfeld",
               "liste": "Ihre Liste", "wiederholung": "Wiederholung", "namensteil": "Namensteil", "vorgang": "andere Datei",
               "firmenteil": "Teil eines Firmennamens", "manuell": "von Ihnen markiert"}
VORSCHLAEGE = {
    "PERSON": ["Mandant", "Mandantin", "Gegner", "Gegnerin", "Zeuge", "Zeugin", "Erblasser", "Erblasserin"],
    "ORGANIZATION": ["Gegnerfirma", "Arbeitgeber", "Versicherung", "Werkstatt", "Bank"],
    "ADRESSE": ["Anschrift Mandant", "Anschrift Gegner", "Unfallort"],
    "PLZ_ORT": ["Wohnort Mandant", "Wohnort Gegner"],
}


def gruppe_von(entity: str) -> str:
    for g, ents in GRUPPEN_ANZEIGE.items():
        if entity in ents:
            return g
    return "Daten und Sonstiges"


def sicherheit(score: float) -> str:
    return "sicher" if score >= 0.7 else "wahrscheinlich" if score >= 0.5 else "unsicher"


@dataclass
class Dokument:
    name: str
    text: str
    data: bytes | None
    pfad: str = ""                       # Originalpfad bei Ordner-Eingabe
    info: dict = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    anonym: str = ""
    platzhalter: dict[tuple[int, int], str] = field(default_factory=dict)
    schluessel: dict[int, str] = field(default_factory=dict)   # Treffer-Index -> "Person_1"


@dataclass
class Fortschritt:
    laeuft: bool = False
    schritt: str = ""
    datei: str = ""
    prozent: int = 0
    fertig: bool = False
    fehler: str = ""
    begonnen: float = 0.0


class Modelle:
    """Lädt die Sprachmodelle einmal im Hintergrund."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.analyzer = None
        self.fehler = ""
        self._thread: threading.Thread | None = None

    def starten(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._laden, daemon=True)
            self._thread.start()

    def _laden(self) -> None:
        try:
            self.analyzer = build_analyzer(self.cfg["spacy_model"], self.cfg.get("gliner_model") or None,
                                           float(self.cfg.get("gliner_threshold", 0.5)))
        except Exception as e:  # pragma: no cover
            self.fehler = f"{type(e).__name__}: {e}"

    @property
    def bereit(self) -> bool:
        return self.analyzer is not None

    def warten(self, timeout: float = 600) -> None:
        t0 = time.time()
        while not self.bereit and not self.fehler and time.time() - t0 < timeout:
            time.sleep(0.2)
        if self.fehler:
            raise RuntimeError(self.fehler)


class Sitzung:
    def __init__(self, cfg_laden, cfg_speichern, modelle: Modelle):
        self.cfg_laden = cfg_laden
        self.cfg_speichern = cfg_speichern
        self.modelle = modelle
        self.protokoll = Protokoll(est.daten_ordner)
        self.leeren()

    def leeren(self) -> dict:
        self.docs: list[Dokument] = []
        self.ordner: str = ""
        self.manual: list[str] = []
        self.disabled: set[str] = set()          # Platzhalter-Schlüssel, die stehen bleiben ("Person_2")
        self.bezeichnungen: dict[str, str] = {}  # "Person_1" -> "Mandant"
        self.aliases: dict[str, str] = {}        # "günther" -> "Cornelia Günther" (gehört zu …)
        self.getrennt: set[str] = set()          # Schreibweisen, die eine eigene Identität bleiben
        self.aus_stellen: set[tuple[int, int, int]] = set()  # einzelne Stellen, die stehen bleiben (Datei, Start, Ende)
        self.verlauf: list[tuple[str, dict]] = []  # Rückgängig-Stapel: (was, Zustand davor)
        self.mapping: dict[str, str] = {}
        self.zuordnung: dict[str, str] = {}
        self.fortschritt = Fortschritt()
        self.ergebnis: dict | None = None
        self.schluessel_pfad: str = ""
        return self.zustand()

    # ------------------------------------------------------------------ Dateien
    def datei_hinzufuegen(self, name: str, data: bytes) -> dict:
        name = Path(name).name
        if name.lower().rsplit(".", 1)[-1] not in LESBARE_TYPEN:
            raise ValueError(f"{name}: Dateityp wird nicht unterstützt (PDF, Word, Excel, Text).")
        if self.ordner:
            self.ordner = ""
            self.docs = []
        self.docs = [d for d in self.docs if d.name != name]
        self.docs.append(Dokument(name=name, text="", data=data))
        self._zuruecksetzen()
        return {"name": name, "groesse": len(data)}

    def ordner_setzen(self, pfad: str) -> dict:
        p = Path(pfad.strip())
        if not p.is_dir():
            raise ValueError("Der Ordner wurde nicht gefunden.")
        dateien = [q for q in dateien_im_ordner(p) if not _ist_ausgabe(q, self.cfg_laden().get("suffix", "_anonymisiert"))]
        if not dateien:
            raise ValueError("In diesem Ordner liegen keine Dateien, die Lokanon lesen kann (PDF, Word, Excel, Text).")
        self.ordner = str(p)
        self.docs = [Dokument(name=q.name, text="", data=None, pfad=str(q)) for q in dateien]
        self._zuruecksetzen()
        cfg = self.cfg_laden()
        zuletzt = [str(p)] + [z for z in cfg.get("zuletzt_ordner", []) if z != str(p)]
        cfg["zuletzt_ordner"] = zuletzt[:8]
        self.cfg_speichern(cfg)
        return {"ordner": self.ordner, "dateien": [{"name": d.name, "groesse": Path(d.pfad).stat().st_size} for d in self.docs]}

    def text_setzen(self, text: str) -> dict:
        if not text.strip():
            raise ValueError("Der Text ist leer.")
        name = f"Text {datetime.now():%Y-%m-%d %H-%M}.txt"
        if self.ordner:
            self.ordner, self.docs = "", []
        self.docs.append(Dokument(name=name, text=text, data=text.encode("utf-8")))
        self._zuruecksetzen()
        return {"name": name, "groesse": len(text)}

    def datei_entfernen(self, name: str) -> dict:
        self.docs = [d for d in self.docs if d.name != name]
        self._zuruecksetzen()
        return self.zustand()

    def _zuruecksetzen(self) -> None:
        self.fortschritt = Fortschritt()
        self.ergebnis = None
        self.mapping, self.zuordnung = {}, {}
        self.aus_stellen, self.verlauf = set(), []

    # ------------------------------------------------------------------ Analyse (Hintergrund mit Fortschritt)
    def analysieren(self, manual: list[str] | None = None) -> None:
        if self.fortschritt.laeuft:
            return
        if not self.docs:
            raise ValueError("Bitte zuerst Dateien ablegen oder einen Ordner wählen.")
        self.manual = [m.strip() for m in (manual or []) if m.strip()]
        self.fortschritt = Fortschritt(laeuft=True, schritt="Modelle laden", begonnen=time.time())
        self.ergebnis = None
        threading.Thread(target=self._analyse_lauf, daemon=True).start()

    def _melde(self, schritt: str, datei: str = "", prozent: int | None = None) -> None:
        self.fortschritt.schritt, self.fortschritt.datei = schritt, datei
        if prozent is not None:
            self.fortschritt.prozent = prozent

    def _analyse_lauf(self) -> None:
        prot = self.protokoll
        prot.neuer_lauf("Analyse", [d.name for d in self.docs], self.ordner)
        prot.geheimnisse([(m, "<nachgetragen>") for m in self.manual])
        try:
            cfg = self.cfg_laden()
            self.modelle.warten()
            analyzer = self.modelle.analyzer
            n = len(self.docs)
            for i, d in enumerate(self.docs):
                self._melde("Lese", d.name, int(5 + 45 * i / n))
                t0 = time.time()
                if d.data is None and d.pfad:
                    d.data = Path(d.pfad).read_bytes()
                if d.name.lower().endswith(".txt") and d.text:
                    d.info = {}
                else:
                    d.text, d.info = fio.read_document(d.name, d.data or b"")
                prot.notiere("info", f"{d.name}: gelesen, {len(d.data or b'') // 1024} KB, "
                                     f"{d.info.get('seiten', 0)} Seiten, {d.info.get('ocr_seiten', 0)} per Texterkennung, "
                                     f"{len(d.text)} Zeichen, {time.time() - t0:.1f} s")
                if not d.text.strip():
                    prot.notiere("warnung", f"{d.name}: kein Text gelesen")
            for i, d in enumerate(self.docs):
                self._melde("Erkenne Personendaten", d.name, int(50 + 45 * i / n))
                t0 = time.time()
                d.findings = detect(analyzer, d.text, cfg["entities"], float(cfg.get("threshold", 0.4)),
                                    est.erlaubt_liste(cfg), est.ersetzen_liste(cfg), self.manual,
                                    cfg.get("propagate_repeats", True), cfg.get("include_name_parts", True),
                                    cfg.get("mask_locations", False), cfg.get("keep_institutions", True),
                                    cfg.get("datum_modus", "kontext"))
                prot.notiere("info", f"{d.name}: {len(d.findings)} Treffer ({_zaehle(d.findings)}), "
                                     f"{time.time() - t0:.1f} s")
            self._melde("Gleiche Namen über alle Dateien ab", "", 96)
            neu = propagate_vorgang([d.text for d in self.docs], [d.findings for d in self.docs],
                                    est.erlaubt_liste(cfg), cfg.get("include_name_parts", True))
            for d, fs in zip(self.docs, neu):
                d.findings = fs
            self.verlauf = []
            self._pseudonymisieren()
            self._protokoll_geheimnisse()
            prot.notiere("info", f"Analyse fertig: {len(self.mapping)} Identitäten")
            self._melde("Fertig", "", 100)
            self.fortschritt.fertig = True
        except Exception as e:
            wo = f"{self.fortschritt.schritt} „{self.fortschritt.datei}“" if self.fortschritt.datei else self.fortschritt.schritt
            self._protokoll_geheimnisse()
            prot.ausnahme(f"Analyse, Schritt {wo}", e)
            self.fortschritt.fehler = f"Beim Schritt „{wo}“: {e}"
        finally:
            self.fortschritt.laeuft = False

    def _protokoll_geheimnisse(self) -> None:
        """Alle erkannten Originale (auch abgewählte) für das Protokoll durch ihren Platzhalter ersetzen."""
        paare = [(orig, f"[{ph}]") for ph, orig in self.mapping.items()]
        for d in self.docs:
            paare += [(f.text, f"[{d.schluessel.get(i) or LABELS.get(f.entity, f.entity)}]")
                      for i, f in enumerate(d.findings)]
        self.protokoll.geheimnisse(paare)

    def _pseudonymisieren(self) -> None:
        """Zwei Durchgänge: erst alle Treffer (stabile Nummern und Zuordnung), dann nur die aktiven."""
        mapping: dict[str, str] = {}
        zuordnung: dict[str, str] = {}
        for d in self.docs:
            for f in d.findings:
                f.active = True
            res = pseudonymize(d.text, d.findings, mapping, self.bezeichnungen, self.aliases, self.getrennt)
            mapping, zuordnung = res.mapping, {**zuordnung, **res.zuordnung}
        self.mapping, self.zuordnung = mapping, zuordnung
        fest = {t: mapping[ph] for t, ph in zuordnung.items() if ph in mapping}  # Entscheidung festhalten
        for di, d in enumerate(self.docs):
            d.schluessel = platzhalter_schluessel(d.findings, mapping, zuordnung)
            for i, f in enumerate(d.findings):
                f.active = d.schluessel.get(i, "") not in self.disabled and (di, f.start, f.end) not in self.aus_stellen
            res = pseudonymize(d.text, d.findings, mapping, self.bezeichnungen, fest, self.getrennt)
            d.anonym = res.anonymized
            paare = dict(replacement_pairs(d.text, d.findings, mapping, self.bezeichnungen, zuordnung))
            d.platzhalter = {(f.start, f.end): paare.get(f.text, "") for f in d.findings if f.active}

    # ------------------------------------------------------------------ Prüfen
    def identitaet(self, ph: str, aktiv: bool | None = None, bezeichnung: str | None = None,
                   gehoert_zu: str | None = None, trennen: str | None = None,
                   zuordnen: dict | None = None) -> dict:
        self._sichern("Änderung an einer Karte")
        if aktiv is not None:
            (self.disabled.discard if aktiv else self.disabled.add)(ph)
        if bezeichnung is not None:
            b = bezeichnung.strip()
            if b:
                self.bezeichnungen[ph] = b
            else:
                self.bezeichnungen.pop(ph, None)
        if gehoert_zu is not None:
            ziel = self.mapping.get(gehoert_zu)
            if ziel is None:
                raise ValueError("Die Zielperson wurde nicht gefunden.")
            for t in self._varianten(ph):
                self.aliases[t.lower()] = ziel
                self.getrennt.discard(t.lower())
            self.bezeichnungen.pop(ph, None)
        if trennen is not None:
            self.getrennt.add(trennen.lower())
            self.aliases.pop(trennen.lower(), None)
        if zuordnen:  # {"text": "Günther", "ph": "Person_2"} – Antwort auf eine Mehrdeutigkeits-Frage
            ziel = self.mapping.get(zuordnen.get("ph", ""))
            if ziel is None:
                raise ValueError("Die Zielperson wurde nicht gefunden.")
            self.aliases[zuordnen["text"].lower()] = ziel
            self.getrennt.discard(zuordnen["text"].lower())
        self._pseudonymisieren()
        return self.zustand()

    # ------------------------------------------------------------------ Markieren und im Rest suchen, Rückgängig
    def _dok(self, i: int) -> Dokument:
        if not (0 <= i < len(self.docs)):
            raise ValueError("Diese Datei gibt es in der Prüfung nicht.")
        return self.docs[i]

    def _sichern(self, was: str) -> None:
        import copy

        self.verlauf.append((was, copy.deepcopy({
            "findings": [d.findings for d in self.docs], "disabled": self.disabled, "bezeichnungen": self.bezeichnungen,
            "aliases": self.aliases, "getrennt": self.getrennt, "aus_stellen": self.aus_stellen, "manual": self.manual})))
        self.verlauf = self.verlauf[-40:]

    def rueckgaengig(self) -> dict:
        """Letzte Aktion beim Prüfen zurücknehmen (Karten und Dokumentansicht). Gelernte Einträge in den
        Einstellungen bleiben; sie lassen sich unter Einstellungen → Gelernte Begriffe löschen."""
        if not self.verlauf:
            raise ValueError("Es gibt nichts zum Rückgängigmachen.")
        was, st = self.verlauf.pop()
        for d, fs in zip(self.docs, st["findings"]):
            d.findings = fs
        self.disabled, self.bezeichnungen, self.aliases = st["disabled"], st["bezeichnungen"], st["aliases"]
        self.getrennt, self.aus_stellen, self.manual = st["getrennt"], st["aus_stellen"], st["manual"]
        self._pseudonymisieren()
        self.protokoll.notiere("info", f"Rückgängig: {was}")
        return {**self.zustand(), "rueckgaengig": was}

    def auswahl(self, dok: int, s: int, e: int, art: str | None = None) -> dict:
        """Markierte Stelle: an Wortgrenzen ausrichten, Art vorschlagen, alle Vorkommen im Vorgang suchen."""
        import re

        d = self._dok(dok)
        s, e = mk.ausrichten(d.text, int(s), int(e))
        begriff = " ".join(re.sub(r"(?<=\w)-[ \t]*\n[ \t]*(?=\w)", "", d.text[s:e]).split())
        if len(begriff) < 2:
            raise ValueError("Bitte mindestens zwei Zeichen markieren.")
        art = art if art in dict(mk.ARTEN) else mk.art_vorschlag(d.text, s, e)
        return {"dok": dok, "s": s, "e": e, "arten": mk.ARTEN, **mk.fundstellen(self.docs, begriff, art)}

    def markieren(self, begriff: str, art: str, stellen: list[dict], ursprung: dict | None = None,
                  gehoert_zu: str = "", lernen: bool = False) -> dict:
        """Ausgewählte Fundstellen als eigene Treffer anlegen (Quelle „manuell“). Stellen, die schon zu einem
        aktiven Treffer gehören, werden nicht doppelt angelegt. gehoert_zu: Platzhalter einer bestehenden Identität."""
        if gehoert_zu:
            ziel = self.mapping.get(gehoert_zu)
            if ziel is None:
                raise ValueError("Die Identität wurde nicht gefunden.")
            art = next((g["entity"] for g in self.identitaeten() if g["ph"] == gehoert_zu), art)
        if art not in dict(mk.ARTEN):
            raise ValueError("Unbekannte Art.")
        self._sichern(f"Markierung „{begriff}“")
        neu = 0
        for st in stellen:
            di, s, e = int(st["dok"]), int(st["s"]), int(st["e"])
            d = self._dok(di)
            if not (0 <= s < e <= len(d.text)) or any(f.active and s < f.end and e > f.start for f in d.findings):
                continue
            d.findings = [f for f in d.findings if not (s < f.end and e > f.start)]  # abgewählte Teiltreffer ersetzen
            self.aus_stellen.discard((di, s, e))
            eigen = bool(ursprung) and int(ursprung.get("dok", -1)) == di and int(ursprung.get("s", -1)) == s
            d.findings.append(Finding(s, e, art, 1.0, d.text[s:e], quelle="manuell",
                                      grund="von Ihnen markiert" if eigen else "wie von Ihnen markiert"))
            d.findings.sort(key=lambda f: f.start)
            if gehoert_zu:
                self.aliases[d.text[s:e].lower()] = ziel
                self.getrennt.discard(d.text[s:e].lower())
            elif d.text[s:e].lower() != begriff.lower():
                self.aliases[d.text[s:e].lower()] = begriff  # Schreibvariante (getrennt, gebeugt): gleicher Platzhalter
            neu += 1
        if not neu:
            self.verlauf.pop()
            raise ValueError("Alle gewählten Stellen sind schon markiert.")
        if begriff.lower() not in (m.lower() for m in self.manual):
            self.manual.append(begriff)  # bleibt bei einer erneuten Analyse erhalten
        if lernen:
            self.cfg_speichern(est.lernen(self.cfg_laden(), "immer_ersetzen", [begriff]))
        self._pseudonymisieren()
        self._protokoll_geheimnisse()
        self.protokoll.notiere("info", f"Markiert: {neu} Stellen als {LABELS.get(art, art)}"
                                       + (", künftig immer suchen" if lernen else ""))
        return {**self.zustand(), "neu": neu}

    def stelle(self, dok: int, s: int, e: int, aktion: str) -> dict:
        """Eine markierte Stelle im Dokument: "hier" (nur diese Stelle stehen lassen), "vorgang" (die Identität im
        ganzen Vorgang), "immer" (dazu dauerhaft lernen), "wieder" (doch anonymisieren)."""
        d = self._dok(dok)
        i = next((k for k, f in enumerate(d.findings) if f.start == int(s) and f.end == int(e)), None)
        if i is None:
            raise ValueError("Diese Stelle ist nicht markiert.")
        ph = d.schluessel.get(i, "")
        key = (dok, int(s), int(e))
        if aktion == "wieder":
            self._sichern("Stelle wieder anonymisiert")
            self.aus_stellen.discard(key)
            self.disabled.discard(ph)
        elif aktion == "hier":
            self._sichern("Stelle bleibt stehen")
            self.aus_stellen.add(key)
        elif aktion in ("vorgang", "immer"):
            self._sichern("Angabe bleibt stehen")
            if ph:
                self.disabled.add(ph)
            else:
                self.aus_stellen.add(key)
            if aktion == "immer":
                self.cfg_speichern(est.lernen(self.cfg_laden(), "stehen_lassen", self._varianten(ph) if ph else [d.findings[i].text]))
        else:
            raise ValueError("Unbekannte Aktion.")
        self._pseudonymisieren()
        return self.zustand()

    def _varianten(self, ph: str) -> list[str]:
        out = []
        for d in self.docs:
            for i, f in enumerate(d.findings):
                if d.schluessel.get(i) == ph and f.text not in out:
                    out.append(f.text)
        return out

    def nachtragen(self, begriffe: list[str]) -> None:
        neu = [b.strip() for b in begriffe if b.strip()]
        if not neu:
            return
        self.analysieren(self.manual + neu)

    def lernen(self, art: str, begriffe: list[str]) -> dict:
        """Korrektur dauerhaft merken (Einstellungen, nur auf diesem PC) und im laufenden Durchlauf anwenden."""
        cfg = est.lernen(self.cfg_laden(), art, begriffe)
        self.cfg_speichern(cfg)
        return self.zustand()

    def identitaeten(self) -> list[dict]:
        stehen = {b.lower() for b in est.gelernt(self.cfg_laden(), "stehen_lassen")}
        groups: dict[str, dict] = {}
        voll_namen = {ph: name for ph, name in self.mapping.items()
                      if ph.startswith(LABELS["PERSON"] + "_") and " " in name.strip()}
        for di, d in enumerate(self.docs):
            for i, f in enumerate(d.findings):
                ph = d.schluessel.get(i)
                if not ph:
                    continue
                g = groups.setdefault(ph, {"ph": ph, "typ": LABELS.get(f.entity, f.entity), "entity": f.entity,
                                           "gruppe": gruppe_von(f.entity), "name": self.mapping.get(ph, f.text),
                                           "varianten": [], "anzahl": 0, "score": 0.0, "dateien": [], "quellen": [],
                                           "belege": [],
                                           "beispiel": "", "fragen": [], "_erst": (di, f.start)})
                g["anzahl"] += 1
                g["score"] = max(g["score"], f.score)
                if f.text not in g["varianten"]:
                    g["varianten"].append(f.text)
                if d.name not in g["dateien"]:
                    g["dateien"].append(d.name)
                q = QUELLE_TEXT.get(f.quelle, f.quelle)
                if q not in g["quellen"]:
                    g["quellen"].append(q)
                beleg = f.grund or q
                if beleg not in g["belege"]:
                    g["belege"].append(beleg)
                if not g["beispiel"]:
                    g["beispiel"] = self._snippet(d.text, f)
                # Nackter Nachname, der zu mehreren Personen passen könnte
                if f.entity == "PERSON" and " " not in f.text.strip() and f.text.lower() not in self.aliases \
                        and f.text.lower() not in self.getrennt:
                    kand = [(p, n) for p, n in voll_namen.items()
                            if f.text.lower().rstrip("s") in [w.strip(".,").lower() for w in n.split()]]
                    if len(kand) > 1 and not any(fr["text"] == f.text for fr in g["fragen"]):
                        g["fragen"].append({"text": f.text, "kandidaten": [{"ph": p, "name": n} for p, n in kand]})
        out = []
        for g in groups.values():
            g["aktiv"] = g["ph"] not in self.disabled
            g["aus_einzeln"] = sum(1 for di, d in enumerate(self.docs) for i, f in enumerate(d.findings)
                                   if d.schluessel.get(i) == g["ph"] and (di, f.start, f.end) in self.aus_stellen)
            g["gelernt"] = any(v.lower() in stehen for v in g["varianten"])
            g["sicherheit"] = sicherheit(g["score"])
            gruende = []
            if g["score"] < 0.6:
                gruende.append("nur mit mittlerer Sicherheit erkannt")
            if "Anrede oder Unterschrift" in g["quellen"] and g["score"] < 0.7:
                gruende.append("nur über Anrede, Titel oder Unterschrift erkannt")
            if g["entity"] == "PERSON" and all(" " not in v for v in g["varianten"]) and g["quellen"] == ["Sprachmodell"]:
                gruende.append("einzelnes Wort ohne Vor- oder Nachnamen daneben")
            if g["fragen"]:
                gruende.append("Nachname passt zu mehreren Personen")
            g["gruende"] = gruende
            g["unsicher"] = bool(gruende)
            g["bezeichnung"] = self.bezeichnungen.get(g["ph"], "")
            g["anzeige"] = anzeige_platzhalter(g["ph"], self.bezeichnungen)
            g["vorschlaege"] = VORSCHLAEGE.get(g["entity"], [])
            g["varianten"] = sorted(g["varianten"], key=lambda v: (-len(v.split()), -len(v)))
            out.append(g)
        # Reihenfolge wie im Dokument (erstes Vorkommen), damit Karten nach einem Klick nicht springen
        reihen = list(GRUPPEN_ANZEIGE)
        out.sort(key=lambda g: (reihen.index(g["gruppe"]), g["_erst"]))
        for g in out:
            g.pop("_erst", None)
        return out

    @staticmethod
    def _snippet(text: str, f: Finding, breite: int = 60) -> str:
        vor = text[max(0, f.start - breite):f.start].replace("\n", " ")
        nach = text[f.end:f.end + breite].replace("\n", " ")
        return (("…" if f.start > breite else "") + html.escape(vor) + "<b>" + html.escape(text[f.start:f.end]) + "</b>"
                + html.escape(nach) + ("…" if f.end + breite < len(text) else ""))

    # ------------------------------------------------------------------ Zustand für die Oberfläche
    def zustand(self) -> dict:
        cfg = self.cfg_laden()
        return {
            "ordner": self.ordner,
            "dateien": [{"name": d.name, "groesse": len(d.data or b"") or (Path(d.pfad).stat().st_size if d.pfad else 0),
                         "seiten": d.info.get("seiten", 0), "ocr": d.info.get("ocr_seiten", 0)} for d in self.docs],
            "fortschritt": self.fortschritt.__dict__,
            "identitaeten": self.identitaeten() if self.fortschritt.fertig else [],
            "dokumente": [{"name": d.name, "markiert_html": markiert_html(
                               d.text, d.findings, d.platzhalter,
                               {(f.start, f.end): d.schluessel.get(i, "") for i, f in enumerate(d.findings)}, klassen=True),
                           "anonym": d.anonym, "ersetzt": sum(1 for f in d.findings if f.active)}
                          for d in self.docs] if self.fortschritt.fertig else [],
            "ergebnis": self.ergebnis,
            "rueckgaengig": self.verlauf[-1][0] if self.verlauf else "",
            "ausgabe_ordner": self.ordner or str(self._ausgabe_ordner(cfg)),
            "erweitert": cfg.get("erweitert", {}),
        }

    # ------------------------------------------------------------------ Anonymisieren
    def zurueck_zum_pruefen(self) -> dict:
        """Vom Ergebnis zurück in die Prüfung: Erkennung und Entscheidungen bleiben, das Ergebnis wird verworfen.
        Beim nächsten Anonymisieren werden die Kopien neu geschrieben."""
        if self.fortschritt.laeuft:
            raise ValueError("Bitte warten, bis Lokanon fertig ist.")
        if not self.docs or not any(d.findings or d.text for d in self.docs):
            raise ValueError("Es gibt keine Prüfung, zu der Lokanon zurückkehren kann.")
        self.ergebnis = None
        self.fortschritt = Fortschritt(fertig=True, schritt="Fertig", prozent=100)
        self.protokoll.notiere("info", "Zurück zum Prüfen")
        return self.zustand()

    def anonymisieren(self) -> None:
        if not self.fortschritt.fertig or self.fortschritt.laeuft:
            raise ValueError("Bitte zuerst die Analyse abschließen.")
        self.fortschritt = Fortschritt(laeuft=True, schritt="Anonymisiere", begonnen=time.time(), fertig=True)
        threading.Thread(target=self._anonymisieren_lauf, daemon=True).start()

    def _ausgabe_ordner(self, cfg: dict) -> Path:
        from server.einstellungen import ausgabe_ordner

        return ausgabe_ordner(cfg)

    def _anonymisieren_lauf(self) -> None:
        prot = self.protokoll
        prot.neuer_lauf("Anonymisieren", [d.name for d in self.docs], self.ordner, neu=False)
        self._protokoll_geheimnisse()
        try:
            cfg = self.cfg_laden()
            suffix = cfg.get("suffix") or "_anonymisiert"
            ziel = Path(self.ordner) if self.ordner else self._ausgabe_ordner(cfg)
            ziel.mkdir(parents=True, exist_ok=True)
            erweitert = cfg.get("erweitert") or {}
            vorgang = self._vorgang_anlegen(cfg) if erweitert.get("vorgaenge") else None
            dateien, hinweise = [], []
            namen_paare, vergeben = self._dateiname_paare(), set()
            n = len(self.docs)
            for i, d in enumerate(self.docs):
                self._melde("Anonymisiere", d.name, int(100 * i / n))
                pairs = replacement_pairs(d.text, d.findings, self.mapping, self.bezeichnungen, self.zuordnung)
                neu = aus.dateiname_anonym(d.name, suffix, namen_paare)
                stamm, endung, k = Path(neu).stem, Path(neu).suffix, 2
                while neu.lower() in vergeben:  # zwei Originale ergeben denselben Namen
                    neu, k = f"{stamm} ({k}){endung}", k + 1
                vergeben.add(neu.lower())
                eintrag = {"name": d.name, "ausgabe": neu, "pfad": str(ziel / neu), "status": "ok", "hinweis": "",
                           "ersetzt": sum(1 for f in d.findings if f.active), "funde": [], "rat": ""}
                rest = aus.leck_test(d.anonym, [f.text for f in d.findings if f.active])
                bewusst = {f.text.lower() for f in d.findings if not f.active}  # „nur hier stehen lassen“
                rest = [r for r in rest if r.lower() not in bewusst]
                try:
                    if rest:  # schon der Text ist nicht sauber: keine Kopie schreiben
                        raise fio.PdfLeck([(r, "im anonymisierten Text") for r in rest])
                    inhalt = aus.erzeuge(d.name, d.data, d.anonym, pairs)
                    (ziel / neu).write_bytes(inhalt)
                    if vorgang is not None:
                        vorgang.schreibe(d.name, inhalt, neu.rsplit(".", 1)[-1], Path(neu).stem)
                    prot.notiere("info", f"{d.name}: Kopie geschrieben, {eintrag['ersetzt']} Stellen ersetzt")
                except fio.PdfLeck as e:
                    eintrag["status"] = "fehler"
                    eintrag["funde"] = [{"text": o, "ort": ort} for o, ort in e.funde]
                    eintrag["hinweis"] = "Nicht erzeugt: Die Gegenprüfung fand danach noch Originaltext."
                    eintrag["rat"] = _rat(e.funde)
                    for o, ort in e.funde:
                        prot.notiere("fehler", f"{d.name}: Gegenprüfung fand {o} {ort}")
                    hinweise.append(f"{d.name}: Gegenprüfung fand noch Originaltext")
                except Exception as e:
                    eintrag["status"] = "fehler"
                    eintrag["hinweis"] = f"Datei nicht erzeugt: {e}"
                    eintrag["rat"] = ("Bitte das Protokoll unter „Details“ ansehen. Die Textfassung ist trotzdem "
                                      "nutzbar, sofern sie erzeugt wurde.")
                    prot.ausnahme(f"Kopie von {d.name}", e)
                    hinweise.append(f"{d.name}: {e}")
                ext = d.name.lower().rsplit(".", 1)[-1]
                # Textfassung: auf Wunsch immer, und als Ersatz, wenn die Kopie im Originalformat scheitert
                # (der Text hat den Leck-Test bestanden).
                if ext in ("pdf", "docx", "xlsx", "csv") and not rest and (
                        cfg.get("ki_textfassung") or eintrag["status"] == "fehler"):
                    md = Path(neu).stem + ".md"
                    (ziel / md).write_text(d.anonym, encoding="utf-8")
                    eintrag["textfassung"] = md
                    if eintrag["status"] == "fehler":
                        eintrag["ersatz"] = True
                        prot.notiere("info", f"{d.name}: Textfassung als Ersatz geschrieben")
                if vorgang is not None:
                    vorgang.notiere_treffer(d.name, d.findings, len(d.text), True)
                dateien.append(eintrag)
            if erweitert.get("testfaelle"):
                try:
                    if tf.speichern(est.daten_ordner(), self.docs):
                        prot.notiere("info", f"Als eigener Testfall gespeichert ({n} Dateien, verschlüsselt)")
                except Exception as e:  # ein Testfall darf das Anonymisieren nie verhindern
                    prot.ausnahme("Testfall speichern", e)
            schluessel_pfad = ""
            if erweitert.get("rueckuebersetzung"):
                schluessel_pfad = self._schluessel_speichern(cfg, ziel)
                if not schluessel_pfad:
                    hinweise.append("Kein Schlüssel gespeichert: In den Einstellungen fehlt das Passwort für Schlüssel.")
            if vorgang is not None:
                vorgang.mapping, vorgang.bezeichnungen = dict(self.mapping), dict(self.bezeichnungen)
                vorgang.schreibe_pruefbericht(pruefbericht_html(vorgang, [
                    {"name": d.name, "text": d.text, "findings": d.findings, "platzhalter": d.platzhalter} for d in self.docs]))
                vorgang.schreibe_uebersicht()
                vorgang.schreibe_protokoll()
            self.ergebnis = {"dateien": dateien, "ordner": str(ziel), "hinweise": hinweise,
                             "schluessel_pfad": schluessel_pfad, "vorgang": vorgang.basis if vorgang else "",
                             "zeit": datetime.now().isoformat(timespec="seconds")}
            self.schluessel_pfad = schluessel_pfad
            ok = sum(1 for e in dateien if e["status"] == "ok")
            prot.notiere("info" if ok == len(dateien) else "warnung", f"Anonymisieren fertig: {ok} von {len(dateien)} Kopien")
            self._melde("Fertig", "", 100)
        except Exception as e:
            prot.ausnahme("Anonymisieren", e)
            self.fortschritt.fehler = f"{e}"
        finally:
            self.fortschritt.laeuft = False

    def _dateiname_paare(self) -> list[tuple[str, str]]:
        """Ersetzungen für Dateinamen aus allen Dateien der Sitzung, damit "Klage Müller.docx" auch dann bereinigt
        wird, wenn Müller nur in einer anderen Datei steht. Dazu die Namensteile erkannter Personen ("Müller" aus
        "Hans Müller"), längste zuerst."""
        paare: dict[str, str] = {}
        for d in self.docs:
            for orig, ph in replacement_pairs(d.text, d.findings, self.mapping, self.bezeichnungen, self.zuordnung):
                paare.setdefault(orig, ph)
        for d in self.docs:
            for f in d.findings:
                if not f.active or f.entity != "PERSON" or f.text not in paare:
                    continue
                for teil in f.text.replace("-", " ").split():
                    teil = teil.strip(".,;:")
                    if len(teil) >= 3 and teil[0].isupper() and teil.lower() not in _ANREDEN:
                        paare.setdefault(teil, paare[f.text])
        return sorted(paare.items(), key=lambda kv: len(kv[0]), reverse=True)

    def _vorgang_anlegen(self, cfg: dict) -> Vorgang:
        from server.einstellungen import vorgaenge_ordner

        name = (Path(self.ordner).name if self.ordner else Path(self.docs[0].name).stem) + f" {datetime.now():%Y-%m-%d %H-%M}"
        v = Vorgang(name=name, ordner="", profil=cfg.get("profil", "kanzlei"))
        v.lege_basis_fest(vorgaenge_ordner(cfg))
        for d in self.docs:
            if d.data:
                v.sichere_original(d.name, d.data)
        return v

    def _schluessel_speichern(self, cfg: dict, ziel: Path) -> str:
        pw = (cfg.get("schluessel_passwort") or "").strip()
        if not pw:
            return ""
        from server.einstellungen import schluessel_ordner

        name = sicherer_name((Path(self.ordner).name if self.ordner else Path(self.docs[0].name).stem)
                             + f" {datetime.now():%Y-%m-%d %H-%M}")
        obj = {"vorgang": name, "erstellt": datetime.now().isoformat(timespec="seconds"), "mapping": self.mapping,
               "bezeichnungen": self.bezeichnungen, "ausgabe": str(ziel)}
        p = schluessel_ordner(cfg) / f"{name}.anon.json"
        p.write_bytes(encrypt_mapping(obj, pw))
        return str(p)

    # ------------------------------------------------------------------ Rückübersetzung (erweitert)
    def zurueck(self, text: str, schluessel_pfad: str = "", passwort: str = "") -> dict:
        if schluessel_pfad:
            p = Path(schluessel_pfad)
            if not p.exists():
                raise ValueError("Schlüsseldatei nicht gefunden.")
            obj = decrypt_mapping(p.read_bytes(), passwort or self.cfg_laden().get("schluessel_passwort", ""))
            mapping = mapping_aus_schluessel(obj)
            bez = obj.get("bezeichnungen", {}) if isinstance(obj, dict) else {}
            out = deanonymize(text, mapping, bez)
            return {"text": out, "quelle": p.name, "platzhalter": _ersetzt(text, out)}
        if not self.mapping:
            raise ValueError("Kein offener Durchlauf. Bitte eine Schlüsseldatei wählen.")
        out = deanonymize(text, self.mapping, self.bezeichnungen)
        return {"text": out, "quelle": "aktueller Durchlauf", "platzhalter": _ersetzt(text, out)}

    # ------------------------------------------------------------------ KI-Anweisung (erweitert)
    @staticmethod
    def anweisung() -> str:
        return ANWEISUNG_PATH.read_text(encoding="utf-8") if ANWEISUNG_PATH.exists() else ""

    @staticmethod
    def skill_zip() -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for p in SKILL_DIR.rglob("*"):
                if p.is_file():
                    z.write(p, f"{SKILL_DIR.name}/{p.relative_to(SKILL_DIR)}")
        return buf.getvalue()


_ANREDEN = {"herr", "herrn", "frau", "prof", "dr", "dres", "von", "van", "der", "den"}


def _zaehle(findings: list[Finding]) -> str:
    n: dict[str, int] = {}
    for f in findings:
        k = f"{LABELS.get(f.entity, f.entity)}/{f.quelle}"
        n[k] = n.get(k, 0) + 1
    return ", ".join(f"{k} {v}" for k, v in sorted(n.items())) or "keine"


def _rat(funde: list[tuple[str, str]]) -> str:
    """Was die Nutzerin tun kann, je nach Fundort der Gegenprüfung."""
    orte = " ".join(o for _, o in funde)
    if "sichtbaren Text" in orte or "anonymisierten Text" in orte:
        return ("Die Stelle steht noch sichtbar da, meist in einer anderen Schreibweise (getrennt, in Großbuchstaben, "
                "mit Bindestrich). „Zurück zum Prüfen“, den Begriff genau so nachtragen und erneut anonymisieren.")
    if "gescannten Seite" in orte:
        return ("Die Texterkennung liest die Stelle nach dem Schwärzen noch. „Zurück zum Prüfen“ und die Schreibweise "
                "nachtragen, oder die Textfassung verwenden.")
    return ("Der Text steckt in einem unsichtbaren Teil der PDF, den Lokanon nicht bereinigen konnte. Die Textfassung "
            "(.md) ist sauber und liegt im Ausgabeordner. Wer eine PDF braucht: Original über „Drucken → Microsoft "
            "Print to PDF“ neu erzeugen und diese Datei ablegen.")


def _ist_ausgabe(p: Path, suffix: str) -> bool:
    return p.stem.endswith(suffix)


def _ersetzt(vorher: str, nachher: str) -> int:
    """Wie viele [Platzhalter] beim Zurückübersetzen aufgelöst wurden."""
    import re

    rx = re.compile(r"\[[^\[\]\n]{1,60}\]")
    return max(0, len(rx.findall(vorher)) - len(rx.findall(nachher)))
