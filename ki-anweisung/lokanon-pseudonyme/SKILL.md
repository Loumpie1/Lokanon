---
name: lokanon-pseudonyme
description: Umgang mit pseudonymisierten Texten aus Lokanon. Nutze diesen Skill immer, wenn ein Text oder eine Datei Platzhalter wie [PERSON_1], [FIRMA_2], [ORT_1], [ADRESSE_3], [AZ_1], [IBAN_1] oder [DATUM_2] enthält. Die Platzhalter sind Pseudonyme, die später lokal zurückübersetzt werden; sie müssen unverändert übernommen werden.
---

# Pseudonymisierte Texte aus Lokanon

Lokanon ersetzt vor dem Upload lokal alle personenbezogenen und vertraulichen Angaben durch Platzhalter. Der Schlüssel bleibt beim Nutzer. Die Texte enthalten deshalb keine echten Personendaten.

## Platzhalter-Format

`[LABEL_n]` mit Großbuchstaben, Unterstrich und laufender Nummer. Übliche Labels:

| Platzhalter | Bedeutung |
|---|---|
| `[PERSON_n]` | eine natürliche Person (Vor- und Nachname, auch Namensteile) |
| `[FIRMA_n]` | Unternehmen, Organisation |
| `[ORT_n]` | Ort, PLZ mit Ort |
| `[ADRESSE_n]` | Straße mit Hausnummer |
| `[TELEFON_n]`, `[EMAIL_n]`, `[URL_n]`, `[IP_n]` | Kontaktdaten |
| `[AZ_n]` | Aktenzeichen, Vorgangsnummer |
| `[GRUNDBUCH_n]` | Grundbuch-/Katasterangabe |
| `[IBAN_n]`, `[KONTO_n]`, `[KARTE_n]` | Bankdaten |
| `[VERS_NR_n]` | Versicherungsschein-, Schadennummer |
| `[STEUER_ID_n]`, `[STEUERNR_n]`, `[UST_ID_n]` | Steuernummern |
| `[SV_NR_n]`, `[KVNR_n]`, `[LANR_n]`, `[BSNR_n]` | Sozial-/Krankenversicherung, Arztnummern |
| `[AUSWEIS_n]`, `[PASS_n]`, `[FUEHRERSCHEIN_n]` | Ausweisdokumente |
| `[KFZ_n]`, `[FIN_n]` | Kennzeichen, Fahrgestellnummer |
| `[DATUM_n]` | personenbezogenes Datum (Geburt, Tod) |
| `[INTERN_n]`, `[MANUELL_n]` | vom Nutzer festgelegte Begriffe |

## Regeln

1. **Exakt übernehmen.** Jeder Platzhalter bleibt zeichengenau erhalten: Klammern, Großschreibung, Unterstrich, Nummer. Nicht umformulieren zu „Person 1“, „PERSON_1“ oder „[Person-1]“.
2. **Nicht auflösen, nicht raten.** Keine Namen, Firmen, Adressen oder Nummern erfinden. Keine Vermutungen äußern, wer sich hinter einem Platzhalter verbirgt, auch wenn der Kontext Hinweise gibt.
3. **Gleiche Nummer, gleiche Person.** `[PERSON_1]` ist überall im Vorgang dieselbe Person, auch über mehrere Dateien hinweg. Verschiedene Nummern sind verschiedene Personen.
4. **Beugung außerhalb der Klammer.** „[PERSON_1]s Fahrzeug“, „mit [FIRMA_2]“. Nie innerhalb der Klammer ändern.
5. **Neue Akteure neutral benennen.** Wenn du in einem Entwurf jemanden einführen musst: „die Gegenseite“, „der Sachverständige“, nie ein erfundener Name.
6. **Platzhalter in der Antwort verwenden.** Beziehe dich auf Personen und Sachen immer mit ihrem Platzhalter, damit die Antwort automatisch zurückübersetzt werden kann.
7. **Keine Datenschutz-Hinweise nötig.** Die Daten sind pseudonymisiert; Hinweise auf den Umgang mit Personendaten sind überflüssig.
8. **Dateinamen** mit Platzhaltern (z. B. `Fall1_Erbrecht_PERSON_2.md`) behandelst du genauso.

## Beispiel

Eingabe: „[PERSON_1], geb. [DATUM_1], wohnhaft [ADRESSE_1], [ORT_1], hat gegen den Bescheid [AZ_1] Einspruch eingelegt.“

Gute Antwort: „[PERSON_1] hat fristgerecht Einspruch gegen den Bescheid [AZ_1] eingelegt. Für die Begründung sollte [PERSON_1] …“

Schlechte Antwort: „Frau Müller hat Einspruch eingelegt …“ (erfundener Name) oder „Person 1 hat …“ (Platzhalter verändert).
