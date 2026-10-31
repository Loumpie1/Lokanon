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
                                "DE_HEALTH_INSURANCE", "DE_LANR", "DE_BSNR", "DE_KFZ", "KFZ", "FIN"],
    "Daten und Sonstiges": ["DATUM", "BERUF", "DIAGNOSE", "EIGENE_BEGRIFFE", "MANUELL"],
}
QUELLE_TEXT = {"modell": "Sprachmodell", "regel": "Muster", "heuristik": "Anrede oder Unterschrift",
               "liste": "Ihre Liste", "wiederholung": "Wiederholung", "namensteil": "Namensteil", "vorgang": "andere Datei"}
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
        self.leeren()

    def leeren(self) -> dict:
        self.docs: list[Dokument] = []
        self.ordner: str = ""
        self.manual: list[str] = []
        self.disabled: set[str] = set()          # Platzhalter-Schlüssel, die stehen bleiben ("Person_2")
        self.bezeichnungen: dict[str, str] = {}  # "Person_1" -> "Mandant"
        self.aliases: dict[str, str] = {}        # "günther" -> "Cornelia Günther" (gehört zu …)
        self.getrennt: set[str] = set()          # Schreibweisen, die eine eigene Identität bleiben
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
        try:
            cfg = self.cfg_laden()
            self.modelle.warten()
            analyzer = self.modelle.analyzer
            n = len(self.docs)
            for i, d in enumerate(self.docs):
                self._melde("Lese", d.name, int(5 + 45 * i / n))
                if d.data is None and d.pfad:
                    d.data = Path(d.pfad).read_bytes()
                if d.name.lower().endswith(".txt") and d.text:
                    d.info = {}
                else:
                    d.text, d.info = fio.read_document(d.name, d.data or b"")
            for i, d in enumerate(self.docs):
                self._melde("Erkenne Personendaten", d.name, int(50 + 45 * i / n))
                d.findings = detect(analyzer, d.text, cfg["entities"], float(cfg.get("threshold", 0.4)),
                                    cfg.get("allow_list"), cfg.get("deny_list"), self.manual,
                                    cfg.get("propagate_repeats", True), cfg.get("include_name_parts", True),
                                    cfg.get("mask_locations", False), cfg.get("keep_institutions", True),
                                    cfg.get("datum_modus", "kontext"))
            self._melde("Gleiche Namen über alle Dateien ab", "", 96)
            neu = propagate_vorgang([d.text for d in self.docs], [d.findings for d in self.docs],
                                    cfg.get("allow_list"), cfg.get("include_name_parts", True))
            for d, fs in zip(self.docs, neu):
                d.findings = fs
            self._pseudonymisieren()
            self._melde("Fertig", "", 100)
            self.fortschritt.fertig = True
        except Exception as e:
            self.fortschritt.fehler = f"{e}"
        finally:
            self.fortschritt.laeuft = False

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
        for d in self.docs:
            d.schluessel = platzhalter_schluessel(d.findings, mapping, zuordnung)
            for i, f in enumerate(d.findings):
                f.active = d.schluessel.get(i, "") not in self.disabled
            res = pseudonymize(d.text, d.findings, mapping, self.bezeichnungen, fest, self.getrennt)
            d.anonym = res.anonymized
            paare = dict(replacement_pairs(d.text, d.findings, mapping, self.bezeichnungen, zuordnung))
            d.platzhalter = {(f.start, f.end): paare.get(f.text, "") for f in d.findings if f.active}

    # ------------------------------------------------------------------ Prüfen
    def identitaet(self, ph: str, aktiv: bool | None = None, bezeichnung: str | None = None,
                   gehoert_zu: str | None = None, trennen: str | None = None,
                   zuordnen: dict | None = None) -> dict:
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

    def identitaeten(self) -> list[dict]:
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
            "dokumente": [{"name": d.name, "markiert_html": markiert_html(d.text, d.findings, d.platzhalter),
                           "anonym": d.anonym, "ersetzt": sum(1 for f in d.findings if f.active)}
                          for d in self.docs] if self.fortschritt.fertig else [],
            "ergebnis": self.ergebnis,
            "ausgabe_ordner": self.ordner or str(self._ausgabe_ordner(cfg)),
            "erweitert": cfg.get("erweitert", {}),
        }

    # ------------------------------------------------------------------ Anonymisieren
    def anonymisieren(self) -> None:
        if not self.fortschritt.fertig or self.fortschritt.laeuft:
            raise ValueError("Bitte zuerst die Analyse abschließen.")
        self.fortschritt = Fortschritt(laeuft=True, schritt="Anonymisiere", begonnen=time.time(), fertig=True)
        threading.Thread(target=self._anonymisieren_lauf, daemon=True).start()

    def _ausgabe_ordner(self, cfg: dict) -> Path:
        from server.einstellungen import ausgabe_ordner

        return ausgabe_ordner(cfg)

    def _anonymisieren_lauf(self) -> None:
        try:
            cfg = self.cfg_laden()
            suffix = cfg.get("suffix") or "_anonymisiert"
            ziel = Path(self.ordner) if self.ordner else self._ausgabe_ordner(cfg)
            ziel.mkdir(parents=True, exist_ok=True)
            erweitert = cfg.get("erweitert") or {}
            vorgang = self._vorgang_anlegen(cfg) if erweitert.get("vorgaenge") else None
            dateien, hinweise = [], []
            n = len(self.docs)
            for i, d in enumerate(self.docs):
                self._melde("Anonymisiere", d.name, int(100 * i / n))
                pairs = replacement_pairs(d.text, d.findings, self.mapping, self.bezeichnungen, self.zuordnung)
                neu = aus.dateiname_anonym(d.name, suffix)
                eintrag = {"name": d.name, "ausgabe": neu, "pfad": str(ziel / neu), "status": "ok", "hinweis": "",
                           "ersetzt": sum(1 for f in d.findings if f.active)}
                try:
                    inhalt = aus.erzeuge(d.name, d.data, d.anonym, pairs)
                    (ziel / neu).write_bytes(inhalt)
                    if vorgang is not None:
                        vorgang.schreibe(d.name, inhalt, neu.rsplit(".", 1)[-1], Path(neu).stem)
                except Exception as e:
                    eintrag["status"] = "fehler"
                    eintrag["hinweis"] = (f"Datei nicht erzeugt: {e}" if "noch" not in str(e) else
                                          "Nicht erzeugt: Die Gegenprüfung fand noch Originaltext. "
                                          "Bitte die Textfassung verwenden oder die Stelle nachtragen.")
                    hinweise.append(f"{d.name}: {e}")
                rest = aus.leck_test(d.anonym, [f.text for f in d.findings if f.active])
                if rest and eintrag["status"] == "ok":
                    eintrag["status"] = "fehler"
                    eintrag["hinweis"] = "Noch lesbar: " + ", ".join(rest) + ". Bitte Begriff nachtragen."
                if cfg.get("ki_textfassung") and d.name.lower().rsplit(".", 1)[-1] in ("pdf", "docx", "xlsx", "csv"):
                    md = Path(neu).stem + ".md"
                    (ziel / md).write_text(d.anonym, encoding="utf-8")
                    eintrag["textfassung"] = md
                if vorgang is not None:
                    vorgang.notiere_treffer(d.name, d.findings, len(d.text), True)
                dateien.append(eintrag)
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
            self._melde("Fertig", "", 100)
        except Exception as e:
            self.fortschritt.fehler = f"{e}"
        finally:
            self.fortschritt.laeuft = False

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


def _ist_ausgabe(p: Path, suffix: str) -> bool:
    return p.stem.endswith(suffix)


def _ersetzt(vorher: str, nachher: str) -> int:
    """Wie viele [Platzhalter] beim Zurückübersetzen aufgelöst wurden."""
    import re

    rx = re.compile(r"\[[^\[\]\n]{1,60}\]")
    return max(0, len(rx.findall(vorher)) - len(rx.findall(nachher)))
