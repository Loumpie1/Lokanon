"""Wörterbuch-Prüfung: Ist ein vorgeschlagener Name ein gewöhnliches deutsches Wort?

Statt immer längerer Stopplisten ("Gesamtbrutto", "Ferienregelung", "Gespräch" …) wird gegen Wortlisten aus Wiktionary
geprüft (anonymizer/daten, CC BY-SA 4.0). Zusammengesetzte Wörter werden zerlegt ("Ferien|regelung"). Wörter, die auch
Vor- oder Nachnamen sind ("Fischer", "Koch", "Engel"), gelten nie als gewöhnlich – dort entscheidet weiter das Modell.
"""
from __future__ import annotations

import gzip
from functools import lru_cache
from pathlib import Path

DATEN = Path(__file__).resolve().parent / "daten"

# Typische Enden deutscher Familiennamen: so endende Zusammensetzungen ("Lindemann", "Rosenbaum") nicht als
# gewöhnliches Wort werten
NAMENSENDEN = ("mann", "berg", "baum", "feld", "stein", "hof", "hoff", "bach", "burg", "dorf", "haus", "hausen", "meier",
               "meyer", "maier", "mayer", "kamp", "brink", "beck", "horst", "wald", "thal", "tal", "bruch", "heim",
               "rath", "kötter", "mund", "schmidt", "schmitz", "berger", "bauer", "müller", "möller", "brock", "busch",
               "kemper", "winkel", "hagen", "felder", "wiese", "lohe", "loh", "kotte", "ing", "inger", "ski", "sky",
               "herr", "stern", "hammer", "schläger")
_FUGEN = ("", "s", "es", "n", "en", "er", "e")


@lru_cache(maxsize=None)
def _liste(name: str) -> frozenset[str]:
    p = DATEN / f"{name}.txt.gz"
    if not p.exists():
        return frozenset()
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        return frozenset(z.strip() for z in fh if z.strip())


def ist_vorname(w: str) -> bool:
    return w in _liste("vornamen")


def ist_nachname(w: str) -> bool:
    return w in _liste("nachnamen")


def ist_name(w: str) -> bool:
    return ist_vorname(w) or ist_nachname(w)


def _einfach(w: str) -> bool:
    """Substantiv (großgeschrieben) oder Adjektiv/Partizip (kleingeschrieben) aus der Liste."""
    if (w[:1].upper() + w[1:]) in _liste("substantive"):
        return True
    low = w.lower()
    # Adjektiv/Partizip, auch gebeugt ("weitergeleitete" zu "weitergeleitet")
    return low in _liste("adjektive") or any(low.endswith(e) and low[:-len(e)] in _liste("adjektive")
                                             for e in ("e", "en", "er", "es", "em"))


@lru_cache(maxsize=20000)
def ist_wort(w: str) -> bool:
    """Gewöhnliches deutsches Wort, auch zusammengesetzt ("Ferienregelung", "Familienpsychologisches")."""
    w = w.strip(".,:;()\"'„“")
    if len(w) < 2 or not w.replace("-", "").isalpha():
        return False
    if "-" in w:  # "SV-Brutto", "AN-Anteil": letzter Teil entscheidet, Abkürzungen davor zählen nicht
        teile = [t for t in w.split("-") if t]
        return bool(teile) and ist_wort(teile[-1]) and all(t.isupper() or ist_wort(t) for t in teile[:-1])
    if _einfach(w):
        return True
    if len(w) < 9 or w.lower().endswith(NAMENSENDEN):  # "Rehbein", "Lindemann" bleiben Namen
        return False
    low = w.lower()
    for i in range(3, len(w) - 2):
        kopf, rest = low[:i], low[i:]
        if not _einfach(rest) and not (len(rest) >= 7 and ist_wort(rest)):
            continue
        for fuge in _FUGEN:
            if kopf.endswith(fuge) and len(kopf) - len(fuge) >= 3 and _einfach(kopf[:len(kopf) - len(fuge)]):
                return True
    return False


def gewoehnlich(w: str) -> bool:
    """Gewöhnliches Wort und kein bekannter Vor- oder Nachname."""
    w = w.strip(".,:;()\"'„“")
    return ist_wort(w) and not ist_name(w) and not ist_name(w.rstrip("s"))
