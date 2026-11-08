# Hilfe-Inventar: Funktion → Anker → Tour → Hilfetext → Anleitung

Stand 08.11.2026 (0.4.0). Regel: [entwicklung/hilfe-mitpflegen.md](entwicklung/hilfe-mitpflegen.md).
`tests/test_hilfe.py` liest diese Tabelle: Jeder `data-tour`-Anker in `ui/app.js`, den das Drehbuch nicht benutzt,
muss hier mit „ohne Tour“ stehen. Kapitel der Einführung: ablegen, pruefen, markieren, anonymisieren, merken, faelle,
gespeichert (`ui/einfuehrung/drehbuch.js`).

## Anker in der Einführung

| Anker | Funktion | Tour | Hilfetext | Anleitung |
|---|---|---|---|---|
| `nav-start` | Startseite | ablegen | – | #ablauf |
| `neu-dateien` | Dateien hinzufügen | ablegen | – | #ablauf |
| `neu-ordner` | Ordner öffnen | ablegen | – | #ablauf |
| `fristen` | Fälle und Fristen auf der Startseite | ablegen | frist | #gespeichert |
| `pruefen-kopf` | Zusammenfassung, Fall | pruefen | fall | #pruefen |
| `hinweis-ansehen` | Bitte ansehen | pruefen | – | #pruefen |
| `zeile` | Zeile einer Angabe | pruefen | stehen_lassen | #pruefen |
| `dokument` | Dokument mit Markierungen, Fähnchen | pruefen, markieren | – | #pruefen |
| `platzhalter-vorschlaege` | Platzhalter ändern | pruefen | – | #pruefen |
| `befehl-markieren` | Übersehenes markieren | markieren | markieren | #markieren |
| `markierfenster` | Fenster an der Auswahl | markieren | – | #markieren |
| `markier-ueberall` | Überall ersetzen | markieren | – | #markieren |
| `befehl-rueckgaengig` | Rückgängig | markieren | – | #markieren |
| `nachtrag` | Begriff eintragen | markieren | markieren | #markieren |
| `befehl-anonymisieren` | Anonymisieren mit Zähler | anonymisieren | – | #ausgabe |
| `ergebnis-dateien` | Ergebnis, Gegenprüfung | anonymisieren | – | #ausgabe |
| `befehl-ki` | KI-Anweisung | anonymisieren | – | #ki |
| `befehl-zurueck` | Antwort zurückübersetzen | anonymisieren | – | #erweitert |
| `merken` | Frage „künftig vorschlagen?“ | merken | speichern_warum | #gespeichert |
| `merken-fall` | Fall bestätigen | merken | fall | #gespeichert |
| `merken-liste` | Angaben, Regeln, Fristen | merken | regel | #gespeichert |
| `merken-warum` | „Warum?“ | merken | speichern_warum | #gespeichert |
| `merken-ok` | Merken | merken | – | #gespeichert |
| `nav-faelle` | Fälle und gelernte Angaben | faelle, gespeichert | speichern | #gespeichert |
| `faelle` | Liste der Fälle | faelle | fall | #gespeichert |
| `fall` | ein Fall | gespeichert | fall, frist | #gespeichert |
| `fall-verlaengern` | Verlängern | gespeichert | verlaengern | #gespeichert |
| `verlaengern-widerruf` | Bis auf Widerruf | gespeichert | verlaengern | #gespeichert |
| `fall-abschliessen` | Fall abgeschlossen | gespeichert | abschliessen | #gespeichert |
| `fristhinweis` | Hinweis vor dem Löschen | gespeichert | frist | #gespeichert |
| `suche` | Namen oder Fall suchen | gespeichert | – | #gespeichert |
| `ueberall-loeschen` | Überall löschen | gespeichert | ueberall_loeschen | #gespeichert |
| `loeschdialog` | Löschen mit Vorschau | gespeichert | originale_bleiben, protokoll_bleibt, ki_kopien | #gespeichert |
| `loeschen-ok` | Endgültig löschen | gespeichert | – | #gespeichert |
| `nachweis-oeffnen` | Löschbestätigung | gespeichert | loeschprotokoll | #gespeichert |
| `loeschprotokoll` | Löschprotokoll | faelle | loeschprotokoll | #gespeichert |
| `nav-einstellungen` | Einstellungen | faelle | – | #einstellungen |
| `aufbewahrung` | Aufbewahrung und Fristen | faelle | aufbewahrung, handakte, sicherung, verschluesselt | #gespeichert |

## Anker ohne Tour

| Anker | Funktion | Grund | Hilfetext | Anleitung |
|---|---|---|---|---|
| `befehlsleiste` | Befehlsleiste | ohne Tour: Rahmen, in jedem Kapitel sichtbar | – | – |
| `hilfe-menue` | ?-Menü mit Einführung und Kapiteln | ohne Tour: Schlussschritt nennt es | – | #hilfe |
| `menue-einfuehrung` | Eintrag „Einführung starten“ | ohne Tour: Einstieg selbst | – | #hilfe |
| `uebung-band` | Band „Übungsvorgang“ | ohne Tour: erklärt sich während der Tour | – | – |
| `nav-vorgang` | Aktueller Vorgang | ohne Tour: Tour wechselt selbst dorthin | – | #ablauf |
| `nav-protokoll` | Protokoll | ohne Tour: Fehlersuche, nicht Alltag | protokoll_bleibt | #hilfe |
| `nav-einfuehrung` | Einführung | ohne Tour: Einstieg selbst | – | #hilfe |
| `befehl-dateien` | Dateien hinzufügen (Befehlsleiste) | ohne Tour: gleich wie neu-dateien | – | #ablauf |
| `neu-text` | Text einfügen | ohne Tour: Variante von neu-dateien | – | #ablauf |
| `start-einfuehrung` | Link „Einführung starten“ | ohne Tour: Einstieg selbst | – | – |
| `zuletzt` | Zuletzt bearbeitet, Auswahl löschen | ohne Tour: Löschen zeigt Kapitel 7 an den Fällen | – | #gespeichert |
| `reiter` | Dateireiter | ohne Tour: selbsterklärend | – | #pruefen |
| `docview` | Seite im Dokument | ohne Tour: Tour zeigt den ganzen Dokumentbereich | – | #pruefen |
| `pruefbereich` | Prüfbereich rechts | ohne Tour: Tour zeigt Kopf und Zeilen | – | #pruefen |
| `fallzeile` | Fall im Prüfbereich ändern | ohne Tour: im Schritt „Was Lokanon gefunden hat“ erwähnt | fall | #gespeichert |
| `filter` | Filter nach Art | ohne Tour: selbsterklärend | – | #pruefen |
| `markier-arten` | Art im Markierfenster | ohne Tour: Teil des Markierfensters | – | #markieren |
| `zeile-schalter` | Haken einer Zeile | ohne Tour: Tour bedient ihn über die Zeile | – | #pruefen |
| `suchergebnis` | Ergebnis der Suche | ohne Tour: Teil des Schritts „Überall löschen“ | – | #gespeichert |
| `fall-loeschen` | Fall löschen | ohne Tour: Tour zeigt Löschen über die Suche | ueberall_loeschen | #gespeichert |
| `nachweis` | Nachweis im Löschprotokoll | ohne Tour: wie nachweis-oeffnen | loeschprotokoll | #gespeichert |
