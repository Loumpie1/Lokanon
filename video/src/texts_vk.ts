// Alle Texte des Visitenkarten-Films (2:06). Hier ändern, dann neu rendern.

export const vk = {
  introUnterzeile: "Mandatsunterlagen sicher mit KI bearbeiten",
  credits: [
    { k: "Motion", v: "Bewegung mit Bedeutung" },
    { k: "Produkt", v: "Funktionen für Kanzleien" },
    { k: "Regie", v: "Ein roter Faden in drei Akten" },
  ],
  akte: [
    { nr: "Akt 1", titel: "Die Ausgangslage" },
    { nr: "Akt 2", titel: "Die Wende" },
    { nr: "Akt 3", titel: "Die Auflösung" },
  ],

  montag: {
    eyebrow: "Montag, 8:40 Uhr",
    titel: "Eine Akte, eine Frist.",
    lede: "Die Klageerwiderung muss raus. Ein KI-Assistent könnte in Minuten eine Fristenübersicht und einen ersten Entwurf liefern.",
    stats: [
      { wert: 42, label: "Seiten" },
      { wert: 14, label: "Tage Frist" },
      { wert: 1, label: "Name auf Seite 1" },
    ],
    caption: "Auf Seite 1 steht ein Name. Damit ist die Cloud tabu.",
  },

  konflikt: {
    eyebrow: "Der Konflikt",
    titel: "Was die KI nicht sehen darf",
    karten: [
      { para: "§ 203 StGB", titel: "Das Mandatsgeheimnis", text: "Wer anvertraute Geheimnisse offenbart, macht sich strafbar. Ein Name mit Sachverhalt im Chatfenster ist eine Offenbarung." },
      { para: "§ 43e BRAO", titel: "Dienstleister nur mit Vertrag", text: "Externe Dienste nur mit Verschwiegenheitsverpflichtung und nur, soweit erforderlich. Privat-Tarife der KI-Anbieter liefern das nicht." },
      { para: "Art. 28 DSGVO", titel: "Datenschutz bleibt Pflicht", text: "Personenbezogene Daten brauchen Vertrag und Verzeichnis. Was keinen Personenbezug mehr hat, braucht das nicht (EuGH C‑413/23 P)." },
    ],
    wende: "Die Wende: Wenn der Name die Kanzlei nie verlässt, bleibt das Geheimnis gewahrt – und die KI bekommt trotzdem den ganzen Fall.",
  },

  schluessel: {
    eyebrow: "Der Schlüssel",
    titel: "Zwei Sichten auf denselben Fall",
    links: {
      wer: "Was der KI-Anbieter sieht",
      zitat: "„[Person_1], [Adresse_1], [Aktenzeichen_1] – ein Verfahren vor dem Amtsgericht Mülheim.“",
      punkte: ["Sachverhalt und Rechtsfragen, vollständig", "Keine Namen, Anschriften, Kennzeichen, Konten", "Gleiches Format, Metadaten entfernt"],
    },
    rechts: {
      wer: "Was Sie sehen",
      zitat: "„Sabine Winter, Eppinghofer Straße 47, 14 VI 512/26.“",
      punkte: ["Rückübersetzung auf Wunsch, Schlüssel mit Passwort verschlüsselt", "Versteht auch „Person 1“ oder „[Person_1]s“", "Nichts davon verlässt den PC"],
    },
    caption: "Der Schlüssel bleibt verschlüsselt in der Kanzlei.",
  },

  funktionen: {
    eyebrow: "Visitenkarte des Produkts",
    titel: "Was Lokanon kann",
    kpis: [
      { wert: 98, einheit: " %", label: "Erkennungsrate, Referenzfälle" },
      { wert: 98, einheit: " %", label: "Treffergenauigkeit" },
      { wert: 0, einheit: " Bytes", label: "gehen zur Laufzeit ins Netz" },
      { wert: 3, einheit: "", label: "Schritte: Ablegen, Prüfen, Fertig" },
    ],
    tiles: [
      { icon: "pc", titel: "Läuft auf dem PC", text: "Kein Cloud-Dienst, keine Schnittstelle. Internet nur zur Installation." },
      { icon: "folder", titel: "Gleiche Datei, gleicher Name", text: "Aus Klage.docx wird Klage_anonymisiert.docx, im gleichen Format." },
      { icon: "toggle", titel: "Eine Person, eine Karte", text: "„Sabine Winter“ und „Frau Winter“ gehören zusammen. Ein Schalter lässt einen Begriff stehen." },
      { icon: "tag", titel: "Eigene Bezeichnungen", text: "[Mandantin] statt [Person_7], überall in allen Dateien und in der Antwort." },
      { icon: "scan", titel: "Scans inklusive", text: "Texterkennung für gescannte PDFs, auch gedreht. Sichtkopie aufrecht und geschwärzt." },
      { icon: "shield", titel: "Leck-Test vor jeder Ausgabe", text: "Jede Schwärzung wird gegengelesen. Bleibt ein Begriff, geht die Datei nicht raus." },
      { icon: "link", titel: "Fragt bei Zweifeln nach", text: "Passt ein Nachname zu zwei Personen, fragt Lokanon: wer ist gemeint?" },
      { icon: "key", titel: "Mehr nur auf Wunsch", text: "Rückübersetzung, KI-Anweisung, Vorgangsordner: unter Einstellungen → Erweitert." },
    ],
    caption: "Gebaut für den Schreibtisch, nicht für die IT-Abteilung.",
  },

  ablauf: {
    eyebrow: "Für wen",
    titel: "Drei Schritte, ein Bildschirm",
    chips: ["Einzelanwälte", "Kanzleien bis 10 Personen", "Rechtsanwaltsfachangestellte", "Syndizi"],
    schritte: [
      { titel: "Ablegen", text: "Dateien auf das Fenster ziehen oder den Aktenordner wählen. Die Erkennung startet von selbst." },
      { titel: "Prüfen", text: "Karten durchsehen, Schalter setzen, eigene Namen wie [Mandantin] vergeben." },
      { titel: "Fertig", text: "Je Datei eine Kopie im gleichen Format, mit dem Zusatz „_anonymisiert“." },
    ],
  },

  bildschirme: {
    caption: "Echte Bildschirme aus Lokanon 0.2.0, erfundener Fall.",
    seiten: [
      { datei: "shots/ablegen.jpg", titel: "Ablegen", punkte: ["Dateien auf die Fläche ziehen oder „Ordner wählen“", "PDF auch als Scan, Word, Excel, Text", "Oben immer: „Läuft lokal auf diesem PC“"] },
      { datei: "shots/pruefen.jpg", titel: "Prüfen", punkte: ["Eine Karte je Person, alle Schreibweisen zusammen", "Eigene Namen wie [Mandantin] per Klick", "Rückfrage, wenn ein Nachname zu zwei Personen passt"] },
      { datei: "shots/fertig.jpg", titel: "Fertig", punkte: ["Je Datei eine Kopie mit Zusatz „_anonymisiert“", "PDF echt geschwärzt, Leck-Test bestanden", "Beim Ordner liegen die Kopien neben den Originalen"] },
    ],
  },

  grenzen: {
    eyebrow: "Ehrlich gesagt",
    titel: "Was Lokanon nicht verspricht",
    punkte: [
      { titel: "Keine Erkennung ist vollständig.", text: "Indirekte Hinweise erkennt die Software nicht. Die Prüfung durch den Menschen ist Teil des Ablaufs." },
      { titel: "Pseudonym ist nicht anonym.", text: "Solange die Kanzlei den Schlüssel hat, bleibt für sie der Personenbezug. Für den Anbieter fehlt er." },
      { titel: "Scans sind nur so gut wie der Scan.", text: "Handschrift und Stempel können die Texterkennung täuschen. Sichtkopien nur nach Gegenprüfung." },
      { titel: "Pilotversion.", text: "Unsigniert, kein Praxis-Profil, Word-Kommentare werden noch nicht bereinigt." },
    ],
    caption: "Ein Werkzeug für Berufsgeheimnisträger nennt seine Grenzen.",
  },

  karten: {
    eyebrow: "Drei Handschriften",
    titel: "Die Visitenkarten hinter diesem Film",
    karten: [
      { rolle: "Motion Design", titel: "Bewegung, die etwas bedeutet", text: "Jede Animation zeigt eine Sache, die Lokanon tut.", rueck: "So ist es gebaut", punkte: ["Markierung → Platzhalter als Kernbewegung", "Eine Kurve, schnelle Einfahrt, weiches Ausklingen", "Staffelung in Leserichtung", "Der rote Faden ist die Person"], sig: "Bewegung ist Erklärung, nicht Effekt." },
      { rolle: "Product Owner", titel: "Funktionen für den Kanzleialltag", text: "Jede Funktion beantwortet eine Frage aus der Kanzlei.", rueck: "Was wir entschieden haben", punkte: ["Anwälte zuerst, Praxis-Profil später", "Gleiche Datei, gleicher Name, plus Zusatz", "Keine Scores: sicher, wahrscheinlich, unsicher", "Installer ohne Adminrechte, alles enthalten"], sig: "Verständlich für Fachangestellte." },
      { rolle: "Regie & Drehbuch", titel: "Ein roter Faden in drei Akten", text: "Die Person in der Akte ist die Hauptfigur.", rueck: "Das Drehbuch", punkte: ["Akt 1: eine Akte, ein Name, drei Regeln", "Akt 2: der Name verschwindet, der Fall bleibt", "Akt 3: die KI arbeitet, der Name bleibt zu Hause", "Die Grenzen stehen im Drehbuch"], sig: "Erst die Geschichte, dann die Liste." },
    ],
  },

  outro: {
    titel: "Pilotversion für Kanzleien",
    sub: "Windows 10/11 · pro Benutzer · ohne Adminrechte · ca. 2,8 GB",
    paket: [
      { tag: "exe", text: "Installer mit allen Sprachmodellen, läuft danach offline" },
      { tag: "html", text: "Anleitung, für Fachangestellte geschrieben" },
      { tag: "doc", text: "Pilot-Hinweis, Rückmeldebogen, rechtliche Vorlagen" },
      { tag: "txt", text: "KI-Anweisung und Claude-Skill" },
      { tag: "mp4", text: "Filme und Vorstellung, auch in Lokanon unter Einstellungen" },
    ],
    claim: "Lokanon. Läuft auf Ihrem PC.",
  },
} as const;
