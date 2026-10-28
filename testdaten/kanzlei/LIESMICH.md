# Testfälle Kanzlei (fiktiv)

Fünf erfundene Mandate aus Erb- und Verkehrsrecht der fiktiven Kanzlei Lehmkuhl & Partner.
Personen, Telefonnummern, E-Mails (example.com), Konten, Kennzeichen und Nummern sind erfunden.
Echt sind nur Straßennamen, Städte und Gerichtsadressen. Die IBANs haben gültige Prüfziffern.

| Datei | Inhalt | Prüft vor allem |
|---|---|---|
| Fall1 …Brinkhoff.docx | Mandatsnotiz Testamentsanfechtung | Namen, Namensteile, Name „Dr. Essen“ = Stadt, Grundbuch, Metadaten (Autor gesetzt) |
| Fall2 …Haverkamp.md | Pflichtteilsverlangen | Steuer-ID, Steuernummer, 2 IBANs, Depotnummer |
| Fall2 …Haverkamp.xlsx | Nachlassverzeichnis | Excel-Zellen, Formel bleibt erhalten |
| Fall3 …Schulte.docx | Unfallaufnahme | Kennzeichen, FIN, Versicherungs-/Schadennummern, Name „Bach“ |
| Fall4 …Engel.pdf | Einspruch Bußgeld | PDF-Extraktion, Führerscheinnummer, indirekte Identifizierung |
| Fall5 …Rhein.txt | E-Mail-Verlauf | Spitzname „Wolle“, „Rhein“ vs. Rhein-Ruhr-Zentrum, Anhänger-Kennzeichen |

Bewusst nicht markiert (sollen stehen bleiben): Kanzlei, Anwältin, Gerichte, Behörden, Versicherer,
Krankenhäuser, Datumsangaben ohne Personenbezug. Werden sie maskiert, zählen sie als Fehlalarm.

`INDIREKT` markiert Stellen, die ohne Namen auf eine Person schließen lassen – die Basis-Version
findet sie nicht; das ist der Testfall für den späteren LLM-Check.

## Messen

```
python evaluate.py PFAD\testfaelle\referenz_markierungen.jsonl
```

`generate.py` erzeugt alles neu (muss neben dem Ordner anon-lokal liegen).
