# Anforderung: Selbst markieren, für künftige Dokumente lernen, Löschfristen je Fall, geführte Einführung

Aufgenommen am 08.11.2026, Abschnitt 9 (Einführung) ergänzt am selben Tag. Baut auf
[markieren-und-suchen.md](markieren-und-suchen.md) auf (umgesetzt in 0.3.0).

## Ausgangslage (Stand 0.3.0)

Schon vorhanden:
- Übersehenes im Dokument mit der Maus markieren; Lokanon schlägt die Art vor und sucht im ganzen Vorgang.
- Feld „Fehlt etwas?“ zum Nachtragen von Hand.
- Haken „künftig in allen Dokumenten suchen“, standardmäßig aus.
- „Gelernte Begriffe“ unter Einstellungen, einzeln löschbar.

Schwachstellen:
1. **Schwer zu finden.** Markieren erklärt nur ein grauer Hinweis. Bei ausgeblendetem Dokument entdeckt es keiner.
2. **Lernen ist ein Umweg.** Der Haken muss bei jeder Markierung gesetzt werden.
3. **Speicherung.** Gelernte Begriffe (echte Namen) stehen **im Klartext** in `einstellungen.yaml` und **verfallen
   nie**. Es ist nicht nachvollziehbar, aus welchem Fall ein Begriff stammt.

## Ziel

- Lokanon schlägt vor, was zu anonymisieren ist; der Anwender wählt schnell an und ab (funktioniert schon).
- Der Anwender sieht ohne Erklärung, wie er Übersehenes selbst markiert.
- Selbst markierte Begriffe lernt Lokanon nach einer kurzen Bestätigung und schlägt sie in künftigen Dokumenten vor.
- Jeder gelernte Begriff ist einem Fall zugeordnet. Löschfristen laufen automatisch, lassen sich je Fall verlängern,
  und ein Löschwunsch des Mandanten ist mit einem Klick erledigt und nachweisbar.
- Das alles darf die Bedienung nicht aufwendiger machen als heute.

## 1. Markieren sichtbar machen

- **Knopf „Übersehenes markieren“** über dem Dokument schaltet einen Markiermodus ein: Klick auf ein Wort markiert das
  ganze Wort, Ziehen mehrere Wörter. **Doppelklick** markiert auch ohne Modus.
- **Karte am Ende der Liste:** „Fehlt etwas? Im Dokument markieren oder hier eintippen.“ Bei ausgeblendetem Dokument
  blendet ein Klick es ein.
- **Kurzer Hinweis beim ersten Mal**, danach nie wieder.
- Danach die Leiste wie heute („Falkenhorst als [Projekt ▾] · 3 Stellen gefunden · überall ersetzen“), ohne Haken
  fürs Lernen. Gelernt wird am Ende (Abschnitt 3).
- Abhängigkeit: Für gescannte PDFs braucht es die Seitenbild-Vorschau (offener Punkt aus der UI-Liste).

## 2. Was gelernt wird

**a) Regel statt Name (bevorzugt).**
- Steht der markierte Wert hinter einer Bezeichnung („Mandantennr.: 48213“, „Schadennummer …“), lernt Lokanon die
  Bezeichnung: „Künftig immer den Wert nach ‚Mandantennr.‘ ersetzen“.
- Bei Nummern mit festem Aufbau das Muster: „AZ-2026-0815“ → „Nummern dieses Musters vorschlagen“.
- Gespeichert wird nur Bezeichnung oder Muster, keine personenbezogenen Daten. Kein Fallbezug, keine Löschfrist nötig.

**b) Der Begriff selbst.**
- Für Namen, Projektnamen und Kürzel ohne Bezeichnung davor.
- **Gelernte Begriffe werden vorgeschlagen, nie stillschweigend ersetzt.** Sie erscheinen als normale Karte mit der
  Begründung „von Ihnen gelernt am 08.11. · Fall 12 O 345/26“ und sind abwählbar.
- Schreibvarianten (gebeugt, getrennt) findet die bestehende Suche mit.

**c) Später:** das eigene Modell an den eigenen Testfällen nachtrainieren, sobald genug Fälle vorliegen.

## 3. Bestätigung: einmal am Ende

Nach „Anonymisieren“, nur wenn etwas selbst markiert wurde:

> **4 Begriffe für künftige Dokumente merken?**  Fall: [12 O 345/26 ▾]
> ☑ Falkenhorst · Projekt · ohne Frist
> ☑ Nolte · Person · bis 08.11.2027
> ☑ Wert nach „Mandantennr.“ · Regel · ohne Frist
> ☐ …
> **[Merken]**  [Nicht merken]

- Alles vorausgewählt, ein Klick genügt. Einzelne Begriffe lassen sich abwählen.
- „Nicht merken“ ohne Rückfrage. Mit „Nicht mehr fragen“ lässt sich das Lernen ganz abschalten (Einstellungen).
- Beim Markieren selbst fragt Lokanon nichts.

## 4. Zuordnung zum Fall (gewählt: Etikett automatisch, Fall optional)

- **Lokanon setzt den Fall selbst:** Aktenzeichen aus dem Dokument, sonst Ordner- oder Vorgangsname, sonst
  „Vorgang vom 08.11.2026“. Bekannte Fälle werden wiedererkannt (gleiches Aktenzeichen → gleicher Fall).
- **Wer nichts tut**, hat trotzdem eine Herkunft je Begriff.
- **Wer den Fall im Abschlussfenster bestätigt oder korrigiert**, bekommt die saubere Zuordnung mit allen
  Fall-Funktionen (Abschnitt 5). Das Feld ist eine Auswahl mit Eingabe, kein Pflichtfeld.
- Ein Begriff kann mehreren Fällen gehören (z. B. ein Sachverständiger). Er wird erst gelöscht, wenn keiner seiner Fälle
  ihn mehr hält.

## 5. Löschfristen

- **Personenbezogene Begriffe** (Person, Adresse, Kontakt, Kennnummer …): Frist ab dem **letzten Fund**,
  Standard 12 Monate, einstellbar 3/6/12/24 Monate. Jeder neue Fund in einem Dokument setzt die Frist neu.
- **Nicht personenbezogen** (Projekt, Kürzel, Regel, Muster): ohne Frist, einzeln löschbar.
- **Je Fall:**
  - „Verlängern“ um 6, 12 oder 24 Monate oder „bis auf Widerruf (Mandat läuft)“
  - „Fall abgeschlossen“: ab jetzt läuft eine kurze Frist (Standard 3 Monate)
  - „Jetzt löschen“
- **Hinweis vor dem Löschen:** 30 Tage vorher beim Start „12 Begriffe aus Fall 12 O 345/26 laufen am 15.12. ab“
  mit [Verlängern] [Löschen lassen]. Wegklicken verschiebt den Hinweis, löscht aber nicht vorzeitig.
- **Aufräumen** automatisch beim Start von Lokanon.
- Die Aufbewahrungsfrist für Handakten (§ 50 BRAO, 6 Jahre) gilt für diese Liste nicht; sie ist nicht Teil der
  Handakte. Kürzere Fristen sind deshalb richtig.

## 6. Übersicht, Löschwunsch, Nachweis

Neuer Bereich **Einstellungen → Fälle und gelernte Begriffe**:
- Liste der Fälle mit Anzahl Begriffe, zuletzt genutzt, Löschung am. Aufklappbar mit den Begriffen.
- Suche über Begriffe und Fälle.
- **Löschwunsch eines Mandanten:** Fall öffnen → „Fall löschen“, oder Namen suchen → „überall löschen“. Gelöscht wird
  in gelernten Begriffen, eigenen Testfällen und Protokoll.
- **Löschprotokoll ohne Klartext:** Datum, Fall (verschlüsselt gespeichert, im Protokoll nur Fallnummer), Anzahl,
  Grund (Frist / Mandantenwunsch / von Hand). Als Nachweis exportierbar.
- Bereich **Aufbewahrung** für alles, was Lokanon speichert (gelernte Begriffe, Testfälle, Schlüssel der
  Rückübersetzung, Protokoll): je eine Frist und „jetzt löschen“.

## 7. Speicherung

- Neue Datei `<home>/gelernt.lokanon` statt `gelernt:` in `einstellungen.yaml`, **verschlüsselt mit dem Windows-Konto
  (DPAPI)**, Fernet als Rückfall, wie `server/testfaelle.py`.
- Je Eintrag: Begriff, Art, Fälle, gelernt am, zuletzt gefunden, Frist, Herkunft (Markierung, Nachtrag, Regel).
- **Übernahme:** Bestehende `gelernt:`-Einträge aus `einstellungen.yaml` beim ersten Start übernehmen (Fall
  „Übernommen aus 0.3.0“, Frist ab Übernahmetag) und dort entfernen. `allow_list`/`deny_list` von Hand bleiben, wie sie
  sind (Kanzleidaten, gewollt dauerhaft).
- „Stehen lassen“-Lernen (Gegenrichtung) bekommt dieselbe Speicherung; es betrifft meist keine Personendaten und
  läuft ohne Frist.

## 8. Datenschutz (Einschätzung, keine Rechtsberatung)

| Grundsatz | Umsetzung |
|---|---|
| Zweckbindung, Datenminimierung (Art. 5 Abs. 1 b, c) | Regeln und Bezeichnungen vor Namen lernen; nur nach Bestätigung |
| Speicherbegrenzung (Art. 5 Abs. 1 e) | Frist ab letztem Fund, Fall abschließen, automatisches Aufräumen |
| Löschung (Art. 17) | Fall löschen oder überall löschen per Suche, inkl. Testfälle und Protokoll |
| Rechenschaft (Art. 5 Abs. 2) | Zuordnung zum Fall, Löschprotokoll ohne Klartext, Export |
| Sicherheit (Art. 32), § 203 StGB | DPAPI-Verschlüsselung, Klartext nur im App-Fenster, nichts verlässt den PC |
| Datenschutz durch Voreinstellung (Art. 25) | Lernen nur nach Bestätigung, abschaltbar |

- Ergänzung für [verarbeitungsverzeichnis-eintrag.md](../vorlagen/verarbeitungsverzeichnis-eintrag.md): gelernte
  Begriffe als eigene Datenkategorie mit Zweck, Frist und Löschkonzept.
- Fristen und Texte vor dem Pilot-Rollout mit der/dem Datenschutzbeauftragten abstimmen.

## 9. Interaktive Einführung im Programm

### Ziel

Neue Anwender lernen Lokanon nicht aus der Anleitung, sondern im Programm selbst: Lokanon lädt ein Beispieldokument,
und der Anwender führt jeden Schritt **selbst** aus. Eine Sprechblase steht direkt neben dem Bedienelement, der Rest
der Oberfläche ist abgedunkelt. Dauer: etwa 5 Minuten, in Kapitel geteilt, jederzeit abbrechbar.

### So sieht es aus

- **Hervorhebung:** Das Bedienelement des Schritts bleibt hell, alles andere wird abgedunkelt (Ausschnitt).
- **Sprechblase daneben**, mit Pfeil auf das Element. Darin:
  - Kapitel und Schritt („Prüfen · 3 von 6“)
  - zwei, drei Sätze: was das ist, was jetzt passiert
  - Knöpfe [Zurück] [Weiter] und „Einführung beenden“
- **Zwei Arten von Schritten:**
  - *Zeigen:* Lokanon erklärt, der Anwender klickt auf „Weiter“.
  - *Selbst tun:* Die Blase sagt „Schalten Sie jetzt ‚Morbus Crohn‘ aus“. „Weiter“ ist ausgegraut, bis der Anwender
    es getan hat. Dann ein kurzes „Gut so“ und automatisch der nächste Schritt. Nach 20 Sekunden ohne Aktion erscheint
    „Zeig es mir“: Lokanon führt den Schritt selbst vor.
- **Bedienung:** Esc beendet, Enter = Weiter. Die Blase rückt mit, wenn das Fenster kleiner wird oder die Liste
  scrollt. Für Bildschirmleser wird jeder Schritt angesagt.

### Das Beispiel

- **Ein erfundenes Schreiben** („Unfallsache Moritz Günther ./. Krause Logistik AG“), mitgeliefert unter
  `ui/einfuehrung/`. Es enthält bewusst:
  - sichere Treffer (Name, Firma, Adresse, Telefon, IBAN, Kennzeichen)
  - einen **Fehlalarm** zum Abwählen („Morbus Crohn“ als Person vorgeschlagen)
  - einen **übersehenen Begriff** zum Selbstmarkieren („Projekt Falkenhorst“, dreimal im Text)
  - eine **Bezeichnung mit Wert** („Mandantennr.: 48213“) für das Regel-Lernen
  - ein Aktenzeichen, das als Fall vorgeschlagen wird
- **Feste Erkennung:** Die Treffer für das Beispiel liegen vorberechnet bei. Die Einführung läuft damit sofort, auch
  während die Sprachmodelle beim ersten Start noch laden, und sieht bei jedem gleich aus. Alles danach (markieren,
  suchen, ersetzen, Gegenprüfung, Ausgabe) läuft über die echten Funktionen.

### Kapitel

| Kapitel | Was der Anwender sieht und tut | Art |
|---|---|---|
| 1. Ablegen | Ablagefläche, „Ordner wählen“, Anzeige „Läuft lokal“; Lokanon legt das Beispiel ab | Zeigen |
| 2. Prüfen | Zusammenfassung, „Bitte ansehen“, Karte mit Begründung; **Fehlalarm ausschalten**; Klick auf Karte → Stelle im Dokument; **Platzhalter „[Mandant]“ vergeben** | Selbst tun |
| 3. Selbst markieren | Knopf „Übersehenes markieren“; **„Falkenhorst“ markieren**; Art wählen, 3 Stellen gefunden, überall ersetzen; **Strg+Z** probieren | Selbst tun |
| 4. Anonymisieren | **Anonymisieren klicken**; Gegenprüfung erklärt; Fertig-Ansicht mit Kopie, Ordner öffnen, KI-Anweisung, Rückübersetzung | Selbst tun |
| 5. Merken | Abschlussfenster „Begriffe merken?“; Fall „12 O 345/26“ vorgeschlagen; Frist erklärt; **Merken klicken** | Selbst tun |
| 6. Fälle und Einstellungen | Übersicht Fälle: verlängern, abschließen, löschen; Aufbewahrung; Kanzlei-Liste; Erweitert | Zeigen |

Zum Schluss: „Das Beispiel wird jetzt gelöscht. Die Einführung finden Sie jederzeit unter ? → Einführung.“

### Wo sie erscheint

- **Nach der Einrichtung beim ersten Start:** „Einführung starten (ca. 5 Min.)“ oder „Später“. „Später“ zeigt sie
  beim nächsten Start nicht erneut, nur der ?-Knopf bekommt einen Punkt.
- **?-Knopf oben:** Menü mit „Anleitung“, „Einführung“ und den einzelnen Kapiteln.
- **Direktlink** `#einfuehrung` bzw. `#einfuehrung/markieren` (für Pilot-Mails und die Anleitung).
- **Nach einem Update:** „Neu in 0.4: zwei Minuten Tour durch die neuen Funktionen“. Gezeigt werden nur Schritte, die
  mit der neuen Version markiert sind.
- Gesehene Kapitel stehen in den Einstellungen (`einfuehrung: {gesehen: [...], version: "0.4.0"}`), keine Personendaten.

### Wie sie eingebaut wird

**Getrennter Übungsvorgang (Server).**
- Die Einführung läuft in einer **zweiten `Sitzung`** neben der echten. Eine Arbeit, die der Anwender gerade offen hat,
  bleibt unberührt.
- Diese Sitzung hat eigene, flüchtige Einstellungen und einen Temp-Ordner als Ausgabe. Gelerntes, Testfälle und
  Protokoll landen **nicht** in den echten Dateien. Beim Beenden wird alles gelöscht.
- `server/app.py`: Die Endpunkte nutzen künftig `aktive_sitzung()` statt der festen `sitzung`.
  - `POST /api/einfuehrung/start` legt die Übungssitzung an und lädt das Beispiel mit den vorberechneten Treffern.
  - `POST /api/einfuehrung/ende` verwirft sie und schaltet zurück.
- Der Zustand meldet `einfuehrung: true`. Die Oberfläche zeigt dann oben ein Band: „Übungsvorgang, Ihre Daten sind
  nicht betroffen“.

**Führung (Oberfläche).**
- Neues Modul `ui/einfuehrung.js` mit `ui/einfuehrung.css`, ohne fremde Bibliothek (offline, rund 300 Zeilen):
  - Abdunkeln mit Ausschnitt, Sprechblase mit Pfeil, Positionierung neben dem Ziel, mitrücken bei Größenänderung
  - Warten auf das Ziel, wenn die Ansicht neu gezeichnet wird
- **Drehbuch als Daten** in `ui/einfuehrung/drehbuch.js`. Je Schritt:
  - `ziel`: ein Element mit festem Anker `data-tour="…"` (nicht die CSS-Klassen, die sich bei Umbauten ändern)
  - `titel`, `text`, Position der Blase
  - `warten`: `weiter` oder ein Ereignis wie `karte-aus`, `markiert`, `anonymisiert`, `gemerkt`
  - `vormachen`: was „Zeig es mir“ ausführt
  - `seit`: Version, für die Tour „Neu in …“
- **Ereignisse aus der App:** `ui/app.js` meldet wichtige Aktionen über ein kleines
  `document.dispatchEvent(new CustomEvent("lokanon", {detail: {art: "markiert", …}}))`. Die Führung hört nur zu und
  greift nicht in die Logik ein.
- **Anker setzen:** `data-tour` an rund 20 Bedienelementen in `ui/app.js` (Ablagefläche, Karte, Schalter,
  Markier-Knopf, Anonymisieren, Merken-Fenster, Fälle …).
- **Anleitung** (`static/anleitung/index.html`) bekommt je Kapitel einen Link „Im Programm zeigen“.

### Wartung

- Ein automatischer Test öffnet jeden Schritt des Drehbuchs im Browser und prüft, dass das Ziel existiert und sichtbar
  ist. So fällt eine kaputte Einführung nach UI-Umbauten sofort auf.
- Wer eine neue Funktion baut, ergänzt einen Schritt mit `seit: "<Version>"`. Dann erscheint er automatisch in der
  Tour „Neu in …“.

### Vor- und Nachteile dieser Bauweise

- **Vorteile:**
  - Der Anwender übt an den echten Funktionen.
  - Das Beispiel ist bei jedem gleich, und keine echten Daten sind betroffen.
  - Läuft offline und ohne fremde Bibliothek.
  - Die Tour „Neu in …“ fällt bei jedem Update nebenbei ab.
- **Nachteile:**
  - Jede Änderung an der Oberfläche muss das Drehbuch mitziehen. Der Test fängt das ab, kostet aber Pflege.
  - Die zweite Sitzung braucht einen kleinen Umbau in `server/app.py`.
  - Vorberechnete Treffer zeigen nicht, wie die Erkennung bei eigenen Dokumenten arbeitet. Das Band „Übungsvorgang“
    und der Schlusssatz sagen das.

## 10. Gespeicherte Angaben erklären: speichern, verwalten, löschen

Gespeicherte Angaben sind der Teil, bei dem Anwender am ehesten unsicher sind („Was hat Lokanon sich gemerkt? Darf
es das?“). Die Erklärung kommt deshalb auf vier Ebenen, immer mit einer kurzen Begründung.

### Die Begründungen (eine Quelle für alle Ebenen)

Kurz, ohne Paragrafen im ersten Satz. Paragraf nur in „Mehr dazu“.

| Frage | Kurzbegründung | Mehr dazu |
|---|---|---|
| Warum speichert Lokanon überhaupt? | Damit Sie Übersehenes nur einmal markieren. Beim nächsten Dokument schlägt Lokanon es selbst vor. | Gespeichert wird nur, was Sie am Ende bestätigen. |
| Warum ein Fall? | Damit Sie bei einem Löschwunsch alles zu einem Mandat auf einmal finden und zeigen können, woher eine Angabe stammt. | Rechenschaftspflicht, Art. 5 Abs. 2 DSGVO |
| Warum eine Frist? | Namen von Mandanten, Gegnern und Zeugen dürfen nur so lange gespeichert sein, wie sie gebraucht werden. Läuft ein Mandat länger, verlängern Sie den Fall. | Speicherbegrenzung, Art. 5 Abs. 1 e DSGVO |
| Warum verschlüsselt? | Sie unterliegen der Schweigepflicht. Ohne Ihr Windows-Konto kann niemand die Liste lesen, auch nicht in einer Sicherungskopie. | Art. 32 DSGVO, § 203 StGB |
| Warum ein Löschprotokoll ohne Namen? | Es belegt, dass gelöscht wurde, ohne die gelöschten Namen wieder aufzuschreiben. | Nachweis gegenüber Mandant und Aufsicht |
| Warum nicht 6 Jahre wie die Handakte? | Die Liste ist ein Arbeitsmittel, nicht Teil der Handakte. Für sie gilt: so kurz wie möglich. | § 50 BRAO gilt für die Handakte |

Die Texte stehen einmal in `ui/einfuehrung/hilfetexte.js` und werden von Abschlussfenster, Kontexthilfe, Tour und
(beim Build) der Anleitung verwendet. So sagen alle Stellen dasselbe.

### Ebene 1: Im Moment des Speicherns

Im Abschlussfenster „Begriffe merken?“ eine Zeile unter der Liste:
„Nur auf diesem PC, verschlüsselt. Personennamen löscht Lokanon 12 Monate nach dem letzten Fund. **Warum?**“
„Warum?“ öffnet eine kleine Blase mit den drei Kurzbegründungen (speichern, Frist, verschlüsselt) und dem Link
„In 2 Minuten zeigen“ zur Tour.

### Ebene 2: Kontexthilfe neben den Bedienelementen

Ein kleines (i) neben Frist, Fall, „Verlängern“, „Fall abgeschlossen“, „Überall löschen“ und Löschprotokoll. Ein Klick
zeigt die Kurzbegründung und „Mehr dazu“. Kein Tooltip beim Überfahren, damit nichts flackert.

### Ebene 3: Tour-Kapitel 7 „Gespeicherte Angaben“ (ca. 3 Minuten)

Läuft in der Übungssitzung. Dafür bringt das Beispiel drei erfundene Fälle mit:
- einen laufenden Fall
- einen, dessen Frist in 20 Tagen abläuft
- einen abgeschlossenen

| Schritt | Was der Anwender sieht und tut | Art |
|---|---|---|
| 1 | Warum Lokanon speichert (Kurzbegründung), Hinweis: nur nach Bestätigung | Zeigen |
| 2 | Einstellungen → „Fälle und gelernte Begriffe“ **öffnen** | Selbst tun |
| 3 | Fall „12 O 345/26“ **aufklappen**: Begriffe, zuletzt gefunden, Löschung am; Warum ein Fall | Selbst tun |
| 4 | Warum eine Frist; Fall **verlängern** „bis auf Widerruf (Mandat läuft)“ | Selbst tun |
| 5 | Zweiten Fall **als abgeschlossen markieren**; die kurze Frist beginnt | Selbst tun |
| 6 | Der Hinweis vor dem Löschen (für den dritten Fall vorgeführt): Verlängern oder Löschen lassen | Zeigen |
| 7 | Löschwunsch eines Mandanten: Namen **suchen**, **überall löschen**; Lokanon zeigt vorher, was gelöscht wird (Begriffe, Testfälle, Protokoll) | Selbst tun |
| 8 | Löschprotokoll: Eintrag ohne Namen, **Nachweis exportieren**; Warum ohne Namen | Selbst tun |
| 9 | Aufbewahrung: Fristen einstellen, Lernen ganz abschalten; Warum verschlüsselt | Zeigen |

Erreichbar über ? → Einführung → „Gespeicherte Angaben“, über „In 2 Minuten zeigen“ im Abschlussfenster und über
den Direktlink `#einfuehrung/gespeichert`. Beim ersten Mal, wenn der Anwender etwas merkt, bietet Lokanon das Kapitel
einmal an.

### Ebene 4: Anleitung

Abschnitt „Gespeicherte Angaben und Datenschutz“ in `static/anleitung/index.html`:
- die Tabelle mit den Begründungen
- „Im Programm zeigen“ → Kapitel 7
- kurze Fragen und Antworten, zum Beispiel:
  - „Muss das ins Verarbeitungsverzeichnis?“ (ja, Mustertext liegt bei)
  - „Was passiert bei einer Neuinstallation?“
  - „Wer kann die Liste lesen?“

## 11. Bearbeitete Vorgänge und Fälle löschen

### Was heute pro Lauf entsteht (Stand 0.3.0)

| Daten | Ort | Personendaten? | Heute verknüpft? |
|---|---|---|---|
| Originaldateien | wo der Anwender sie hat | ja | gehören nicht Lokanon |
| Anonymisierte Kopien (+ .md) | neben den Originalen oder `Dokumente\Lokanon\Anonymisiert` | nein, sofern vollständig | nein |
| Schlüssel für Rückübersetzung | `.anon.json` im Schlüsselordner, mit Passwort verschlüsselt | **ja** (Platzhalter → Klartext) | nur über Name und Uhrzeit |
| Vorgangsordner (Erweitert) | Vorgangsordner | **ja: Kopie der Originale, Prüfbericht im Klartext** | eigener Ordner |
| Eigene Testfälle (Erweitert) | `testfaelle\*.lokanon-test`, DPAPI | **ja** | nur über Uhrzeit |
| Protokoll | `protokolle\*.log`, 30 Tage | nein (geschwärzt) | über Laufnummer |
| Gelernte Angaben (neu) | `gelernt.lokanon`, DPAPI | **ja** | über den Fall (Abschnitt 4) |

**Folgerung:** Ein Löschen „des Falls“ ist heute nicht möglich, weil nichts die Teile verbindet. Voraussetzung ist ein
**Vorgangsverzeichnis**.

### Voraussetzung: Vorgangsverzeichnis und Fallschlüssel

- **`vorgaenge.lokanon` (DPAPI):** Je Vorgang stehen dort:
  - Name, Fall, Zeitpunkt
  - Pfade der Kopien, des Schlüssels, des Vorgangsordners und der Testfälle
  - die Laufnummer im Protokoll
  
  Daraus entsteht die Liste „Zuletzt bearbeitet“ auf der Startseite.
- **Ein eigener Schlüssel je Fall** (selbst mit DPAPI geschützt). Gelernte Angaben, Testfälle und künftig auch der
  Vorgangsordner werden damit verschlüsselt.
  - Wird der Fall gelöscht, wird auch dieser Schlüssel gelöscht. Dann sind auch Kopien dieser Daten in Sicherungen,
    OneDrive-Versionen oder im Papierkorb nicht mehr lesbar (Löschen durch Schlüsselvernichtung).
  - Das ist verlässlicher als Überschreiben, das auf SSDs nicht sicher wirkt.
- **Vorgangsordner verschlüsseln:** Heute liegen dort Kopien der Originale im Klartext. Künftig sind sie mit dem
  Fallschlüssel verschlüsselt; geöffnet wird nur über Lokanon.

### Wo man löscht

- **Startseite → Zuletzt bearbeitet:** Menü je Zeile „Vorgang löschen“; mehrere Zeilen markieren → „Auswahl löschen“.
- **Fälle:** „Fall löschen“ löscht alle Vorgänge des Falls und seine gelernten Angaben.
- **Suche nach einem Namen** („Löschwunsch eines Mandanten“, Abschnitt 6) → „Überall löschen“ führt in denselben
  Dialog, vorbelegt mit allen Fällen, in denen der Name vorkommt.
- **Automatisch nach Frist:** dieselbe Routine ohne Dialog, angekündigt 30 Tage vorher.

### Der Dialog: eine Rückfrage, alle Folgen sichtbar

> **Fall 14 C 512/26 löschen?**  2 Vorgänge · zuletzt bearbeitet heute
>
> **Wird gelöscht**
> ☑ Gelernte Angaben (12). *3 weitere bleiben, weil sie auch zu Fall 3 O 1120/26 gehören.*
> ☑ Schlüssel für die Rückübersetzung (2). *KI-Antworten zu diesem Fall lassen sich danach nicht mehr zurückübersetzen.*
> ☑ Vorgangsordner mit Prüfbericht und Kopie der Originale (2)
> ☑ Eigene Testfälle (2)
>
> **Sie entscheiden**
> ☐ Anonymisierte Kopien (8 Dateien in `…\Akte Winter`). *Enthalten keine Namen. Was Sie schon an eine KI gegeben
> haben, kann Lokanon nicht löschen.* Kommen in den Papierkorb.
>
> **Bleibt**
> · Ihre Originaldateien (Lokanon verändert sie nie)
> · Protokoll ohne Namen (löscht sich nach 30 Tagen) und ein Eintrag im Löschprotokoll
>
> Grund: (•) Wunsch des Mandanten  ( ) Fall abgeschlossen  ( ) Sonstiges
>
> [Abbrechen]  **[12 Angaben und 6 Dateien endgültig löschen]**

Regeln:
- Alles mit Personendaten ist vorausgewählt. Abwählbar ist es nur beim Grund „Sonstiges“. Bei „Wunsch des
  Mandanten“ muss alles weg.
- Der Löschknopf nennt, was passiert („12 Angaben und 6 Dateien“), statt nur „OK“. Fokus liegt auf „Abbrechen“.
- **Eine zweite Rückfrage nur bei echtem Risiko:**
  - der Fall ist als „Mandat läuft“ markiert
  - ein Schlüssel wurde in den letzten 14 Tagen für eine Rückübersetzung benutzt
  - der Vorgang ist gerade offen

  Sonst keine zweite Frage. Das ist bewusst so, damit Löschen nicht nervt.
- Kein „Rückgängig“: Personendaten in einem Papierkorb von Lokanon widersprächen dem Zweck. Die Kopien, die keine
  Personendaten enthalten, gehen in den Windows-Papierkorb.

### Danach: Ergebnis und Nachweis

- **Ergebnisseite:** was gelöscht wurde, je Art mit Anzahl.
- **Was nicht ging, mit Pfad und „Erneut versuchen“:** Datei in Word geöffnet, Netzlaufwerk nicht erreichbar, Datei
  verschoben.
- **Löschprotokoll:** Datum, Fallnummer (ohne Namen), Arten und Anzahl, Grund.
  - „Nachweis exportieren“ erzeugt eine HTML-/PDF-Bestätigung ohne Namen, für die Akte oder den Mandanten.

### Sonderfälle

- **Vorgang ist gerade geöffnet:** erst schließen; der Dialog bietet „Schließen und löschen“.
- **Kopien wurden verschoben oder umbenannt:** Lokanon meldet „nicht gefunden“. Der Rest wird trotzdem gelöscht.
- **Kopien in OneDrive:** gehen in den Papierkorb von OneDrive; der Dialog nennt das.
- **Eine Angabe gehört zu mehreren Fällen:** Sie bleibt, bis der letzte Fall gelöscht ist. Bei „Wunsch des
  Mandanten“ über die Namenssuche wird sie überall gelöscht.
- **Vorgänge ohne Fall:** lassen sich einzeln löschen. Nach 12 Monaten werden sie automatisch gelöscht.

### Hilfe und Tour

- **Tour-Kapitel 7, neuer Schritt nach dem Löschwunsch:** „Fall löschen“ am dritten Beispielfall. Der Anwender sieht
  den Dialog, wählt einen Grund, löscht und öffnet den Nachweis.
- **Neue Hilfetexte** in `hilfetexte.js`:
  - „Warum bleiben die Originale?“
  - „Warum bleibt das Protokoll?“
  - „Warum sind auch Sicherungskopien danach unlesbar?“
  - „Warum kann Lokanon an eine KI gegebene Kopien nicht löschen?“
- **(i)-Hilfe** an jeder Zeile des Dialogs.
- **Anleitung:** Abschnitt „Fälle löschen“ unter „Gespeicherte Angaben und Datenschutz“.

## 12. Neue Oberfläche: Arbeitsplatz mit Teilen aus der Prüfstation

Entschieden am 08.11.2026 nach Rückmeldung der Pilotanwender („sieht nach KI-Baukasten aus“). Entwürfe:
[Design-Canvas](https://claude.ai/artifact/C39mfcWHw9Lzj2kUhwrDT3), Reihe „Gewählt“.

**Grundlage A · Arbeitsplatz** (wie Windows-Bürosoftware):
- Titelzeile mit Suche, Befehlsleiste mit Symbol und Text, Navigation links (Start, Aktueller Vorgang, Fälle und
  gelernte Angaben, Protokoll, Einführung, Einstellungen), Statusleiste („Läuft lokal“, „Sprachmodelle bereit“, Seite).
- Dokument als weiße Seite auf Grau in der Mitte, Dateien als Reiter.
- Prüfbereich rechts: kompakte Liste mit Kontrollkästchen, gruppiert, ausgewählter Eintrag klappt auf.
- Schrift Segoe UI (Windows), 14 px, Ecken 4 px, keine Schatten außer der Dokumentseite.
- Verschwindet: große Serifenüberschrift, zentrierte Begrüßung, abgerundete Karten mit farbigem Rand, Pillenknöpfe.

**Übernommen aus B · Prüfstation:**
1. Kleines Fenster direkt an der markierten Stelle: Art wählen, Anzahl Stellen, „Nur hier“ / „Überall ersetzen“.
2. Fähnchen mit dem Platzhalter an der ausgewählten Stelle im Dokument.
3. Anzahl auf dem Hauptknopf: „Anonymisieren · 15“.
4. Bereich „Fälle und Fristen“ auf der Startseite neben dem Ablegen.
- Seitenvorschaubilder nur für gescannte PDFs (zusammen mit der Seitenbild-Vorschau).
- Gruppe „Selbst markiert“ in der Liste.

**Entfällt aus A:** der doppelte Knopf „Vorschau anonymisiert“ (die Umschaltung über dem Dokument reicht).

**Hilfe und Tour:** Jeder Bereich bekommt beim Umbau seine `data-tour`-Anker; das Drehbuch entsteht gleich auf der
neuen Oberfläche, nicht auf der alten.

## Reihenfolge der Umsetzung

0. Neue Oberfläche (Abschnitt 12), zuerst Gerüst: Titelzeile, Befehlsleiste, Navigation, Statusleiste, Prüfbereich,
   Startseite. Alle weiteren Schritte bauen darauf.

1. Vorgangsverzeichnis und Fallschlüssel (Abschnitt 11), verschlüsselte Speicherung, Übernahme aus 0.3.0, Frist ab
   letztem Fund, Aufräumen beim Start
2. Markiermodus, Doppelklick, Karte am Listenende, Hinweis beim ersten Mal
3. Abschlussfenster „merken?“ mit Fall; gelernte Begriffe als Vorschläge mit Begründung
4. Bereich „Fälle und gelernte Begriffe“: verlängern, abschließen, Suche, Löschprotokoll; Vorgänge und Fälle löschen
   mit Dialog, Ergebnisseite und Nachweis (Abschnitt 11); Vorgangsordner verschlüsseln
5. Bezeichnungen und Nummernmuster lernen
6. Bereich „Aufbewahrung“, Hinweis vor dem Löschen, Text fürs Verarbeitungsverzeichnis
7. Einführung: Übungssitzung im Server, Führungsmodul, Beispiel mit vorberechneten Treffern, Drehbuch für Kapitel 1–6,
   Einstieg nach der Einrichtung und im ?-Menü, Test für alle Schritte
   - Kommt zuletzt, weil sie die Funktionen aus 1–6 zeigt. Das Führungsmodul kann früher entstehen.
8. Gespeicherte Angaben erklären: `hilfetexte.js` mit den Begründungen, „Warum?“ im Abschlussfenster, (i)-Kontexthilfe,
   Tour-Kapitel 7 mit drei Beispielfällen, Abschnitt in der Anleitung

Ab hier gilt für jeden Schritt die Regel aus [hilfe-mitpflegen.md](../entwicklung/hilfe-mitpflegen.md): Wer eine
Funktion baut oder ändert, zieht Drehbuch, Hilfetexte und Anleitung im selben Commit mit.

## Abnahme

- Tests mit `LOKANON_HOME` im Temp-Ordner: Datei verschlüsselt (kein Klartext in den Bytes), Übernahme aus
  `einstellungen.yaml`, Frist läuft ab und wird durch neuen Fund verlängert, Fall löschen entfernt Begriffe, Testfälle
  und Protokolleinträge, Begriff in zwei Fällen bleibt bis zum zweiten.
- Über die API: markieren → anonymisieren → merken mit Fall → neuer Vorgang zeigt den Begriff als Vorschlag mit
  Begründung → Fall löschen → nächster Vorgang zeigt ihn nicht mehr.
- Im Browser durchklicken: Markiermodus, Doppelklick, Abschlussfenster mit einem Klick, Fälle-Übersicht.
- Einführung: alle Kapitel im Browser durchspielen, einmal selbst und einmal nur mit „Zeig es mir“. Danach prüfen:
  echte Einstellungen, gelernte Begriffe, Testfälle und Protokoll unverändert; Temp-Ordner gelöscht; eine vorher
  offene Arbeit ist noch da. Test „jedes Drehbuch-Ziel existiert“ grün.
