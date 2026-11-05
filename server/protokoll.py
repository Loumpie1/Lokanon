"""Fehlerprotokoll je Durchlauf, ohne Klartext.

Ins Protokoll kommen Ablauf, Zahlen und Fehler, damit sich nachvollziehen lässt, was passiert ist: welche Datei (als
„Datei 2 (.pdf)“), wie viele Seiten und Treffer je Art, welche Stufe gescheitert ist und wo die Gegenprüfung noch
etwas fand. Erkannte Originale werden vor dem Schreiben durch ihren Platzhalter ersetzt, Dateinamen durch ihre
Nummer und der gewählte Ordner durch „<Ordner>“. So kann man das Protokoll weitergeben, ohne Personendaten
mitzugeben.

Ablage: <Datenordner>/protokolle/JJJJ-MM-TT.log, eine Zeile je Eintrag; Dateien älter als 30 Tage werden gelöscht.
"""
from __future__ import annotations

import re
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

AUFBEWAHREN_TAGE = 30


class Protokoll:
    def __init__(self, ordner_fn):
        self._ordner_fn = ordner_fn
        self._lock = threading.Lock()
        self.lauf = ""
        self.eintraege: list[dict] = []
        self._ersatz: list[tuple[re.Pattern, str]] = []

    @property
    def ordner(self) -> Path:
        p = Path(self._ordner_fn()) / "protokolle"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def neuer_lauf(self, art: str, dateinamen: list[str], ordner: str = "", neu: bool = True) -> None:
        """Beginnt einen Abschnitt (Analyse oder Anonymisieren). Dateinamen und Ordner werden ab jetzt ersetzt.
        neu=False (Anonymisieren): Die Einträge der Analyse bleiben in der Anzeige stehen."""
        if neu or not self.lauf:
            self.lauf = datetime.now().strftime("%H%M%S")
            self.eintraege = []
        self._ersatz = []
        self.geheimnisse([(n, f"Datei {i + 1} (.{n.rsplit('.', 1)[-1].lower()})") for i, n in enumerate(dateinamen)])
        if ordner:
            self.geheimnisse([(ordner, "<Ordner>")])
        self._aufraeumen()
        self.notiere("info", f"{art} gestartet")

    def geheimnisse(self, paare: list[tuple[str, str]]) -> None:
        """Texte, die nie im Protokoll stehen dürfen, mit ihrem Ersatz. Längste zuerst."""
        neu = [(re.compile(re.escape(o.strip()), re.IGNORECASE), e) for o, e in paare if o and len(o.strip()) >= 2]
        self._ersatz = sorted(self._ersatz + neu, key=lambda t: -len(t[0].pattern))

    def schwaerzen(self, text: str) -> str:
        for rx, e in self._ersatz:
            text = rx.sub(e, text)
        return text

    def notiere(self, stufe: str, text: str) -> None:
        """stufe: info | warnung | fehler"""
        e = {"zeit": datetime.now().strftime("%H:%M:%S"), "stufe": stufe, "text": self.schwaerzen(text)}
        with self._lock:
            self.eintraege.append(e)
            try:
                with open(self.ordner / f"{datetime.now():%Y-%m-%d}.log", "a", encoding="utf-8") as fh:
                    fh.write(f"{e['zeit']} lauf={self.lauf} [{stufe}] {e['text']}\n")
            except OSError:
                pass  # Protokoll darf die Arbeit nie aufhalten

    def ausnahme(self, wo: str, exc: BaseException) -> None:
        """Fehler mit Art, Meldung und den Code-Stellen (Datei:Zeile, ohne Variablenwerte)."""
        stellen = [f"{Path(fr.filename).name}:{fr.lineno} {fr.name}" for fr in traceback.extract_tb(exc.__traceback__)]
        self.notiere("fehler", f"{wo}: {type(exc).__name__}: {exc}" + (f" | Stellen: {' > '.join(stellen[-6:])}"
                                                                        if stellen else ""))

    def _aufraeumen(self) -> None:
        grenze = time.time() - AUFBEWAHREN_TAGE * 86400
        try:
            for p in self.ordner.glob("*.log"):
                if p.stat().st_mtime < grenze:
                    p.unlink()
        except OSError:
            pass
