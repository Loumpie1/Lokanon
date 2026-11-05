# Anforderung: Übersehenes im Dokument markieren und im Rest suchen

Aufgenommen am 04.11.2026. Umsetzung im Build **nach** der Erkennungsoptimierung, zusammen mit den UI-Punkten:
- Rückweg von „Fertig“
- Fehlerprotokoll
- Layout der Prüfen-Ansicht
- Klick → Stelle
- Dokumentbereich ausblendbar

## Ziel

Lokanon übersieht etwas. Die Nutzerin markiert die Stelle direkt im Dokument und legt fest, dass sie anonymisiert wird.
Lokanon fragt dann, ob es den Rest des Dokuments oder des ganzen Vorgangs nach derselben Angabe durchsuchen soll,
zeigt die Fundstellen und wendet sie nach Bestätigung an.

## Ablauf aus Sicht der Nutzerin

1. Im Schritt „Prüfen“ öffnet sie die Dokumentvorschau und markiert mit der Maus „Spedition Nolte“.
2. Neben der Markierung erscheint eine kleine Leiste mit der Frage „Anonymisieren als …“.
   - Lokanon schlägt die Art vor, hier Firma, weil „Spedition“ davorsteht.
   - Andere Arten stehen zur Auswahl, ebenso „gehört zu …“ für eine schon erkannte Identität.
3. Sie bestätigt. Darauf fragt Lokanon:
   „Spedition Nolte“ kommt noch 6-mal vor: 4-mal in diesem Dokument, 2-mal in „Schreiben_Gegenseite.pdf“.
   Auch dort anonymisieren? **[Alle anwenden] [Einzeln ansehen] [Nur hier]**
4. Bei „Einzeln ansehen“ erscheint eine Liste aller Fundstellen mit Satzausschnitt. Alle sind vorausgewählt und
   einzeln abwählbar. Ein Klick auf eine Fundstelle springt in der Vorschau dorthin.
5. Danach gibt es eine neue Karte [Firma_3] mit allen Stellen, und die Vorschau zeigt den Platzhalter.
6. Unter der Rückfrage steht der Haken „künftig in allen Dokumenten suchen“. Damit wird der Begriff gelernt, wie
   heute schon beim Nachtragen.

## Funktionale Anforderungen

**M1 – Dokumentvorschau**
- Jedes Dokument des Vorgangs wird lesbar angezeigt:
  - PDF als Seitenbild mit darüberliegender, unsichtbarer Textebene
  - Scans mit den Wortpositionen aus der Texterkennung
  - DOCX, TXT und XLSX als formatierter Text bzw. Tabelle
- Erkannte Stellen sind farbig hinterlegt, mit einer Farbe je Art.
- Ein Klick auf eine Karte springt zur Stelle, ein Klick auf eine Stelle springt zur Karte. Das deckt auch den offenen
  UI-Punkt „Klick → Stelle“ ab.

**M2 – Markieren**
- Markiert werden kann per Maus (Ziehen oder Doppelklick auf ein Wort) und per Tastatur (Umschalt + Pfeiltasten).
- Die Auswahl wird an Wortgrenzen ausgerichtet. Zeichengenau nur, wenn die Nutzerin bewusst ein Wortteil markiert,
  etwa bei „Nolte-Logistik“.
- Mehrzeilige Auswahl ist erlaubt, etwa für Anschriften über zwei Zeilen.
- Bei Scans bezieht sich die Auswahl auf die Wörter aus der Texterkennung.

**M3 – Art und Zuordnung**
- Lokanon schlägt die Art aus Kontext und Form vor:
  - Anrede davor → Person
  - Rechtsform oder Branchenwort → Firma
  - Ziffernmuster → passende Nummernart
- „Gehört zu“ ordnet die Stelle einer bestehenden Identität zu. Beispiel: „Frau Dr. B.“ zu [Person_2] bekommt
  denselben Platzhalter.

**M4 – Suchen im Rest.** Den Umfang wählt die Nutzerin: dieses Dokument oder ganzer Vorgang (Voreinstellung).
Gesucht wird nach:
- dem exakten Begriff, ohne Rücksicht auf Groß- und Kleinschreibung und nur an Wortgrenzen. „Nolte“ trifft also
  nicht „Noltenbach“.
- Beugungen: „Noltes“, „der Nolte’schen“.
- Silbentrennung und Zeilenumbruch: „Spedi-|tion Nolte“ im PDF.
- Ligaturen und Leerraum-Varianten, wie heute schon bei der Leck-Prüfung.
- Namensteilen bei Personen, wie heute bei `include_name_parts`. Markiert die Nutzerin „Moritz Günther“, werden
  „Günther“ und „Herrn Günther“ als eigene, abwählbare Gruppe angeboten.

Fundstellen, die schon zu einem anderen Treffer gehören, werden angezeigt, aber nicht doppelt angelegt. Ein Hinweis
nennt den bisherigen Platzhalter und bietet „hierher übernehmen“ an.

**M5 – Rückfrage und Anwenden**
- Die Rückfrage nennt die Anzahl je Dokument.
- „Alle anwenden“ wirkt sofort.
- „Einzeln ansehen“ zeigt die Liste aus Schritt 4 des Ablaufs.
- Bei mehr als 50 Fundstellen warnt Lokanon, weil der Begriff wahrscheinlich zu allgemein ist, etwa „Bank“.

**M6 – Rückgängig**
- Jede manuelle Aktion lässt sich mit einem Schritt zurücknehmen, auch „Alle anwenden“.
- Strg+Z und ein Toast mit „Rückgängig“.

**M7 – Gegenrichtung (Fehlalarm per Markierung).** Ein Klick auf eine hinterlegte Stelle zeigt „Nicht anonymisieren“
mit denselben Optionen: nur hier / im ganzen Vorgang / künftig immer stehen lassen.

**M8 – Begründung.** Manuell markierte Stellen tragen die Begründung „von Ihnen markiert“, übernommene Fundstellen
„wie von Ihnen markiert“. Das erscheint auf der Karte.

**M9 – Ausgabe und Prüfung.** Manuelle Stellen laufen durch dieselbe Pipeline wie erkannte:
- Platzhalter-Vergabe
- PDF-Schwärzung
- Leck-Test, der auch alle manuell markierten Begriffe prüft
- Rückübersetzung

**M10 – Lernen**
- Mit dem Haken „künftig in allen Dokumenten suchen“ landet der Begriff unter Einstellungen → Gelernte Begriffe
  (`immer_ersetzen`).
- Ohne Haken gilt er nur für diesen Vorgang.

## Nicht-funktionale Anforderungen

- **Tempo:** Die Suche im ganzen Vorgang dauert unter 1 Sekunde bei 50 Seiten. Es ist reine Textsuche, kein Modell.
- **Datenschutz:** Markierte Begriffe bleiben im Vorgang und werden nur mit Haken in den Einstellungen gespeichert.
  Protokolle enthalten keine Klartexte.
- **Bedienbarkeit:** Alles ist auch per Tastatur erreichbar. Farben haben zusätzlich ein Muster oder Symbol, damit sie
  bei Farbschwäche unterscheidbar sind.

## Abnahmekriterien

1. Im Testvorgang (Schriftsatz als PDF, E-Mail als TXT, Lohnabrechnung als Scan) wird „Spedition Nolte“ einmal in der
   PDF markiert. „Alle anwenden“ erfasst alle Vorkommen in allen drei Dateien, auch die Silbentrennung und den Scan.
2. In keiner Ausgabedatei steht danach „Nolte“, und der Leck-Test ist grün.
3. Markiert man „Moritz Günther“, wird „Herrn Günther“ als eigene Gruppe angeboten und lässt sich abwählen.
4. „Rückgängig“ stellt den vorherigen Zustand vollständig wieder her, Karten und Vorschau eingeschlossen.
5. Eine Markierung von „Bank“ löst die Warnung „sehr häufig, bitte einzeln prüfen“ aus.
6. Mit Haken „künftig …“ wird der Begriff im nächsten neuen Vorgang ohne Zutun vorgeschlagen.

## Anknüpfungspunkte im Code (Stand 04.11.2026)

- **Heute vorhanden:**
  - Nachtragen als Freitext (`Sitzung.nachtragen`, `analyseStarten(t)` in `ui/app.js`)
  - Lernen (`est.lernen`, `immer_ersetzen`)
  - vorgangsweite Weitergabe (`engine.propagate_vorgang`)
  - Namensteile (`engine.namensteile`)
  - Leck-Prüfung mit Ligaturen/Silbentrennung (`files._pdf_needle_regex`, `_pdf_leak_regex`)
  - Wortpositionen aus OCR (`ocr.Seite.woerter`)
- **Neu nötig:**
  - Positionen je Treffer für die Vorschau (PDF-Rects, OCR-Boxen, Text-Offsets)
  - ein Endpunkt „markieren“ mit Rückgabe der Fundstellen je Datei, bevor angewendet wird
  - Rückgängig-Stapel in der Sitzung

## Stand der Umsetzung (05.11.2026)

Umgesetzt in `server/markieren.py`, `server/dienst.py` (`auswahl`, `markieren`, `stelle`, `rueckgaengig`) und
`ui/app.js`, getestet in `tests/test_server.py::test_markieren_und_im_rest_suchen`:

- **M2:** Maus und Umschalt+Pfeiltasten. Abgeschnittene Wortränder bis 2 Zeichen werden ergänzt. Mehrzeilige
  Auswahl ist möglich.
- **M3:** Art-Vorschlag und „gehört zu …“.
- **M4:** Gesucht wird nach ganzen Wörtern, Beugung, Silbentrennung, Ligaturen und Namensteilen als eigene Gruppe.
  Schon markierte Stellen werden angezeigt und nicht doppelt angelegt.
- **M5:** Anzahl je Datei, „Alle anwenden“, „Einzeln ansehen“, „Nur hier“ und eine Warnung ab 50 Fundstellen.
- **M6:** Rückgängig mit Strg+Z oder per Toast. Das gilt auch für Änderungen an den Karten.
- **M7:** Nicht anonymisieren: nur hier, im ganzen Vorgang oder künftig immer. Außerdem „doch anonymisieren“.
- **M8:** Begründung „von Ihnen markiert“ bzw. „wie von Ihnen markiert“.
- **M9:** dieselbe Pipeline wie bei erkannten Treffern.
- **M10:** Lernen mit Haken.

Abweichungen und offen:

- **M1:** Die Vorschau zeigt den gelesenen Text, nicht das Seitenbild der PDF. Scans erscheinen als Text aus der
  Texterkennung. Eine Seitenbild-Ansicht mit Textebene ist noch offen.
- **„Nur hier“:** Das wirkt in Text- und Markdown-Ausgaben genau an der Stelle. PDF-, Word- und Excel-Kopien
  ersetzen nach Suchtext, dort wird derselbe Text überall ersetzt (sichere Richtung). Die Oberfläche sagt das.
- **„hierher übernehmen“ (M4):** Eine Fundstelle, die schon zu einem anderen Platzhalter gehört, lässt sich noch
  nicht umhängen. Das geht weiter über „gehört zu“ auf der Karte.
- **Rückgängig und gelernte Begriffe:** Rückgängig nimmt gelernte Einträge in den Einstellungen nicht zurück.
  Sie lassen sich unter Einstellungen → Gelernte Begriffe löschen.
