"""Gedächtnis: gelernte Angaben, Fälle, Vorgangsverzeichnis, Fristen und Löschprotokoll.

Anforderung: docs/anforderungen/lernen-und-loeschfristen.md (Abschnitte 2–7 und 11).

- Gelernte Angaben: was der Anwender selbst markiert und am Ende bestätigt hat („künftig vorschlagen“), dazu
  „künftig immer stehen lassen“. Jede Angabe gehört zu einem oder mehreren Fällen.
- Regeln: gelernte Bezeichnungen („Wert nach ‚Mandantennr.‘“) und Nummernmuster („AZ-0000-0000“). Sie enthalten
  keine Personendaten und haben keine Frist.
- Fälle: Etikett eines Vorgangs, meist das Aktenzeichen aus dem Dokument. Die Löschfrist läuft je Fall ab dem letzten
  Fund; „Mandat läuft“ hält ihn, „abgeschlossen“ startet eine kurze Frist.
- Vorgangsverzeichnis: je Anonymisieren die Pfade der Kopien, des Schlüssels, des Vorgangsordners und der Testfälle,
  damit ein Fall vollständig gelöscht werden kann.
- Löschprotokoll: Datum, Fallnummer, Arten und Anzahl, Grund. Ohne Namen.

Alles liegt in <home>/gedaechtnis.lokanon, verschlüsselt mit server/tresor.py (Windows-Konto).
"""
from __future__ import annotations

import json
import re
import shutil
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

from server import tresor

DATEI = "gedaechtnis.lokanon"
# Arten ohne Personenbezug: kein Fallbezug nötig, keine Frist
OHNE_PERSONENBEZUG = {"PROJEKT"}
STANDARD_FRISTEN = {"personen_monate": 12, "abgeschlossen_monate": 3, "warnen_tage": 30, "lernen_fragen": True}
GRUENDE = {"mandant": "Wunsch des Mandanten", "abgeschlossen": "Fall abgeschlossen", "sonstiges": "Sonstiges",
           "frist": "Frist abgelaufen", "hand": "von Hand"}
NUMMERN_ARTEN = {"KENNNUMMER", "AKTENZEICHEN", "PERSONALNR", "VERSICHERUNGSNR", "DE_HEALTH_INSURANCE", "KONTONUMMER",
                 "TELEFON", "DATUM"}


def heute() -> date:
    return date.today()


def _plus_monate(d: date, monate: int) -> date:
    m = d.month - 1 + monate
    j, m = d.year + m // 12, m % 12 + 1
    tage = [31, 29 if j % 4 == 0 and (j % 100 or j % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(j, m, min(d.day, tage))


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s[:10]) if s else None


def fristen(cfg: dict) -> dict:
    return {**STANDARD_FRISTEN, **(cfg.get("aufbewahrung") or {})}


# ------------------------------------------------------------------------------------------- Regeln
# Bezeichnung am Zeilenende vor der Markierung: bis drei Wörter, nur das letzte darf auf einen Punkt enden
# („Kunden-Nr.“, „Name des Versicherten“), damit kein Satzende davor mitkommt („Falkenhorst. Mandantennr.:“).
_BEZ_RX = re.compile(r"(?P<bez>(?:[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß\-]*[ \-]){0,2}[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß.\-]*)"
                     r"[ \t]*(?P<sep>:|#)?[ \t]*$")
_BEZ_ENDEN = ("nr", "nummer", "id", "zeichen", "kennung", "code", "az", "kennz")


def regel_vorschlag(text: str, s: int, e: int, entity: str) -> dict | None:
    """Steht vor der markierten Stelle eine Bezeichnung („Mandantennr.: 48213“), lässt sich statt des Werts die
    Bezeichnung lernen. Sonst, bei Nummern mit festem Aufbau („AZ-2026-0815“), das Muster. Beides ohne Personendaten."""
    zeile_anfang = text.rfind("\n", 0, s) + 1
    vor = text[zeile_anfang:s].split("|")[-1]
    m = _BEZ_RX.search(vor)
    bez_regel = None
    if m:
        bez = m.group("bez").strip(" -")
        roh = bez.lower().rstrip(".")
        if 2 <= len(bez) <= 30 and sum(c.isalpha() for c in bez) >= 2 and (m.group("sep") or roh.endswith(_BEZ_ENDEN)):
            bez_regel = {"art": "bezeichnung", "wert": bez, "entity": entity, "text": f"Wert nach „{bez}“"}
            if m.group("sep"):  # „Mandantennr.: …“ ist eindeutig ein Feld
                return bez_regel
    muster = nummern_muster(text[s:e])
    if muster:
        return {"art": "muster", "wert": muster[0], "form": muster[1], "entity": entity,
                "text": f"Nummern wie „{muster[1]}“"}
    return bez_regel


def nummern_muster(wert: str) -> tuple[str, str] | None:
    """„AZ-2026-0815“ → (r"AZ-\\d{4}-\\d{4}", "AZ-0000-0000"). Nur Nummern mit Ziffern und mindestens einem Buchstaben;
    reine Ziffernfolgen, auch mit Trennzeichen, wären zu allgemein (Postleitzahl, Betrag, Datum „2026-11“)."""
    w = wert.strip()
    if not (4 <= len(w) <= 30) or not re.fullmatch(r"[A-Za-z0-9\-/. ]+", w) or sum(c.isdigit() for c in w) < 3:
        return None
    if not re.search(r"[A-Za-z]", w):
        return None
    rx, form = [], []
    for t in re.finditer(r"\d+|[A-Z]+|[a-z]+|.", w):
        g = t.group()
        if g.isdigit():
            rx.append(rf"\d{{{len(g)}}}")
            form.append("0" * len(g))
        elif g.isalpha():
            rx.append(re.escape(g) if len(g) <= 4 else (f"[A-Z]{{{len(g)}}}" if g.isupper() else f"[a-z]{{{len(g)}}}"))
            form.append(g if len(g) <= 4 else "A" * len(g))
        else:
            rx.append(r"\s" if g == " " else re.escape(g))
            form.append(g)
    return "".join(rx), "".join(form)


def regel_treffer(text: str, regeln: list[dict]):
    """Treffer der gelernten Regeln im Text (Quelle „gelernt“, mit Begründung)."""
    from anonymizer.engine import Finding

    out = []
    for r in regeln:
        ent = r.get("entity") or "KENNNUMMER"
        if r["art"] == "bezeichnung":
            if ent in NUMMERN_ARTEN:
                wert = r"[A-Za-z0-9][A-Za-z0-9\-/.]*\d[A-Za-z0-9\-/.]*"
            elif ent in ("PERSON", "ORGANIZATION"):
                wert = r"[A-ZÄÖÜ][\wäöüß'’\-]+(?:[ \t]+[A-ZÄÖÜ&][\wäöüß'’\-.]*){0,3}"
            else:
                wert = r"[^\s|;][^\n|;]{1,39}?(?=[ \t]*(?:[|;\n]|$|[ \t]{2}))"
            rx = rf"(?i:(?<![\wäöüß]){re.escape(r['wert'])})[ \t]*[:#]?[ \t]*(?P<w>{wert})"
            for m in re.finditer(rx, text):
                s, e = m.span("w")
                while e > s and text[e - 1] in ".,;:":
                    e -= 1
                if e - s >= 2:
                    out.append(Finding(s, e, ent, 0.9, text[s:e], quelle="gelernt",
                                       grund=f"gelernte Regel: Wert nach „{r['wert']}“"))
        else:
            for m in re.finditer(rf"(?<![\w]){r['wert']}(?![\w])", text):
                out.append(Finding(m.start(), m.end(), ent, 0.9, m.group(), quelle="gelernt",
                                   grund=f"gelerntes Muster „{r.get('form', '')}“"))
    return out


# ------------------------------------------------------------------------------------------- Speicher
class Gedaechtnis:
    def __init__(self, home_fn):
        self._home_fn = home_fn
        self._lock = threading.RLock()

    @property
    def home(self) -> Path:
        return Path(self._home_fn())

    @property
    def pfad(self) -> Path:
        return self.home / DATEI

    def laden(self) -> dict:
        with self._lock:
            leer = {"version": 1, "faelle": {}, "angaben": [], "regeln": [], "vorgaenge": [], "loeschprotokoll": [],
                    "schluessel_genutzt": {}, "zaehler": {}, "aufgeraeumt": ""}
            if not self.pfad.exists():
                return leer
            daten = json.loads(tresor.entschluesseln(self.home, self.pfad.read_bytes()).decode("utf-8"))
            return {**leer, **daten}

    def speichern(self, daten: dict) -> None:
        with self._lock:
            self.home.mkdir(parents=True, exist_ok=True)
            roh = json.dumps(daten, ensure_ascii=False).encode("utf-8")
            tmp = self.pfad.with_suffix(".tmp")
            tmp.write_bytes(tresor.verschluesseln(self.home, roh))
            tmp.replace(self.pfad)

    @staticmethod
    def _neue_id(d: dict, art: str) -> str:
        n = d["zaehler"].get(art, 0) + 1
        d["zaehler"][art] = n
        return f"{art}{n}"

    # ----------------------------------------------------------------------------- Fälle
    def fall(self, d: dict, name: str, auto: bool = False) -> str:
        """Fall mit diesem Namen finden oder anlegen (gleiches Aktenzeichen → gleicher Fall)."""
        name = " ".join(name.split())[:80] or f"Vorgang vom {heute():%d.%m.%Y}"
        for f in d["faelle"].values():
            if f["name"].lower() == name.lower():
                return f["id"]
        fid = self._neue_id(d, "f")
        d["faelle"][fid] = {"id": fid, "nr": int(fid[1:]), "name": name, "auto": auto, "angelegt": heute().isoformat(),
                            "zuletzt": heute().isoformat(), "status": "offen", "verlaengert_bis": None,
                            "abgeschlossen_am": None}
        return fid

    def loeschdatum(self, f: dict, cfg: dict) -> date | None:
        fr = fristen(cfg)
        if f["status"] == "laeuft":
            return None
        if f["status"] == "abgeschlossen":
            return _plus_monate(_d(f["abgeschlossen_am"]) or heute(), int(fr["abgeschlossen_monate"]))
        basis = _plus_monate(_d(f["zuletzt"]) or heute(), int(fr["personen_monate"]))
        bis = _d(f.get("verlaengert_bis"))
        return max(basis, bis) if bis else basis

    def fall_aktion(self, fid: str, aktion: str, cfg: dict, monate: int = 0, name: str = "") -> dict:
        with self._lock:
            d = self.laden()
            f = d["faelle"].get(fid)
            if not f:
                raise ValueError("Diesen Fall gibt es nicht mehr.")
            if aktion == "verlaengern":
                if monate <= 0:
                    f["status"], f["abgeschlossen_am"] = "laeuft", None  # bis auf Widerruf: Mandat läuft
                else:
                    ab = max(self.loeschdatum(f, cfg) or heute(), heute())
                    f["verlaengert_bis"] = _plus_monate(ab, monate).isoformat()
                    if f["status"] == "abgeschlossen":
                        f["status"], f["abgeschlossen_am"] = "offen", None
            elif aktion == "abschliessen":
                f["status"], f["abgeschlossen_am"] = "abgeschlossen", heute().isoformat()
            elif aktion == "wieder_oeffnen":
                f["status"], f["abgeschlossen_am"] = "offen", None
            elif aktion == "umbenennen":
                neu = " ".join(name.split())[:80]
                if not neu:
                    raise ValueError("Bitte einen Namen für den Fall eingeben.")
                f["name"], f["auto"] = neu, False
            else:
                raise ValueError("Unbekannte Aktion.")
            self.speichern(d)
            return self.uebersicht(cfg)

    # ----------------------------------------------------------------------------- Lernen
    def merken(self, fall_name: str, eintraege: list[dict], vorgang_id: str = "") -> dict:
        """Am Ende eines Vorgangs bestätigte Angaben und Regeln speichern. eintraege: {"text", "art"} oder
        {"regel": {"art", "wert", "entity", "form"}}. Der Vorgang bekommt den bestätigten Fall."""
        with self._lock:
            d = self.laden()
            fid = self.fall(d, fall_name)
            d["faelle"][fid]["auto"] = False
            d["faelle"][fid]["zuletzt"] = heute().isoformat()
            n = 0
            for e in eintraege:
                if e.get("regel"):
                    r = e["regel"]
                    if not any(x["art"] == r["art"] and x["wert"].lower() == r["wert"].lower() for x in d["regeln"]):
                        d["regeln"].append({"id": self._neue_id(d, "r"), "art": r["art"], "wert": r["wert"],
                                            "form": r.get("form", ""), "entity": r.get("entity") or "KENNNUMMER",
                                            "gelernt": heute().isoformat()})
                        n += 1
                    continue
                text = " ".join(str(e.get("text", "")).split())
                if len(text) < 2:
                    continue
                a = next((x for x in d["angaben"] if x["text"].lower() == text.lower() and x["richtung"] == "ersetzen"),
                         None)
                if a is None:
                    a = {"id": self._neue_id(d, "a"), "text": text, "art": e.get("art") or "MANUELL",
                         "richtung": "ersetzen", "faelle": [], "gelernt": heute().isoformat(),
                         "zuletzt": heute().isoformat(), "herkunft": e.get("herkunft", "markiert")}
                    d["angaben"].append(a)
                    n += 1
                if a["art"] not in OHNE_PERSONENBEZUG and fid not in a["faelle"]:
                    a["faelle"].append(fid)
                a["zuletzt"] = heute().isoformat()
            for v in d["vorgaenge"]:
                if v["id"] == vorgang_id:
                    v["fall"] = fid
            self._leere_auto_faelle(d)
            self.speichern(d)
            return {"fall": fid, "neu": n}

    def stehen_lassen(self, begriffe: list[str]) -> None:
        """„Künftig immer stehen lassen“: kein Personenbezug zu speichern (meist Fachbegriffe), daher ohne Frist."""
        with self._lock:
            d = self.laden()
            for b in begriffe:
                b = " ".join(str(b).split())
                if len(b) >= 2 and not any(x["text"].lower() == b.lower() and x["richtung"] == "stehen"
                                           for x in d["angaben"]):
                    d["angaben"].append({"id": self._neue_id(d, "a"), "text": b, "art": "", "richtung": "stehen",
                                         "faelle": [], "gelernt": heute().isoformat(), "zuletzt": heute().isoformat(),
                                         "herkunft": "gegenrichtung"})
            self.speichern(d)

    def fuer_erkennung(self) -> dict:
        """Was die Erkennung braucht: Angaben zum Vorschlagen (mit Begründung), Begriffe zum Stehenlassen, Regeln."""
        d = self.laden()
        namen = {fid: f["name"] for fid, f in d["faelle"].items()}
        ersetzen = []
        for a in d["angaben"]:
            if a["richtung"] != "ersetzen":
                continue
            datum = _d(a["gelernt"])
            fall = namen.get(a["faelle"][0], "") if a["faelle"] else ""
            ersetzen.append({"id": a["id"], "text": a["text"], "art": a["art"],
                             "grund": f"von Ihnen gelernt am {datum:%d.%m.%Y}" + (f" · Fall {fall}" if fall else "")})
        return {"ersetzen": ersetzen, "stehen": [a["text"] for a in d["angaben"] if a["richtung"] == "stehen"],
                "regeln": d["regeln"]}

    def gefunden(self, angabe_ids: list[str], fall_name: str) -> None:
        """Gelernte Angaben kamen in einem anonymisierten Vorgang vor: Frist neu ab heute, Fall dazu."""
        if not angabe_ids:
            return
        with self._lock:
            d = self.laden()
            fid = self.fall(d, fall_name, auto=True)
            for a in d["angaben"]:
                if a["id"] in angabe_ids:
                    a["zuletzt"] = heute().isoformat()
                    if a["art"] not in OHNE_PERSONENBEZUG and fid not in a["faelle"]:
                        a["faelle"].append(fid)
            self.speichern(d)

    # ----------------------------------------------------------------------------- Vorgänge
    def vorgang_eintragen(self, name: str, fall_name: str, eintrag: dict, vid: str = "") -> str:
        """Neuer Eintrag, oder (erneut anonymisiert nach „Zurück zum Prüfen“) den bestehenden aktualisieren."""
        with self._lock:
            d = self.laden()
            fid = self.fall(d, fall_name, auto=True)
            d["faelle"][fid]["zuletzt"] = heute().isoformat()
            neu = {"name": name, "fall": fid, "zeit": datetime.now().isoformat(timespec="minutes"), **eintrag}
            alt = next((v for v in d["vorgaenge"] if v["id"] == vid), None) if vid else None
            if alt:
                alt.update(neu)
            else:
                vid = self._neue_id(d, "v")
                d["vorgaenge"].insert(0, {"id": vid, **neu})
            self._leere_auto_faelle(d)
            self.speichern(d)
            return vid

    def schluessel_genutzt(self, pfad: str) -> None:
        with self._lock:
            d = self.laden()
            d["schluessel_genutzt"][str(pfad)] = heute().isoformat()
            self.speichern(d)

    @staticmethod
    def _leere_auto_faelle(d: dict) -> None:
        """Automatisch angelegte Fälle ohne Vorgang und ohne Angabe verschwinden wieder."""
        belegt = {v["fall"] for v in d["vorgaenge"]} | {fid for a in d["angaben"] for fid in a["faelle"]}
        for fid in [fid for fid, f in d["faelle"].items() if f.get("auto") and fid not in belegt]:
            del d["faelle"][fid]

    # ----------------------------------------------------------------------------- Übersicht
    def uebersicht(self, cfg: dict) -> dict:
        d = self.laden()
        fr = fristen(cfg)
        h = heute()
        faelle = []
        for f in sorted(d["faelle"].values(), key=lambda f: f["zuletzt"], reverse=True):
            ld = self.loeschdatum(f, cfg)
            angaben = [{"id": a["id"], "text": a["text"], "art": a["art"], "gelernt": a["gelernt"],
                        "zuletzt": a["zuletzt"], "geteilt": len(a["faelle"]) > 1}
                       for a in d["angaben"] if f["id"] in a["faelle"]]
            vorgaenge = [v for v in d["vorgaenge"] if v["fall"] == f["id"]]
            faelle.append({**f, "loeschdatum": ld.isoformat() if ld else None, "angaben": angaben,
                           "vorgaenge": [{"id": v["id"], "name": v["name"], "zeit": v["zeit"]} for v in vorgaenge],
                           "warnung": bool(ld and (ld - h).days <= int(fr["warnen_tage"]))})
        ohne_fall = [{"id": a["id"], "text": a["text"], "art": a["art"], "gelernt": a["gelernt"],
                      "richtung": a["richtung"]} for a in d["angaben"] if not a["faelle"]]
        return {"faelle": faelle, "ohne_fall": ohne_fall, "regeln": d["regeln"],
                "vorgaenge": [{**v, "fall_name": d["faelle"].get(v["fall"], {}).get("name", "")}
                              for v in d["vorgaenge"]],
                "loeschprotokoll": list(reversed(d["loeschprotokoll"]))[:200], "fristen": fr,
                "hinweise": [f for f in faelle if f["warnung"] and f["loeschdatum"]]}

    def suche(self, q: str) -> dict:
        q = q.strip().lower()
        d = self.laden()
        if len(q) < 2:
            return {"angaben": [], "faelle": []}
        angaben = [a for a in d["angaben"] if q in a["text"].lower()]
        fids = {fid for a in angaben for fid in a["faelle"]} | {fid for fid, f in d["faelle"].items()
                                                              if q in f["name"].lower()}
        fids |= {v["fall"] for v in d["vorgaenge"] if q in v["name"].lower()}
        return {"angaben": [{"id": a["id"], "text": a["text"], "art": a["art"], "faelle": a["faelle"]} for a in angaben],
                "faelle": [{"id": fid, "name": d["faelle"][fid]["name"]} for fid in fids if fid in d["faelle"]]}

    def angabe_entfernen(self, aid: str) -> None:
        with self._lock:
            d = self.laden()
            d["angaben"] = [a for a in d["angaben"] if a["id"] != aid]
            d["regeln"] = [r for r in d["regeln"] if r["id"] != aid]
            self._protokolliere(d, "eine Angabe" if aid.startswith("a") else "eine Regel", {"angaben": 1}, "hand", 0)
            self._leere_auto_faelle(d)
            self.speichern(d)

    # ----------------------------------------------------------------------------- Löschen
    def _plan(self, d: dict, faelle: list[str], vorgaenge: list[str], name: str, grund: str) -> dict:
        fset = set(faelle)
        vs = [v for v in d["vorgaenge"] if v["fall"] in fset or v["id"] in vorgaenge]
        nur_vorgang = not fset
        if nur_vorgang:
            angaben, geteilt = [], 0
        else:
            angaben = [a for a in d["angaben"] if a["faelle"] and set(a["faelle"]) <= fset]
            geteilt = sum(1 for a in d["angaben"] if set(a["faelle"]) & fset and not set(a["faelle"]) <= fset)
        if name and grund == "mandant":
            q = name.lower()
            angaben += [a for a in d["angaben"] if q in a["text"].lower() and a not in angaben]
        def vorhanden(pfade):
            return [p for p in pfade if p and Path(p).exists()]
        schluessel = vorhanden([v.get("schluessel", "") for v in vs])
        ordner = vorhanden([v.get("vorgangsordner", "") for v in vs])
        tests = vorhanden([p for v in vs for p in v.get("testfaelle", [])])
        kopien = vorhanden([p for v in vs for p in v.get("kopien", [])])
        return {"vorgaenge": vs, "angaben": angaben, "geteilt": geteilt, "schluessel": schluessel,
                "vorgangsordner": ordner, "testfaelle": tests, "kopien": kopien}

    def vorschau(self, cfg: dict, faelle: list[str] | None = None, vorgaenge: list[str] | None = None,
                 name: str = "", offene_vorgaenge: list[str] | None = None) -> dict:
        d = self.laden()
        faelle, vorgaenge = list(faelle or []), list(vorgaenge or [])
        if name:
            faelle += [f["id"] for f in self.suche(name)["faelle"] if f["id"] not in faelle]
        p = self._plan(d, faelle, vorgaenge, name, "mandant" if name else "")
        warnungen = []
        for fid in faelle:
            f = d["faelle"].get(fid)
            if f and f["status"] == "laeuft":
                warnungen.append(f"Fall {f['name']} ist als „Mandat läuft“ markiert.")
        grenze = (heute() - timedelta(days=14)).isoformat()
        for s in p["schluessel"]:
            if d["schluessel_genutzt"].get(s, "") >= grenze:
                warnungen.append("Ein Schlüssel dieses Falls wurde in den letzten 14 Tagen für eine Rückübersetzung "
                                 "benutzt.")
                break
        if set(offene_vorgaenge or []) & {v["id"] for v in p["vorgaenge"]}:
            warnungen.append("Ein Vorgang dieses Falls ist gerade geöffnet. Er wird beim Löschen geschlossen.")
        kopien_ordner = sorted({str(Path(k).parent) for k in p["kopien"]})
        return {"faelle": [{"id": fid, "name": d["faelle"][fid]["name"]} for fid in faelle if fid in d["faelle"]],
                "vorgaenge": [{"id": v["id"], "name": v["name"]} for v in p["vorgaenge"]],
                "anzahl": {"angaben": len(p["angaben"]), "geteilt": p["geteilt"], "schluessel": len(p["schluessel"]),
                           "vorgangsordner": len(p["vorgangsordner"]), "testfaelle": len(p["testfaelle"]),
                           "kopien": len(p["kopien"])},
                "kopien_ordner": kopien_ordner, "warnungen": warnungen,
                "vorgangsordner_aus": not any(v.get("vorgangsordner") for v in p["vorgaenge"])}

    def loeschen(self, cfg: dict, faelle: list[str] | None = None, vorgaenge: list[str] | None = None, name: str = "",
                 grund: str = "hand", kopien: bool = False, auswahl: dict | None = None) -> dict:
        """Löscht, was die Vorschau gezeigt hat. Bei „Wunsch des Mandanten“ immer alles mit Personendaten; sonst
        lässt sich über auswahl ({"angaben": False, …}) einzelnes behalten."""
        if grund not in GRUENDE:
            raise ValueError("Unbekannter Grund.")
        auswahl = {k: True for k in ("angaben", "schluessel", "vorgangsordner", "testfaelle")} | (auswahl or {})
        if grund == "mandant":
            auswahl = {k: True for k in auswahl}
        with self._lock:
            d = self.laden()
            faelle, vorgaenge = list(faelle or []), list(vorgaenge or [])
            if name:
                faelle += [f["id"] for f in self.suche(name)["faelle"] if f["id"] not in faelle]
            p = self._plan(d, faelle, vorgaenge, name, grund)
            geloescht = {k: 0 for k in ("angaben", "schluessel", "vorgangsordner", "testfaelle", "kopien")}
            fehler = []

            def weg(art: str, pfad: str, papierkorb: bool = False) -> None:
                try:
                    q = Path(pfad)
                    if q.is_dir():
                        shutil.rmtree(q)
                    elif papierkorb:
                        tresor.papierkorb(q)
                    else:
                        q.unlink()
                    geloescht[art] += 1
                except FileNotFoundError:
                    pass
                except OSError as e:
                    fehler.append({"art": art, "pfad": pfad, "grund": str(e)})

            for art in ("schluessel", "vorgangsordner", "testfaelle"):
                if auswahl.get(art):
                    for q in p[art]:
                        weg(art, q)
            if kopien:
                for q in p["kopien"]:
                    weg("kopien", q, papierkorb=True)
            if auswahl.get("angaben"):
                ids = {a["id"] for a in p["angaben"]}
                geloescht["angaben"] = len(ids)
                d["angaben"] = [a for a in d["angaben"] if a["id"] not in ids]
            fset = set(faelle)
            for a in d["angaben"]:
                a["faelle"] = [x for x in a["faelle"] if x not in fset]
            vids = {v["id"] for v in p["vorgaenge"]}
            d["vorgaenge"] = [v for v in d["vorgaenge"] if v["id"] not in vids]
            for fid in fset:
                d["faelle"].pop(fid, None)
            self._leere_auto_faelle(d)
            was = (f"{len(fset)} Fall" if len(fset) == 1 else f"{len(fset)} Fälle") if fset else \
                (f"{len(vids)} Vorgang" if len(vids) == 1 else f"{len(vids)} Vorgänge")
            nr = self._protokolliere(d, was, geloescht, grund, len(fehler))
            self.speichern(d)
            return {"geloescht": geloescht, "fehler": fehler, "vorgaenge": sorted(vids), "protokoll_nr": nr}

    def _protokolliere(self, d: dict, was: str, geloescht: dict, grund: str, fehler: int) -> str:
        nr = f"L-{len(d['loeschprotokoll']) + 1}"
        d["loeschprotokoll"].append({"nr": nr, "zeit": datetime.now().isoformat(timespec="minutes"), "was": was,
                                     "anzahl": {k: v for k, v in geloescht.items() if v}, "grund": GRUENDE.get(grund, grund),
                                     "nicht_geloescht": fehler})
        return nr

    def aufraeumen(self, cfg: dict) -> dict:
        """Abgelaufene Fälle löschen (einmal am Tag, beim Start). Kopien bleiben; sie enthalten keine Namen."""
        d = self.laden()
        if d.get("aufgeraeumt") == heute().isoformat():
            return {"faelle": 0}
        abgelaufen = [fid for fid, f in d["faelle"].items()
                      if (ld := self.loeschdatum(f, cfg)) is not None and ld < heute()]
        r = {"faelle": len(abgelaufen)}
        if abgelaufen:
            r.update(self.loeschen(cfg, faelle=abgelaufen, grund="frist"))
        d = self.laden()
        d["aufgeraeumt"] = heute().isoformat()
        self.speichern(d)
        return r

    def nachweis_html(self, nr: str) -> str:
        """Löschbestätigung ohne Namen, für die Akte oder den Mandanten."""
        import html as _h

        d = self.laden()
        e = next((x for x in d["loeschprotokoll"] if x["nr"] == nr), None)
        if not e:
            raise ValueError("Diesen Eintrag gibt es im Löschprotokoll nicht.")
        namen = {"angaben": "Gelernte Angaben", "schluessel": "Schlüssel für die Rückübersetzung",
                 "vorgangsordner": "Vorgangsordner mit Prüfbericht und Kopie der Originale",
                 "testfaelle": "Eigene Testfälle", "kopien": "Anonymisierte Kopien (Papierkorb)"}
        zeilen = "".join(f"<tr><td>{_h.escape(namen.get(k, k))}</td><td>{v}</td></tr>" for k, v in e["anzahl"].items())
        zeit = datetime.fromisoformat(e["zeit"])
        return (f"<!doctype html><html lang='de'><meta charset='utf-8'><title>Löschbestätigung {e['nr']}</title>"
                "<style>body{font:15px/1.5 'Segoe UI',system-ui,sans-serif;max-width:640px;margin:40px auto;color:#1a1a1a}"
                "table{border-collapse:collapse;width:100%}td{border-bottom:1px solid #ddd;padding:6px 0}"
                "small{color:#5c5c5c}</style>"
                f"<h1>Löschbestätigung {e['nr']}</h1><p>Am {zeit:%d.%m.%Y} um {zeit:%H:%M} Uhr hat Lokanon auf diesem PC "
                f"Folgendes gelöscht ({_h.escape(e['was'])}). Grund: {_h.escape(e['grund'])}.</p>"
                f"<table>{zeilen or '<tr><td>Keine Daten vorhanden</td><td></td></tr>'}</table>"
                + (f"<p>{e['nicht_geloescht']} Dateien ließen sich nicht löschen.</p>" if e["nicht_geloescht"] else "")
                + "<p><small>Die Originaldateien verändert Lokanon nie. Das Protokoll ohne Namen löscht sich nach 30 Tagen. "
                  "Diese Bestätigung enthält bewusst keine Namen.</small></p></html>")

    # ----------------------------------------------------------------------------- Übernahme aus 0.3.0
    def uebernehmen(self, cfg: dict) -> bool:
        """Gelernte Begriffe aus einstellungen.yaml (bis 0.3.0, Klartext) übernehmen und dort entfernen."""
        alt = cfg.get("gelernt") or {}
        if not any(alt.get(k) for k in ("stehen_lassen", "immer_ersetzen")):
            if "gelernt" in cfg:
                cfg.pop("gelernt")
                return True
            return False
        stehen = [g["begriff"] for g in alt.get("stehen_lassen", []) if isinstance(g, dict) and g.get("begriff")]
        ersetzen = [g["begriff"] for g in alt.get("immer_ersetzen", []) if isinstance(g, dict) and g.get("begriff")]
        if stehen:
            self.stehen_lassen(stehen)
        if ersetzen:
            self.merken("Übernommen aus Lokanon 0.3.0", [{"text": b, "art": "MANUELL", "herkunft": "uebernommen"}
                                                          for b in ersetzen])
        cfg.pop("gelernt")
        return True
