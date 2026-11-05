# Zweitprüfer für Namen und Firmen (05.11.2026)

Ein kleines Prüfmodell (deepset/gbert-base, Ja/Nein-Klassifikator) sieht jeden Namens- und Firmenvorschlag aus
KI-Modell oder Heuristik mit ±120 Zeichen Umgebung und entscheidet „anonymisieren ja/nein“. Vorschläge unter der
Schwelle fallen weg, ihre Weitergaben (Wiederholung, Namensteil, Vorgang) mit. Regeln und Feldtreffer prüft es nicht.

## Ablauf

1. `beispiele.py` erzeugt die Trainingsbeispiele (Erkennung mit niedrigen Schwellen, damit auch Grenzfälle dabei sind):
   - 25 Abwandlungen der Testsammlung mit zufälligen Namen aus den Wörterbuchlisten: 2019 Beispiele, Lösung bekannt.
   - Beispielsätze aus Wiktionary (kaikki.org, CC BY-SA): 1676 Kandidaten aus 5000 Sätzen.
2. `bewerten.py` sollte die Wiktionary-Kandidaten mit Qwen3-4B (llama-cpp) beschriften. **Das war unbrauchbar:**
   Nur 82 von 112 Antworten (73 %) stimmten, meist wurden echte Namen als „kein Name“ beschriftet. Die Kandidaten
   wurden deshalb von Hand gesichtet (478 nein, 1198 ja, `daten/wiki_bewertet.jsonl`).
3. `tokenizer_bauen.py` baut einmalig den Tokenizer (gbert hat nur `vocab.txt`), `trainieren.py` trainiert
   3 Epochen auf der CPU (88 min). 20 % der Wiktionary-Sätze bleiben als Test draußen.
4. `messen.py` misst Ende zu Ende mit den Zählregeln von `evaluate.py`. Prüfsammlung und Kanzleifälle waren nie im
   Training. Die Testsammlung schon, ihre Werte sind daher geschönt.

## Ergebnisse

Wiktionary-Test (339 Kandidaten aus Sätzen, die nicht im Training waren):

| Schwelle | echte Namen verworfen | Fehlalarme verworfen |
|---|---|---|
| 0,5 | 5 / 232 | 87 / 107 |
| 0,3 | 4 / 232 | 87 / 107 |
| 0,1 | 3 / 232 | 82 / 107 |
| 0,02 | 3 / 232 | 80 / 107 |

Unter 0,1 verworfen wurden „Diedr“, „Atreus Söhn“ und „Vier JahreszeitenHaus“ (zerschnittene Schreibweisen).

Ende zu Ende, Recall / Precision, normale Schwellen der Erkennung:

| Sammlung | ohne | Zweitprüfer 0,1 | Zweitprüfer 0,3 |
|---|---|---|---|
| Prüfsammlung | 96,2 / 94,6 | 96,2 / 94,6 | 96,2 / 95,7 |
| Kanzlei | 100 / 99,0 | 100 / 99,0 | 100 / 99,0 |
| Testsammlung (im Training) | 99,3 / 99,2 | 99,3 / 100 | 99,3 / 100 |

- Bei 0,3 fällt in der Prüfsammlung genau ein Fehlalarm weg („Orthopädische Gemeinschaftspraxis“). Die übrigen vier
  stammen aus Regeln oder Feldern („König-Heinrich-Platz 1“, „hat am 14“, „Amtsgericht Duisburg“) oder hält das
  Prüfmodell für plausibel („Kellgren-Lawrence Grad“).
- Mit niedrigen Erkennungsschwellen (0,25 / 0,3) steigt der Recall nicht. Den Recall-Gewinn, auf den man hoffen
  könnte, gibt es also nicht.
- Kein Namensteil ging verloren (eigens gezählt, siehe unten).

## Fehler in der ersten Fassung

Das erste Modell verwarf den Vornamen „Mia“ eines Kindes (p = 0,002). Ursache: Die Testsammlung markiert nur
„Mia Schneider“, nicht das einzelne „Mia“. Die Beschriftung machte daraus 50 Beispiele „kein Name“. `evaluate.py`
zählt solche Namensteile weder als Treffer noch als Fehlalarm, das Leck war in Recall und Precision unsichtbar.
Behoben: Namensteile gelten in `beispiele.py` als Name, und `messen.py` zählt verworfene Namensteile eigens. Das
fehlerhafte Modell liegt unter `daten/modell_v1_fehlerhaft` und wird nicht verwendet.

## Empfehlung: nicht ins Produkt, vorerst

- **Nutzen gering:** In den unabhängigen Sammlungen bleiben kaum Namens- oder Firmen-Fehlalarme übrig, die der
  Zweitprüfer treffen könnte (einer von 104 Angaben). Die restlichen Fehlalarme kommen aus Regeln und Feldern.
- **Risiko ungleich:** Ein verworfener echter Name ist ein Leck, ein Fehlalarm kostet einen Klick. Auch bei 0,1
  verwirft er noch rund 1 % echter Namen in fremdem Text.
- **Kosten:** Der Installer wird um rund 420 MB größer, dazu kommt die Laufzeit je Vorschlag (nicht gemessen).
- **Wenn überhaupt, dann als Hinweis:** In „Prüfen“ könnte er Karten mit „wahrscheinlich kein Name“ kennzeichnen,
  ohne sie automatisch abzuwählen. Das bringt kein Leckrisiko. Lohnt sich erst, wenn die gelernten Korrekturen aus
  echten Dokumenten zeigen, dass Namens- und Firmen-Fehlalarme dort häufig sind.

Trainingsdaten, Modell und Ergebnisse liegen in `daten/` und `modell/` und sind nicht im Repository.
