# Lokanon – Produktvideos (Remotion)

Zwei Kompositionen, beide 1920 × 1080, 30 fps, ohne Ton:

| Komposition | Länge | Datei | Befehl |
| --- | --- | --- | --- |
| `LokanonTeaser` | 30 s | `out/lokanon-teaser.mp4` | `npm run build` |
| `LokanonVisitenkarte` | 2:06 | `out/lokanon-visitenkarte.mp4` | `npm run build:visitenkarte` |
| `LokanonMotion` | 1:14 | `out/lokanon-motion.mp4` | `npm run build:motion` |

## Motion-Film mit motion-anything

`LokanonMotion` ist ein Motion-Design-Film, der mit Rezepten aus
[motion-anything](https://github.com/nexu-io/motion-anything) (nexu-io, Apache-2.0) gebaut ist. Die Seite liegt
unter `public/ma/index.html` und folgt der „einfrierbaren Zeitleiste“ von motion-anything
(`window.__maTimeline.seek(t)`): alle Bewegungen sind Web-Animations-Keyframes, Shader und Zähler laufen über eine
virtuelle Uhr. `src/LokanonMotion.tsx` lädt die Seite in einem iframe, ruft je Bild `seek()` auf und lässt Remotion
fotografieren; so kommen auch WebGL-Shader bildgenau ins MP4 (Render mit `--gl=angle`).

Verwendete Rezepte (`public/ma/recipes/`): `_fx/shaderbg.js` + `strands` (mit Lokanon-Palette, Datei
`strands-lokanon.js`), `shiny-text`, `star-border`, `count-up`; als Bewegungsvokabular außerdem `kinetic-headline`
(rise/pop/blur, Staffelung 40–70 ms), `bounce-cards`, `true-focus`, umgesetzt als Keyframes. Timing und Easing folgen
`MOTION-SPEC.md` von motion-anything. Öffnet man `public/ma/index.html` direkt im Browser, läuft der Film in Schleife
(`?noloop` hält ihn an, `?noshader` lässt den Shader weg).

**Ton:** Die Tonspur entsteht per Code, ohne Fremdaufnahmen (`python tools\sound.py` mit dem Lokanon-venv, braucht nur
numpy): ein Ambient-Bett aus vier Akkorden in D-Moll mit Sub-Bass, darüber kurze Klänge auf die Schlüsselmomente
(Schild, Buchstaben, Markierungen, Platzhalter, Schalter, Dokumentflug, Rückübersetzung, Kennzahlen, Bildschirme,
Abspann); die Sekundenangaben stehen in `tools/sound.py` und entsprechen der Zeitleiste in `public/ma/index.html`.
Ausgabe `public/ma/audio/lokanon-motion.wav`, daraus `lokanon-motion.mp3` (Remotions ffmpeg kann kein M4A schreiben):
`npx remotion ffmpeg -i public/ma/audio/lokanon-motion.wav -c:a libmp3lame -b:a 192k public/ma/audio/lokanon-motion.mp3`.
Teaser und Visitenkarten-Film sind weiterhin stumm.

Der Visitenkarten-Film erzählt die Marketing-Geschichte in drei Akten (Ausgangslage, Wende, Auflösung) und zeigt
danach Funktionen, Ablauf, echte Bildschirme (`public/shots/`), Grenzen und die drei Visitenkarten der Gewerke.
Seine Texte stehen in `src/texts_vk.ts`, die Szenen in `src/scenes/vk/`, die Szenenfolge mit Längen in
`src/LokanonVisitenkarte.tsx` (`SZENEN`). Die Szenen „Erkennen und Prüfen“ und „KI und Rückübersetzung“ sind
dieselben wie im Teaser.

## Teaser

30-Sekunden-Teaser, 1920 × 1080, 30 fps, ohne Ton. Alles ist Vektorgrafik in React
(Remotion), es gibt keine Bild- oder Videodateien. Die Schriften Source Sans 3 und
Source Serif 4 liegen als woff2 in `public/fonts/` (SIL Open Font License), es wird
nichts aus dem Internet geladen.

## Rendern

Voraussetzung: Node 18+ und npm. Im Ordner `video/`:

```bash
npm install
npm run build
```

Ergebnis: `out/lokanon-teaser.mp4` (H.264, CRF 18). Ein Rendern dauert auf einem
normalen Laptop etwa zwei bis vier Minuten.

Weitere Befehle:

| Befehl | Zweck |
| --- | --- |
| `npm run dev` | Remotion Studio im Browser, Vorschau mit Zeitleiste |
| `npm run stills` | drei Einzelbilder nach `out/` (Frames 45, 360, 700) |
| `npx remotion still src/index.ts LokanonTeaser out/bild.png --frame=300` | beliebiges Einzelbild |

Hinweis OneDrive: `node_modules` ist eine Verzeichnisverknüpfung (Junction) nach
`C:\Users\david\Lokanon\video-node_modules`, damit der Sync nicht bremst. Wird der
Ordner auf einen anderen Rechner kopiert, die Verknüpfung löschen und `npm install`
neu ausführen.

## Texte ändern

Alle sichtbaren Texte stehen in **`src/texts.ts`**:

- `texts` – Wortmarke, Unterzeilen, die fünf Bildunterschriften, Claim, Beschriftungen
  der Prüfkarten und des Chatfensters.
- `marks` – die erfundenen Beispieldaten im Musterbrief (Name, Adresse, Aktenzeichen)
  und ihre Platzhalter wie `[PERSON_1]`.
- `brief` – die Textbausteine des Musterbriefs.
- `antwort` – die KI-Antwort, zeilenweise.

Nach einer Änderung einfach neu rendern. Längere Bildunterschriften passen bis etwa
60 Zeichen in eine Zeile; die Schriftgröße steht in `src/theme.ts` (`layout.captionSize`).

## Aufbau

```
src/
  index.ts            Einstieg (registerRoot)
  Root.tsx            Komposition „LokanonTeaser“ (900 Frames)
  LokanonTeaser.tsx   Szenenfolge, Hintergrundfarbe, Kopfzeile
  texts.ts            alle Texte und Beispieldaten
  theme.ts            Farben, Schriften, Easing, Layoutmaße
  fonts.ts            lädt die Schriften aus public/fonts
  scenes/
    Intro.tsx         0–4 s   Schild zeichnet sich, Wortmarke, Unterzeile
    DocumentScene.tsx 4–15 s  Erkennen (Markierungen) und Prüfen (Chips, Schalter)
    ChatScene.tsx     15–26 s Dokument fliegt in den Chat, Antwort, Rückübersetzung
    Outro.tsx         26–30 s Wortmarke, Claim, Unterzeile
  components/
    MorphSpan.tsx     Textstück, das sich in einen Platzhalter-Chip verwandelt
    Document.tsx      stilisierter Musterbrief
    Icons.tsx         Schild, Schloss, Schlüssel (SVG)
    Toggle.tsx        Schalter
    Caption.tsx       Bildunterschrift
    Header.tsx        Kopfzeile der hellen Szenen
    Lockup.tsx        Schild + Wortmarke
```

Zeitpunkte innerhalb einer Szene sind Frame-Konstanten am Anfang der jeweiligen
Szenendatei (zum Beispiel `HL`, `MO`, `TOGGLE_AT` in `DocumentScene.tsx`). Die
Szenenstarts stehen in `LokanonTeaser.tsx` (`SCENES`).

Farben: Tiefblau `#16365C`, Aktionsblau `#1F5FA8`, Petrol `#0E9F8A`, Hintergrund
`#F6F8FB`, Text `#1A2433`; Markierungen Person `#FFD6D6`, Firma `#D6E4FF`,
Adresse `#D9F2E3`, Nummern `#FFF3C4` (alle in `src/theme.ts`).

## Nicht enthalten

- Kein Ton. Eine lizenzfreie Tonspur lässt sich mit `<Audio src={staticFile("musik.mp3")} />`
  in `LokanonTeaser.tsx` ergänzen, sobald eine Datei in `public/` liegt.
- Keine 9:16-Variante. Die Szenen 2–5 sind zweispaltig aufgebaut und bräuchten
  für Hochkant ein eigenes Layout.
