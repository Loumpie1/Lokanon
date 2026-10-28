"""Vorgangsdienst: der Zustand eines offenen Vorgangs und alle Arbeitsschritte (Analyse mit Fortschritt,
Begriffe schalten/umbenennen, Ausgabe, Schlüssel, Rückübersetzung). Die Oberfläche spricht nur mit diesem Dienst.
"""
from __future__ import annotations

import html
import io
import re
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from anonymizer import files as fio
from anonymizer.engine import (LABELS, Finding, anzeige_platzhalter, build_analyzer, deanonymize, detect,
                               propagate_vorgang, pseudonymize, replacement_pairs)
from anonymizer.vault import decrypt_mapping
from anonymizer.vorgang import (ANONYMISIERT, FUER_KI, LESBARE_TYPEN, ORIGINALE, Vorgang, dateien_im_ordner,
                                ist_cloud_pfad, ki_dateiname, mapping_aus_schluessel, markiert_html, pruefbericht_html,
                                sicherer_name)

APP_DIR = Path(__file__).resolve().parents[1]
ANWEISUNG_PATH = APP_DIR / "ki-anweisung" / "projekt-anweisung.md"
SKILL_DIR = APP_DIR / "ki-anweisung" / "lokanon-pseudonyme"

# Anzeige-Gruppen für die Kartenansicht (Reihenfolge = Anzeige)
KARTEN_GRUPPEN = {
    "Personen": ["PERSON"],
    "Firmen und Einrichtungen": ["ORGANIZATION"],
    "Adressen und Orte": ["ADRESSE", "PLZ_ORT", "LOCATION"],
    "Kontaktdaten": ["EMAIL_ADDRESS", "TELEFON", "URL", "IP_ADDRESS"],
    "Akten, Zeichen, Verträge": ["AKTENZEICHEN", "DIKTATZEICHEN", "GRUNDBUCH", "VERSICHERUNGSNR", "DE_HANDELSREGISTER"],
    "Konto und Steuer": ["IBAN_CODE", "KONTONUMMER", "CREDIT_CARD", "DE_TAX_ID", "DE_TAX_NUMBER", "DE_VAT_ID"],
    "Ausweise und Nummern": ["DE_ID_CARD", "DE_PASSPORT", "DE_FUEHRERSCHEIN", "FUEHRERSCHEIN", "DE_SOCIAL_SECURITY",
                             "DE_HEALTH_INSURANCE", "DE_LANR", "DE_BSNR"],
    "Fahrzeug": ["DE_KFZ", "KFZ", "FIN"],
    "Datum": ["DATUM"],
    "Beruf und Gesundheit": ["BERUF", "DIAGNOSE"],
    "Eigene Begriffe": ["EIGENE_BEGRIFFE", "MANUELL"],
}
QUELLE_TEXT = {"modell": "Sprachmodell", "regel": "Muster", "heuristik": "Anrede oder Unterschrift",
               "liste": "Ihre Liste", "wiederholung": "Wiederholung", "namensteil": "Namensteil", "vorgang": "andere Datei"}
BEZEICHNUNG_VORSCHLAEGE = {
    "PERSON": ["Mandant", "Mandantin", "Gegner", "Gegnerin", "Zeuge", "Zeugin", "Anwalt Gegenseite", "Sachverständiger",
               "Erblasser", "Erblasserin", "Kläger", "Beklagter"],
    "ORGANIZATION": ["Gegnerfirma", "Arbeitgeber", "Versicherung", "Gericht", "Werkstatt", "Bank"],
    "ADRESSE": ["Anschrift Mandant", "Anschrift Gegner", "Unfallort"],
    "PLZ_ORT": ["Wohnort Mandant", "Wohnort Gegner"],
}


def gruppe_von(entity: str) -> str:
    for g, ents in KARTEN_GRUPPEN.items():
        if entity in ents:
            return g
    return "Weitere"


def sicherheit(score: float) -> str:
    return "sicher" if score >= 0.7 else "wahrscheinlich" if score >= 0.5 else "unsicher"


def gruppen_key(f: Finding) -> str:
    return f"{f.entity}|{f.text.lower()}"


@dataclass
class Dokument:
    name: str
    text: str
    data: bytes | None
    info: dict = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    anonym: str = ""
    platzhalter: dict[tuple[int, int], str] = field(default_factory=dict)


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
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def starten(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._laden, daemon=True)
            self._thread.start()

    def _laden(self) -> None:
        try:
            a = build_analyzer(self.cfg["spacy_model"], self.cfg.get("gliner_model") or None,
                               float(self.cfg.get("gliner_threshold", 0.5)))
            with self._lock:
                self.analyzer = a
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


class VorgangDienst:
    def __init__(self, cfg_laden, cfg_speichern, modelle: Modelle):
        self.cfg_laden = cfg_laden
        self.cfg_speichern = cfg_speichern
        self.modelle = modelle
        self.vorgang: Vorgang | None = None
        self.vorgang_id: str = ""
        self.docs: list[Dokument] = []
        self.disabled: set[str] = set()
        self.bezeichnungen: dict[str, str] = {}
        self.manual: list[str] = []
        self.fortschritt = Fortschritt()
        self.ausgaben: list[dict] = []
        self.hinweise: list[str] = []
        self.schluessel_pfad: str = ""

    # ------------------------------------------------------------------ Vorgang anlegen und Dateien
    def neu(self, name: str, ordner: str = "") -> dict:
        cfg = self.cfg_laden()
        name = name.strip() or f"Vorgang {datetime.now():%Y-%m-%d %H-%M}"
        v = Vorgang(name=name, ordner=ordner.strip(), profil=cfg.get("profil", "kanzlei"))
        from server.einstellungen import vorgaenge_ordner

        v.lege_basis_fest(vorgaenge_ordner(cfg))
        self.vorgang, self.vorgang_id = v, uuid.uuid4().hex[:8]
        self.docs, self.disabled, self.bezeichnungen, self.manual = [], set(), {}, []
        self.ausgaben, self.hinweise, self.schluessel_pfad = [], [], ""
        self.fortschritt = Fortschritt()
        if ordner.strip():
            if ordner.strip() not in cfg.get("zuletzt_ordner", []):
                cfg["zuletzt_ordner"] = ([ordner.strip()] + cfg.get("zuletzt_ordner", []))[:8]
                self.cfg_speichern(cfg)
        return self.zustand_kurz()

    def datei_hinzufuegen(self, name: str, data: bytes) -> dict:
        """Hochgeladene Datei sofort im Vorgangsordner sichern (Originale\\)."""
        v = self._v()
        name = Path(name).name
        if name.lower().rsplit(".", 1)[-1] not in LESBARE_TYPEN:
            raise ValueError(f"{name}: Dateityp wird nicht unterstützt (txt, md, docx, pdf, xlsx, csv).")
        if v.ordner:
            raise ValueError("Bei einem Aktenordner werden die Dateien aus dem Ordner gelesen.")
        v.sichere_original(name, data)
        self.docs = [d for d in self.docs if d.name != name]
        self.docs.append(Dokument(name=name, text="", data=data))
        return {"name": name, "groesse": len(data)}

    def text_setzen(self, text: str) -> dict:
        v = self._v()
        data = text.encode("utf-8")
        v.sichere_original("text.txt", data)
        self.docs = [d for d in self.docs if d.name != "text.txt"]
        self.docs.append(Dokument(name="text.txt", text=text, data=data))
        return {"name": "text.txt", "groesse": len(data)}

    def datei_entfernen(self, name: str) -> None:
        v = self._v()
        self.docs = [d for d in self.docs if d.name != name]
        p = v.originale / name
        if p.exists() and not v.ordner:
            p.unlink()

    def ordner_dateien(self) -> list[dict]:
        v = self._v()
        if not v.ordner:
            return []
        return [{"name": p.name, "groesse": p.stat().st_size} for p in dateien_im_ordner(v.ordner)]

    # ------------------------------------------------------------------ Analyse (Hintergrund mit Fortschritt)
    def analysieren(self, manual: list[str] | None = None) -> None:
        v = self._v()
        if self.fortschritt.laeuft:
            return
        self.manual = [m.strip() for m in (manual or []) if m.strip()]
        self.fortschritt = Fortschritt(laeuft=True, schritt="Modelle laden", begonnen=time.time())
        threading.Thread(target=self._analyse_lauf, daemon=True).start()

    def _melde(self, schritt: str, datei: str = "", prozent: int | None = None) -> None:
        self.fortschritt.schritt = schritt
        self.fortschritt.datei = datei
        if prozent is not None:
            self.fortschritt.prozent = prozent

    def _analyse_lauf(self) -> None:
        try:
            v = self._v()
            cfg = self.cfg_laden()
            self.modelle.warten()
            analyzer = self.modelle.analyzer
            if v.ordner:
                self.docs = [Dokument(name=p.name, text="", data=p.read_bytes()) for p in dateien_im_ordner(v.ordner)]
            if not self.docs:
                raise ValueError("Keine Dateien im Vorgang.")
            n = len(self.docs)
            for i, d in enumerate(self.docs):
                self._melde("Lese Datei", d.name, int(5 + 45 * i / n))
                if d.name == "text.txt" and d.text:
                    d.info = {}
                else:
                    d.text, d.info = fio.read_document(d.name, d.data)
            for i, d in enumerate(self.docs):
                self._melde("Erkenne Personendaten", d.name, int(50 + 45 * i / n))
                d.findings = detect(analyzer, d.text, cfg["entities"], float(cfg.get("threshold", 0.4)),
                                    cfg.get("allow_list"), cfg.get("deny_list"), self.manual,
                                    cfg.get("propagate_repeats", True), cfg.get("include_name_parts", True),
                                    cfg.get("mask_locations", False), cfg.get("keep_institutions", True),
                                    cfg.get("datum_modus", "kontext"))
            self._melde("Gleiche Begriffe über alle Dateien ab", "", 96)
            neu = propagate_vorgang([d.text for d in self.docs], [d.findings for d in self.docs],
                                    cfg.get("allow_list"), cfg.get("include_name_parts", True))
            for d, fs in zip(self.docs, neu):
                d.findings = fs
            self.disabled = set()
            self._pseudonymisieren()
            self._melde("Fertig", "", 100)
            self.fortschritt.fertig = True
        except Exception as e:
            self.fortschritt.fehler = f"{e}"
        finally:
            self.fortschritt.laeuft = False

    def _pseudonymisieren(self) -> None:
        v = self._v()
        mapping: dict[str, str] = {}
        for d in self.docs:
            for f in d.findings:
                f.active = gruppen_key(f) not in self.disabled
            res = pseudonymize(d.text, d.findings, mapping, self.bezeichnungen)
            d.anonym = res.anonymized
            mapping = res.mapping
        for d in self.docs:
            paare = dict(replacement_pairs(d.text, d.findings, mapping, self.bezeichnungen))
            d.platzhalter = {(f.start, f.end): paare.get(f.text, "") for f in d.findings if f.active}
        v.mapping = mapping
        v.bezeichnungen = dict(self.bezeichnungen)

    # ------------------------------------------------------------------ Prüfen
    def begriff_schalten(self, key: str, aktiv: bool) -> dict:
        if aktiv:
            self.disabled.discard(key)
        else:
            self.disabled.add(key)
        self._pseudonymisieren()
        return self.zustand()

    def bezeichnung_setzen(self, platzhalter: str, bezeichnung: str) -> dict:
        b = bezeichnung.strip()
        if b:
            self.bezeichnungen[platzhalter] = b
        else:
            self.bezeichnungen.pop(platzhalter, None)
        self._pseudonymisieren()
        return self.zustand()

    def nachtragen(self, begriffe: list[str]) -> None:
        neu = [b.strip() for b in begriffe if b.strip()]
        self.analysieren(self.manual + neu)

    def begriffe(self) -> list[dict]:
        groups: dict[str, dict] = {}
        for d in self.docs:
            for f in d.findings:
                k = gruppen_key(f)
                g = groups.setdefault(k, {"key": k, "begriff": f.text, "typ": LABELS.get(f.entity, f.entity),
                                          "entity": f.entity, "gruppe": gruppe_von(f.entity), "anzahl": 0, "score": 0.0,
                                          "dateien": [], "quellen": [], "platzhalter": "", "beispiel": ""})
                g["anzahl"] += 1
                g["score"] = max(g["score"], f.score)
                if d.name not in g["dateien"]:
                    g["dateien"].append(d.name)
                q = QUELLE_TEXT.get(f.quelle, f.quelle)
                if q not in g["quellen"]:
                    g["quellen"].append(q)
                if not g["beispiel"]:
                    g["beispiel"] = self._snippet(d.text, f)
                ph = d.platzhalter.get((f.start, f.end))
                if ph and not g["platzhalter"]:
                    g["platzhalter"] = ph
        texte_typen: dict[str, set] = {}
        for g in groups.values():
            texte_typen.setdefault(g["begriff"].lower(), set()).add(g["entity"])
        out = []
        for g in groups.values():
            g["aktiv"] = g["key"] not in self.disabled
            g["sicherheit"] = sicherheit(g["score"])
            gruende = []
            if g["score"] < 0.6:
                gruende.append("nur mit mittlerer Sicherheit erkannt")
            if "Anrede oder Unterschrift" in g["quellen"] and g["score"] < 0.7:
                gruende.append("nur über Anrede, Titel oder Unterschrift erkannt")
            if len(texte_typen[g["begriff"].lower()]) > 1:
                gruende.append("kann Person oder Ort/Firma sein")
            if g["entity"] == "PERSON" and " " not in g["begriff"] and g["quellen"] == ["Sprachmodell"]:
                gruende.append("einzelnes Wort ohne Vor- oder Nachnamen daneben")
            g["gruende"] = gruende
            g["unsicher"] = bool(gruende)
            # Platzhalter-Basis (PERSON_1) für die Umbenennung
            g["ph_basis"] = self._ph_basis(g)
            g["bezeichnung"] = self.bezeichnungen.get(g["ph_basis"], "") if g["ph_basis"] else ""
            g["vorschlaege"] = BEZEICHNUNG_VORSCHLAEGE.get(g["entity"], [])
            out.append(g)
        out.sort(key=lambda g: (list(KARTEN_GRUPPEN).index(g["gruppe"]) if g["gruppe"] in KARTEN_GRUPPEN else 99,
                                -g["anzahl"], g["begriff"].lower()))
        return out

    def _ph_basis(self, g: dict) -> str:
        v = self._v()
        reverse = {val.lower(): k for k, val in v.mapping.items()}
        key = g["begriff"].lower()
        if key in reverse:
            return reverse[key]
        for full, ph in reverse.items():
            if key in [w.strip(".,").lower() for w in full.split()]:
                return ph
        return ""

    @staticmethod
    def _snippet(text: str, f: Finding, breite: int = 60) -> str:
        vor = text[max(0, f.start - breite):f.start].replace("\n", " ")
        nach = text[f.end:f.end + breite].replace("\n", " ")
        return (("…" if f.start > breite else "") + html.escape(vor) + "<b>" + html.escape(text[f.start:f.end]) + "</b>"
                + html.escape(nach) + ("…" if f.end + breite < len(text) else ""))

    # ------------------------------------------------------------------ Zustand für die Oberfläche
    def zustand_kurz(self) -> dict:
        v = self._v()
        return {"id": self.vorgang_id, "name": v.name, "ordner": v.ordner, "basis": v.basis,
                "originale": str(v.originale) if not v.ordner else v.ordner,
                "cloud": ist_cloud_pfad(v.basis), "dateien": [{"name": d.name, "groesse": len(d.data or b""),
                                                               "info": d.info} for d in self.docs],
                "fortschritt": self.fortschritt.__dict__}

    def zustand(self) -> dict:
        v = self._v()
        z = self.zustand_kurz()
        z.update({
            "begriffe": self.begriffe(),
            "platzhalter_anzahl": len(v.mapping),
            "dokumente": [{"name": d.name, "zeichen": len(d.text), "ocr": d.info.get("ocr_seiten", 0),
                           "seiten": d.info.get("seiten", 0), "ersetzt": sum(1 for f in d.findings if f.active),
                           "markiert_html": markiert_html(d.text, d.findings, d.platzhalter), "anonym": d.anonym}
                          for d in self.docs],
            "ausgaben": self.ausgaben, "hinweise": self.hinweise, "abgeschlossen": v.abgeschlossen,
            "schluessel_pfad": self.schluessel_pfad, "ki_ordner": str(v.ki_ordner), "bezeichnungen": self.bezeichnungen,
        })
        return z

    # ------------------------------------------------------------------ Ausgabe
    def ausgabe(self, formate: list[str], anbieter: str) -> dict:
        v = self._v()
        v.anbieter = anbieter
        v.hinweise, v.dateien = [], []
        v.leere_ausgabe()
        self.ausgaben = []
        paare_vorgang = _alle_paare(v.mapping, self.bezeichnungen)
        for d in self.docs:
            ext = d.name.lower().rsplit(".", 1)[-1]
            ki = ki_dateiname(d.name, paare_vorgang)
            pairs = replacement_pairs(d.text, d.findings, v.mapping, self.bezeichnungen)
            v.notiere_treffer(d.name, d.findings, len(d.text), True)
            eintrag = {"name": d.name, "dateien": [], "status": "ok", "hinweis": ""}
            _, kip = v.schreibe(d.name, d.anonym.encode("utf-8"), "md", ki)
            eintrag["dateien"].append(kip.name)
            if d.data and ext == "docx" and "docx" in formate:
                try:
                    _, kip = v.schreibe(d.name, fio.write_docx(d.data, pairs), "docx", ki)
                    eintrag["dateien"].append(kip.name)
                except Exception as e:
                    eintrag["hinweis"] = f"Word-Kopie nicht möglich ({e})"
            if d.data and ext == "xlsx" and "xlsx" in formate:
                try:
                    _, kip = v.schreibe(d.name, fio.write_xlsx(d.data, pairs), "xlsx", ki)
                    eintrag["dateien"].append(kip.name)
                except Exception as e:
                    eintrag["hinweis"] = f"Excel-Kopie nicht möglich ({e})"
            if d.data and ext == "pdf" and "pdf" in formate:
                try:
                    _, kip = v.schreibe(d.name, fio.write_pdf(d.data, pairs), "pdf", ki)
                    eintrag["dateien"].append(kip.name)
                except Exception as e:
                    eintrag["hinweis"] = "PDF-Sichtkopie verworfen, weil die Gegenprüfung noch Originaltext fand. " \
                                         "Die Textfassung (.md) ist sauber."
                    eintrag["status"] = "teilweise"
                    v.hinweise.append(f"{d.name}: {e}")
            rest = [f.text for f in d.findings if f.active and len(f.text) >= 3
                    and re.search(rf"(?<!\w){re.escape(f.text)}(?!\w)", d.anonym, flags=re.IGNORECASE)]
            if rest:
                eintrag["status"] = "fehler"
                eintrag["hinweis"] = "Textfassung enthält noch Originaltext: " + ", ".join(sorted(set(rest)))
                v.hinweise.append(f"{d.name}: Leck-Test – {', '.join(sorted(set(rest)))}")
            self.ausgaben.append(eintrag)
        v.schreibe_pruefbericht(pruefbericht_html(v, [{"name": d.name, "text": d.text, "findings": d.findings,
                                                      "platzhalter": d.platzhalter} for d in self.docs]))
        v.schreibe_uebersicht()
        v.schreibe_protokoll()
        self.hinweise = list(v.hinweise)
        return {"ausgaben": self.ausgaben, "hinweise": self.hinweise, "basis": v.basis, "ki_ordner": str(v.ki_ordner),
                "pruefbericht": str(v.basis_pfad / "Pruefbericht.html")}

    def ki_zip(self) -> bytes:
        v = self._v()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            if v.ki_ordner.is_dir():
                for p in v.ki_ordner.iterdir():
                    if p.is_file():
                        z.write(p, p.name)
        return buf.getvalue()

    # ------------------------------------------------------------------ Schlüssel und Rückübersetzung
    def abschliessen(self, passwort: str, ordner: str | None = None) -> dict:
        v = self._v()
        if not passwort:
            raise ValueError("Bitte ein Passwort für den Schlüssel eingeben.")
        from server.einstellungen import schluessel_ordner

        cfg = self.cfg_laden()
        ziel = Path(ordner) if ordner else schluessel_ordner(cfg)
        v.abschliessen()
        p = v.speichere_schluessel(passwort, ziel)
        v.schreibe_protokoll()
        self.schluessel_pfad = str(p)
        return {"schluessel_pfad": str(p), "abgeschlossen": v.abgeschlossen}

    def zurueck(self, text: str, mapping: dict | None = None, bezeichnungen: dict | None = None) -> str:
        if mapping is None:
            v = self._v()
            mapping, bezeichnungen = v.mapping, self.bezeichnungen
        return deanonymize(text, mapping, bezeichnungen)

    @staticmethod
    def schluessel_laden(blob: bytes, passwort: str) -> tuple[dict, dict, str]:
        obj = decrypt_mapping(blob, passwort)
        mapping = mapping_aus_schluessel(obj)
        bez = obj.get("bezeichnungen", {}) if isinstance(obj, dict) else {}
        name = obj.get("vorgang", "") if isinstance(obj, dict) else ""
        return mapping, bez, name

    # ------------------------------------------------------------------ Sonstiges
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

    def _v(self) -> Vorgang:
        if self.vorgang is None:
            raise ValueError("Kein Vorgang geöffnet.")
        return self.vorgang


def _alle_paare(mapping: dict[str, str], bezeichnungen: dict[str, str] | None) -> list[tuple[str, str]]:
    pairs = {}
    for ph, orig in mapping.items():
        pairs[orig] = anzeige_platzhalter(ph, bezeichnungen)
        if ph.startswith("PERSON_"):
            for part in orig.split():
                p = part.strip(".,")
                if len(p) >= 3 and p[0].isupper() and p.lower() not in ("dr", "prof"):
                    pairs.setdefault(p, anzeige_platzhalter(ph, bezeichnungen))
    return sorted(pairs.items(), key=lambda kv: len(kv[0]), reverse=True)


def vorgaenge_liste(ordner: Path) -> list[dict]:
    """Bisherige Vorgänge im Vorgaenge-Ordner (mit Protokoll.json)."""
    out = []
    if not ordner.is_dir():
        return out
    for p in sorted(ordner.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        prot = p / "Protokoll.json"
        if p.is_dir():
            eintrag = {"name": p.name, "basis": str(p), "angelegt": "", "abgeschlossen": "", "dateien": 0,
                       "platzhalter": 0, "ki_ordner": str(p / FUER_KI)}
            if prot.exists():
                try:
                    import json

                    d = json.loads(prot.read_text(encoding="utf-8"))
                    eintrag.update(name=d.get("vorgang", p.name), angelegt=d.get("erstellt", ""),
                                   abgeschlossen=d.get("abgeschlossen", ""), dateien=len(d.get("dateien", [])),
                                   platzhalter=d.get("platzhalter_gesamt", 0))
                except Exception:
                    pass
            else:
                eintrag["angelegt"] = datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")
            out.append(eintrag)
    return out
