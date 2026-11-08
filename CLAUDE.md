# Lokanon – Hinweise für die Entwicklung

## Hilfe und Tour immer mitpflegen

Jede Änderung, die der Anwender sieht oder bedient, zieht im selben Commit Tour-Drehbuch
(`ui/einfuehrung/drehbuch.js`), Hilfetexte (`ui/einfuehrung/hilfetexte.js`), Anleitung
(`static/anleitung/index.html`) und Release-Notiz (`docs/pilot/Neu-in-<Version>.md`) mit. Neue Bedienelemente bekommen
einen `data-tour`-Anker. Ist die Hilfe nicht betroffen, steht `Hilfe: nicht betroffen` in der Commit-Nachricht.
Jede neue Anforderung unter `docs/anforderungen/` hat einen Abschnitt „Hilfe und Tour“.
Details und Wächter: [docs/entwicklung/hilfe-mitpflegen.md](docs/entwicklung/hilfe-mitpflegen.md).
