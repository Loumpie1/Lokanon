# Lokanon 0.3.0 (Pilot) – was neu ist

Stand: 05.11.2026. Lokanon arbeitet weiter vollständig offline auf Ihrem PC.

## Wichtig: Diese Fehler sind behoben

- **Aktiengesellschaften blieben stehen.**
  - In 0.2.0 galt das Kürzel „AG“ überall als „Amtsgericht“. Firmen wie „Krause Logistik AG“ wurden deshalb
    nicht ersetzt.
  - Jetzt gilt „AG“ nur am Anfang als Gericht („AG Essen“).
  - **Bitte Kopien aus 0.2.0, in denen Aktiengesellschaften vorkommen, noch einmal prüfen.**
- **Namen im Dateinamen** der Kopie werden ersetzt.
- **PDF-Lecks geschlossen.**
  - Alternativtexte und Strukturbaum getaggter PDFs (z. B. Online-Rechnungen) werden geleert, ebenso
    Ebenennamen und Seitenbeschriftungen. Darin konnten Namen unsichtbar stehen bleiben.
  - Die Gegenprüfung sucht jetzt auch dort.
- **Durchsuchbare Scans** werden nicht mehr ausgeweißt.

## Bessere Erkennung

- **Formulare und Tabellen:**
  - Bezeichnung und Wert gehören zusammen („Name: …“, „Versichertennr. …“, „Fall-Nr.“, „PIZ“).
  - Lohnabrechnungen: Fachbegriffe sind keine Namen.
- **Arztbriefe und Befunde:**
  - Geburtsdatum mit „*“, „Nachname, Vorname“, Titel mit Initialen („Dr. med. V. Jäger“).
  - Medikamente, Laborwerte und Fachbegriffe gelten nicht mehr als Namen.
- **Unterschriften und Richterblöcke**, Postleitzahlen mit Landeskennung („A-1010 Wien“), Straße im
  Anschriftblock.
- **Weniger Fehlalarme:** Tarifverträge und Gesetzeskürzel gelten nicht mehr als Firmen. Ein Firmenwort allein
  wird wie die Firma ersetzt („bei Brandauer“).
- **Gemessen an öffentlichen deutschen Testdaten** (Arztbriefe, die Lokanon nie gesehen hat): erkannt 97 % statt
  79 %, Fehlalarme mehr als halbiert.

## Neu beim Prüfen

- **Markieren und im Rest suchen:** Übersehene Stelle im Dokument markieren. Lokanon schlägt die Art vor und
  findet alle Vorkommen in allen Dateien, auch gebeugt oder am Zeilenende getrennt.
- **Rückgängig** (Strg+Z) für jede Änderung beim Prüfen.
- **Einzelne Stelle stehen lassen** oder doch anonymisieren.
- **Klick auf eine Karte** springt zur Stelle im Dokument.
- **Begründung je Vorschlag** („Formularfeld „Name““, „nach Titel“).
- **Aus Korrekturen lernen:** „Künftig immer stehen lassen“ bzw. „künftig immer suchen“. Unter Einstellungen →
  Gelernte Begriffe lässt sich das wieder löschen.

## Wenn etwas schiefgeht

- **Fehler sind verständlich:** Lokanon sagt, wo die Gegenprüfung noch Originaltext gefunden hat, und was zu tun
  ist.
- **„Zurück zum Prüfen“** behält Ihre Prüfung.
- **Protokoll ohne Klartext** unter Einstellungen → Protokoll: nur Platzhalter und Dateinummern, gut zum
  Weitergeben bei Rückfragen.

## Neu unter Einstellungen → Erweitert (aus, bis Sie es einschalten)

**Geprüfte Vorgänge als eigene Testfälle speichern:**
- Text und Ihre Korrekturen bleiben verschlüsselt auf Ihrem PC, lesbar nur unter Ihrem Windows-Konto.
- Damit lässt sich jede neue Version an Ihren echten Dokumenten messen.
- Hilft uns sehr, wenn Sie es im Pilot einschalten. Es wird nichts übertragen. Auf Wunsch schicken Sie uns nur die
  Auswertung ohne Klartext.
