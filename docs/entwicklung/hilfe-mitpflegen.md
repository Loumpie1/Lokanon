# Regel: Hilfe und Tour wachsen mit jeder Änderung mit

Festgelegt am 08.11.2026. Gilt für jede Weiterentwicklung an Oberfläche oder Verhalten von Lokanon.

## Grundsatz

Eine Funktion ist erst fertig, wenn sie erklärt ist. Wer etwas baut oder ändert, das der Anwender sieht oder
bedient, passt **im selben Commit** an:

1. **Drehbuch der Tour** (`ui/einfuehrung/drehbuch.js`): betroffene Schritte, Texte, Anker; neue Funktion bekommt
   einen Schritt mit `seit: "<Version>"`.
2. **Hilfetexte** (`ui/einfuehrung/hilfetexte.js`): Kurzbegründungen und Kontexthilfe (i).
3. **Anleitung** (`static/anleitung/index.html`): Abschnitt und Link „Im Programm zeigen“.
4. **Release-Notiz** (`docs/pilot/Neu-in-<Version>.md`): ein Punkt je sichtbarer Änderung.

Betrifft eine Änderung die Hilfe nicht (reine Erkennung, interne Umbauten), steht das ausdrücklich in der
Commit-Nachricht: `Hilfe: nicht betroffen`.

## Die vier Quellen und wer was nutzt

| Quelle | Inhalt | Genutzt von |
|---|---|---|
| `ui/einfuehrung/drehbuch.js` | Kapitel, Schritte, Ziele (`data-tour`), Wartebedingungen, `seit` | Tour, Tour „Neu in …“, Tour-Test |
| `ui/einfuehrung/hilfetexte.js` | Kurzbegründungen, Kontexthilfe, „Mehr dazu“ | (i)-Hilfe, Abschlussfenster, Tour, Anleitung (beim Build eingesetzt) |
| `static/anleitung/index.html` | ausführliche Anleitung, FAQ | ?-Menü, Direktlinks |
| `docs/hilfe-inventar.md` | Tabelle: Funktion → `data-tour`-Anker → Tour-Schritt → Hilfetext → Anleitungsabschnitt | Entwickler, Review |

Texte stehen nur an **einer** Stelle. Tour und Anleitung verweisen auf `hilfetexte.js`, statt Sätze zu kopieren.

## Automatische Wächter

| Wächter | Was er prüft | Wo |
|---|---|---|
| Anker-Test (ohne Browser) | Jeder `ziel`-Anker im Drehbuch kommt in `ui/app.js` vor. Jeder `data-tour`-Anker in `ui/app.js` ist im Drehbuch oder im Inventar als „ohne Tour“ geführt. | `tests/test_hilfe.py`, läuft mit `pytest` |
| Hilfetext-Test | Jeder Schlüssel, den Drehbuch, App oder Anleitung nutzen, steht in `hilfetexte.js`, und kein Text ist ungenutzt. | `tests/test_hilfe.py` |
| Tour-Test (Browser) | Spielt jedes Kapitel in der Übungssitzung mit „Zeig es mir“ durch. Jedes Ziel ist sichtbar, jede Wartebedingung tritt ein, danach sind echte Daten unverändert. | `tests/tour_durchspielen.py`, vor jedem Release |
| Release-Prüfung | `build.py` bricht ab, wenn `Neu-in-<Version>.md` Funktionen nennt, für die das Drehbuch keinen Schritt mit `seit: "<Version>"` hat, oder wenn der Tour-Test nicht grün ist. | `build/build.py` |

## Ablauf bei jeder Änderung

1. **Vor dem Bauen:** In der Anforderung steht ein Abschnitt „Hilfe und Tour“: Welche Schritte ändern sich? Braucht es
   einen neuen Schritt oder eine Begründung? Neue Anforderungen ohne diesen Abschnitt gelten als unvollständig.
2. **Beim Bauen:** neue Bedienelemente bekommen gleich einen `data-tour`-Anker; Texte in `hilfetexte.js`.
3. **Vor dem Commit:** `pytest` (Anker- und Hilfetext-Test) grün; Inventar aktualisiert.
4. **Vor dem Release:** Tour-Test im Browser; Tour „Neu in …“ einmal selbst ansehen; Anleitung und Release-Notiz
   gegenlesen.

## Einführung der Regel

Die Wächter entstehen zusammen mit der Tour (Schritt 7 der Reihenfolge in
[lernen-und-loeschfristen.md](../anforderungen/lernen-und-loeschfristen.md)). Bis dahin gilt die Regel für Anforderungen
und Release-Notizen: Jede neue Anforderung beschreibt, wie die Funktion in Tour und Hilfe erklärt wird.
