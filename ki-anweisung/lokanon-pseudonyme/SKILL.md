---
name: lokanon-pseudonyme
description: Umgang mit pseudonymisierten Texten aus Lokanon. Nutze diesen Skill immer, wenn ein Text oder eine Datei Platzhalter wie [Person_1], [Firma_2], [Ort_1], [Adresse_3], [Aktenzeichen_1], [IBAN_1], [Datum_2] oder sprechende Platzhalter wie [Mandant] enthält. Die Platzhalter sind Pseudonyme, die später lokal zurückübersetzt werden; sie müssen unverändert übernommen werden.
---

# Pseudonymisierte Texte aus Lokanon

Lokanon ersetzt vor dem Upload lokal alle personenbezogenen und vertraulichen Angaben durch Platzhalter. Der Schlüssel bleibt beim Nutzer. Die Texte enthalten deshalb keine echten Personendaten.

## Platzhalter-Format

`[Label_n]` mit laufender Nummer, oder ein von der Kanzlei vergebener Name wie `[Mandant]`, `[Gegnerin]`, `[Zeuge_Mueller]`. Übliche Labels:

| Platzhalter | Bedeutung |
|---|---|
| `[Person_n]` | eine natürliche Person (Vor- und Nachname, auch Namensteile, Anrede mit Nachname) |
| `[Firma_n]` | Unternehmen, Organisation |
| `[Ort_n]` | Ort, PLZ mit Ort |
| `[Adresse_n]` | Straße mit Hausnummer |
| `[Telefon_n]`, `[Email_n]`, `[URL_n]`, `[IP_n]` | Kontaktdaten |
| `[Aktenzeichen_n]`, `[Zeichen_n]` | Aktenzeichen, Vorgangsnummer, Diktatzeichen |
| `[Grundbuch_n]` | Grundbuch-/Katasterangabe |
| `[IBAN_n]`, `[Konto_n]`, `[Karte_n]` | Bankdaten |
| `[VersNr_n]` | Versicherungsschein-, Schadennummer |
| `[SteuerID_n]`, `[Steuernr_n]`, `[UStID_n]` | Steuernummern |
| `[SVNr_n]`, `[KVNr_n]`, `[LANR_n]`, `[BSNR_n]` | Sozial-/Krankenversicherung, Arztnummern |
| `[Ausweis_n]`, `[Pass_n]`, `[Fuehrerschein_n]` | Ausweisdokumente |
| `[Kennzeichen_n]`, `[FIN_n]` | Kennzeichen, Fahrgestellnummer |
| `[Datum_n]` | personenbezogenes Datum (Geburt, Tod) |
| `[Begriff_n]` | vom Nutzer festgelegte Begriffe |

## Regeln

1. **Exakt übernehmen.** Jeder Platzhalter bleibt zeichengenau erhalten: Klammern, Schreibweise, Unterstrich, Nummer. Nicht umformulieren zu „Person 1“, „PERSON_1“ oder „[Person-1]“.
2. **Nicht auflösen, nicht raten.** Keine Namen, Firmen, Adressen oder Nummern erfinden. Keine Vermutungen äußern, wer sich hinter einem Platzhalter verbirgt, auch wenn der Kontext Hinweise gibt.
3. **Gleicher Platzhalter, gleiche Person.** `[Person_1]` ist überall dieselbe Person, auch über mehrere Dateien hinweg. Verschiedene Nummern sind verschiedene Personen.
4. **Beugung außerhalb der Klammer.** „[Person_1]s Fahrzeug“, „mit [Firma_2]“. Nie innerhalb der Klammer ändern.
5. **Neue Akteure neutral benennen.** Wenn du in einem Entwurf jemanden einführen musst: „die Gegenseite“, „der Sachverständige“, nie ein erfundener Name.
6. **Platzhalter in der Antwort verwenden.** Beziehe dich auf Personen und Sachen immer mit ihrem Platzhalter, damit die Antwort automatisch zurückübersetzt werden kann.
7. **Keine Datenschutz-Hinweise nötig.** Die Daten sind pseudonymisiert; Hinweise auf den Umgang mit Personendaten sind überflüssig.
8. **Dateinamen** mit dem Zusatz `_anonymisiert` sind die bereinigten Fassungen; behandle sie genauso.

## Beispiel

Eingabe: „[Mandant], geb. [Datum_1], wohnhaft [Adresse_1], [Ort_1], hat gegen den Bescheid [Aktenzeichen_1] Einspruch eingelegt.“

Gute Antwort: „[Mandant] hat fristgerecht Einspruch gegen den Bescheid [Aktenzeichen_1] eingelegt. Für die Begründung sollte [Mandant] …“

Schlechte Antwort: „Frau Müller hat Einspruch eingelegt …“ (erfundener Name) oder „Der Mandant hat …“ (Platzhalter verändert).
