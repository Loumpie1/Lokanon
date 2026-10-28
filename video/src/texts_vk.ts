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
      zitat: "„[PERSON_1], [ADRESSE_1], [AZ_1] – ein Verfahren vor dem Amtsgericht Mülheim.“",
      punkte: ["Sachverhalt und Rechtsfragen, vollständig", "Keine Namen, Anschriften, Kennzeichen, Konten", "Dateinamen ohne Mandantennamen"],
    },
    rechts: {
      wer: "Was Sie sehen",
      zitat: "„Sabine Winter, Eppinghofer Straße 47, 14 VI 512/26.“",
      punkte: ["Schlüsseldatei je Vorgang, mit Passwort verschlüsselt", "Rückübersetzung versteht auch „Person 1“", "Nichts davon verlässt den PC"],
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
      { wert: 4, einheit: "", label: "Schritte bis zur Antwort" },
    ],
    tiles: [
      { icon: "pc", titel: "Läuft auf dem PC", text: "Kein Cloud-Dienst, keine Schnittstelle. Internet nur zur Installation." },
      { icon: "folder", titel: "Vorgangsordner in der Akte", text: "Originale, Anonymisiert, Für die KI, Prüfbericht. Keine IT-Sprache." },
      { icon: "toggle", titel: "Prüfen mit Schaltern", text: "Sicher, wahrscheinlich, unsicher. Ein Klick lässt einen Begriff stehen." },
      { icon: "tag", titel: "Eigene Bezeichnungen", text: "[MANDANTIN] statt [PERSON_7], überall im Vorgang und in der Antwort." },
      { icon: "scan", titel: "Scans inklusive", text: "Texterkennung für gescannte PDFs, auch gedreht. Sichtkopie aufrecht und geschwärzt." },
      { icon: "shield", titel: "Leck-Test vor jeder Ausgabe", text: "Jede Schwärzung wird gegengelesen. Bleibt ein Begriff, geht die Datei nicht raus." },
      { icon: "link", titel: "Vorgangsweit konsistent", text: "Nachnamen, Genitiv, Wiederholungen über alle Dateien eines Vorgangs." },
      { icon: "key", titel: "Schlüssel und Rückübersetzung", text: "Verschlüsselt auf dem PC. Die KI-Antwort wird mit einem Klick zurückübersetzt." },
    ],
    caption: "Gebaut für den Schreibtisch, nicht für die IT-Abteilung.",
  },

  ablauf: {
    eyebrow: "Für wen",
    titel: "Vier Schritte, ein Doppelklick",
    chips: ["Einzelanwälte", "Kanzleien bis 10 Personen", "Rechtsanwaltsfachangestellte", "Syndizi"],
    schritte: [
      { titel: "Vorgang anlegen", text: "Dateien ablegen oder Aktenordner wählen. Die Analyse startet von selbst." },
      { titel: "Prüfen", text: "Karten durchsehen, Schalter setzen, Bezeichnungen vergeben." },
      { titel: "Fertigstellen", text: "Dateien für die KI erzeugen, Leck-Test lesen, Schlüssel sichern." },
      { titel: "Antwort", text: "KI-Antwort einfügen, Platzhalter werden ersetzt." },
    ],
  },

  bildschirme: {
    caption: "Echte Bildschirme aus Lokanon 2.0, erfundener Vorgang.",
    seiten: [
      { datei: "shots/start.jpg", titel: "Vorgang anlegen", punkte: ["Name vergeben, Dateien ablegen oder Aktenordner wählen", "Alternativ Text einfügen, etwa eine E-Mail", "Unten links immer: „Läuft lokal auf diesem PC“"] },
      { datei: "shots/pruefen.jpg", titel: "Prüfen", punkte: ["Jeder Treffer eine Karte mit Schalter", "„Bitte ansehen“ listet Unsicheres in einfachen Worten", "Rechts das Original mit Etiketten, auf Wunsch die KI-Fassung"] },
      { datei: "shots/fertigstellen.jpg", titel: "Fertigstellen", punkte: ["PDF-Sichtkopie geschwärzt, Word und Excel ohne Metadaten", "Erst nach dem Haken „geprüft“ entstehen Dateien", "KI-Anweisung zum Kopieren gleich daneben"] },
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
      { rolle: "Product Owner", titel: "Funktionen für den Kanzleialltag", text: "Jede Funktion beantwortet eine Frage aus der Kanzlei.", rueck: "Was wir entschieden haben", punkte: ["Anwälte zuerst, Praxis-Profil später", "Originalname lokal, bereinigt für die KI", "Keine Scores: sicher, wahrscheinlich, unsicher", "Installer ohne Adminrechte, alles enthalten"], sig: "Verständlich für Fachangestellte." },
      { rolle: "Regie & Drehbuch", titel: "Ein roter Faden in drei Akten", text: "Die Person in der Akte ist die Hauptfigur.", rueck: "Das Drehbuch", punkte: ["Akt 1: eine Akte, ein Name, drei Regeln", "Akt 2: der Name verschwindet, der Fall bleibt", "Akt 3: die Antwort kehrt zurück, der Schlüssel bleibt", "Die Grenzen stehen im Drehbuch"], sig: "Erst die Geschichte, dann die Liste." },
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
      { tag: "mp4", text: "Produktvideo für die Vorstellung in der Kanzlei" },
    ],
    claim: "Lokanon. Läuft auf Ihrem PC.",
  },
} as const;
