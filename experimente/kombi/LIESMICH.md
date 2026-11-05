# Kombi-Experiment: mehr Modelle, tiefere Schwellen, Zweitprüfer (05.11.2026)

Grundlage ist Erkennung v4 (Commit 84c33bf). Gemessen mit `kombi.py` auf den Entwicklungsteilen der öffentlichen
Daten (siehe `experimente/messlatte`) und den eigenen Sammlungen. Ergebnisse in `ergebnisse.json`.

| Variante | Arztbriefe R / P | Urteile R / P | Prüfsammlung R / P | Kanzlei R / P | Testsammlung R / P | Zeit Arztbriefe |
|---|---|---|---|---|---|---|
| v4 (spaCy + GLiNER) | 95,3 / 65,0 | 62,4 / 70,8 | 96,2 / 95,6 | 100 / 99,0 | 99,6 / 99,2 | 434 s |
| + GLiNER2-PII | 95,8 / 65,0 | 62,4 / 64,7 | 97,1 / 95,7 | 100 / 99,0 | 100 / 98,8 | 951 s |
| + GLiNER2-PII + Zweitprüfer 0,3 | 95,8 / 84,9 | 61,4 / 79,1 | 97,1 / 95,7 | 100 / 99,0 | 100 / 99,6 | 951 s + Prüfer |
| + GLiNER2-PII, Schwellen gesenkt | 95,8 / 63,2 | 63,0 / 47,2 | 97,1 / 93,6 | 100 / 97,0 | 100 / 97,6 | 895 s |
| … gesenkt + Zweitprüfer 0,3 | 95,8 / 82,7 | 61,9 / 54,4 | 97,1 / 93,6 | 100 / 97,0 | 100 / 98,4 | 895 s + Prüfer |

## Befund

- **Tiefere Schwellen lohnen nicht.** Sie bringen kaum Recall (Urteile +0,6 Punkte) und viele Fehlalarme.
- **GLiNER2-PII zusätzlich** findet je eine Angabe mehr in Prüf- und Testsammlung, bringt in Urteilen aber
  Fehlalarme. Es verdoppelt die Rechenzeit und braucht rund 0,8 GB mehr im Installer.
- **Der Zweitprüfer** filtert jetzt, wo die öffentlichen Daten echte Fehlalarme zeigen, deutlich: in Arztbriefen
  173 → 57, in Urteilen 65 → 31. Dafür verwirft er in den Urteilen zwei echte Namen (Recall −1,0). Ein
  verworfener Name ist ein Leck.

## Empfehlung

Nicht automatisch filtern. Der Zweitprüfer taugt als **Hinweis in „Prüfen“** („wahrscheinlich kein Name“), der
Fehlalarme schneller abwählbar macht, ohne etwas selbst zu verwerfen. GLiNER2-PII lohnt den Aufwand nur, wenn das
eigene Modell (experimente/eigenes_modell) nicht mehr bringt; dazu siehe dort.
