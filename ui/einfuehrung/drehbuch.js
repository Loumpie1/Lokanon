/* Drehbuch der Einführung (docs/anforderungen/lernen-und-loeschfristen.md, Abschnitte 9 und 10).
   Regel (docs/entwicklung/hilfe-mitpflegen.md): Wer die Oberfläche ändert, zieht dieses Drehbuch im selben Commit
   mit. tests/test_hilfe.py prüft, dass jedes ziel als data-tour-Anker in ui/app.js existiert.

   Schritt: kapitel, ziel (data-tour-Anker; mit name: [data-name="…"]), titel, text oder hilfe (Schlüssel aus
   hilfetexte.js), art "zeigen" (Weiter) oder "tun" (wartet auf das Ereignis warten, das ui/app.js mit melde()
   schickt; bedingung prüft dessen Angaben), aufgabe, vorher/vormachen/nachher (async, bekommen LokanonApp),
   ueberspringen, seit (Version, für die Tour „Neu in …“). */
(() => {
  const warte = (ms) => new Promise((r) => setTimeout(r, ms));
  const $ = (s, c = document) => c.querySelector(s);
  const klick = async (sel, c = document) => { for (let i = 0; i < 20; i++) { const e = $(sel, c); if (e) { e.click(); return; } await warte(100); } };
  // Originaltext eines Dokuments aus der markierten Ansicht (ohne Platzhalter-Etiketten)
  const textVon = (html) => { const d = document.createElement("div"); d.innerHTML = html; d.querySelectorAll("sup.ph").forEach((x) => x.remove()); return d.textContent; };
  async function markiereUeberApi(app, wort, art) {
    const text = textVon(app.state.z.dokumente[0].markiert_html); const s = text.indexOf(wort);
    const a = await app.api("/auswahl", { json: { dok: 0, s, e: s + wort.length, art } });
    const stellen = a.dateien.flatMap((f) => f.stellen.filter((st) => !st.schon).map((st) => ({ dok: f.i, s: st.s, e: st.e })));
    if (stellen.length) app.state.z = await app.api("/markieren", { json: { begriff: a.begriff, art, stellen, ursprung: { dok: 0, s: a.s } } });
  }
  async function anonymisiereUndWarte(app) {
    await app.api("/anonymisieren", { method: "POST" });
    for (let i = 0; i < 100; i++) { const f = await app.api("/fortschritt"); if (!f.laeuft) break; await warte(300); }
    await app.laden(); app.zeige("vorgang");
  }
  const imBeispiel = async (app) => { if (!app.state.z || !app.state.z.uebung || !app.state.z.dokumente.length || app.state.z.ergebnis) await app.beispielLaden(); else app.zeige("vorgang"); };

  const kapitel = [
    { id: "ablegen", nr: 1, titel: "Dateien ablegen", vorbereiten: async (app) => app.zeige("start") },
    { id: "pruefen", nr: 2, titel: "Prüfen", vorbereiten: imBeispiel },
    { id: "markieren", nr: 3, titel: "Übersehenes markieren", vorbereiten: imBeispiel },
    { id: "anonymisieren", nr: 4, titel: "Anonymisieren", vorbereiten: imBeispiel },
    { id: "merken", nr: 5, titel: "Merken für künftige Dokumente", vorbereiten: async (app) => {
      if (app.state.z && app.state.z.ergebnis && app.state.z.ergebnis.merken.length && !app.state.z.ergebnis.gemerkt) { app.zeige("vorgang"); return; }
      await app.beispielLaden(); await markiereUeberApi(app, "Falkenhorst", "PROJEKT"); await markiereUeberApi(app, "48213", "KENNNUMMER"); await anonymisiereUndWarte(app); } },
    { id: "faelle", nr: 6, titel: "Fälle und Einstellungen", vorbereiten: async (app) => app.zeige("start") },
    { id: "gespeichert", nr: 7, titel: "Gespeicherte Angaben: verwalten und löschen", vorbereiten: async (app) => app.zeige("start") },
  ];

  const schritte = [
    // 1 Ablegen
    { kapitel: "ablegen", ziel: "nav-start", art: "zeigen", seit: "0.3.0", titel: "Willkommen",
      text: "Diese Einführung zeigt Lokanon an einem erfundenen Beispiel. Alles, was Sie jetzt tun, bleibt in einem Übungsvorgang; Ihre eigenen Daten sind nicht betroffen. Links stehen die Bereiche, oben die Befehle." },
    { kapitel: "ablegen", ziel: "neu-dateien", art: "zeigen", seit: "0.3.0", titel: "Dateien ablegen",
      text: "Hier legen Sie Dateien ab: PDF, Word, Excel, Text, auch gescannte Seiten. Sie können Dateien auch einfach in das Fenster ziehen." },
    { kapitel: "ablegen", ziel: "neu-ordner", art: "zeigen", seit: "0.3.0", titel: "Ordner öffnen",
      text: "Mit einem Ordner landen die anonymisierten Kopien direkt neben den Originalen. Die Originale verändert Lokanon nie." },
    { kapitel: "ablegen", ziel: "fristen", art: "zeigen", seit: "0.4.0", titel: "Fälle und Fristen",
      text: "Hier sehen Sie, welche gemerkten Angaben bald gelöscht werden, und können sie verlängern. Mehr dazu in Kapitel 7." },
    { kapitel: "ablegen", ziel: null, art: "zeigen", seit: "0.3.0", titel: "Das Beispiel",
      text: "Lokanon legt jetzt ein erfundenes Schreiben und eine E-Mail ab und erkennt die Personendaten. Beim echten Arbeiten dauert das je nach Umfang einige Sekunden.",
      nachher: (app) => app.beispielLaden() },
    // 2 Prüfen
    { kapitel: "pruefen", ziel: "pruefen-kopf", art: "zeigen", seit: "0.3.0", titel: "Was Lokanon gefunden hat",
      text: "Rechts stehen alle Angaben, die ersetzt werden, nach Art geordnet. Darunter der Fall: Lokanon hat das Aktenzeichen aus dem Schreiben genommen." },
    { kapitel: "pruefen", ziel: "hinweis-ansehen", art: "zeigen", seit: "0.3.0", titel: "Bitte ansehen",
      text: "Lokanon ersetzt im Zweifel lieber zu viel. Was unsicher ist, steht hier und ist in der Liste gelb beschriftet." },
    { kapitel: "pruefen", ziel: "zeile", name: "Morbus Crohn", art: "tun", warten: "karte-aus", bedingung: (d) => d.name === "Morbus Crohn", seit: "0.3.0",
      titel: "Ein Fehlalarm", text: "„Morbus Crohn“ ist eine Krankheit, kein Name.", aufgabe: "Nehmen Sie den Haken bei „Morbus Crohn“ heraus.",
      vormachen: () => klick('[data-tour="zeile"][data-name="Morbus Crohn"] input') },
    { kapitel: "pruefen", ziel: "zeile", name: "Sabine Winter", art: "tun", warten: "karte-gewaehlt", bedingung: (d) => d.name === "Sabine Winter", seit: "0.3.0",
      titel: "Zur Stelle springen", text: "Ein Klick auf eine Zeile zeigt die Stelle im Dokument und klappt die Einzelheiten auf.", aufgabe: "Klicken Sie auf „Sabine Winter“.",
      vormachen: () => klick('[data-tour="zeile"][data-name="Sabine Winter"] .name') },
    { kapitel: "pruefen", ziel: "dokument", art: "zeigen", seit: "0.4.0", titel: "Das Fähnchen",
      text: "Im Dokument zeigt ein Fähnchen den Platzhalter, der in der Kopie steht, und wie oft die Angabe vorkommt. „Im Dokument zeigen“ springt zur nächsten Stelle." },
    { kapitel: "pruefen", ziel: "platzhalter-vorschlaege", art: "tun", warten: "bezeichnung", seit: "0.3.0", titel: "Sprechende Platzhalter",
      text: "Statt [Person_1] kann in der Kopie [Mandantin] stehen. Die KI versteht den Text dann besser.", aufgabe: "Wählen Sie „Mandantin“.",
      vorher: async () => { if (!$('[data-tour="platzhalter-vorschlaege"]')) await klick('[data-tour="zeile"][data-name="Sabine Winter"] .name'); },
      vormachen: () => klick('[data-tour="platzhalter-vorschlaege"] [data-v="Mandantin"]') },
    // 3 Markieren
    { kapitel: "markieren", ziel: "befehl-markieren", art: "zeigen", seit: "0.4.0", titel: "Übersehenes markieren", hilfe: "markieren" },
    { kapitel: "markieren", ziel: "dokument", art: "tun", warten: "auswahl", bedingung: (d) => /falkenhorst/i.test(d.begriff || ""), seit: "0.4.0",
      titel: "Lokanon hat etwas übersehen", text: "Das „Projekt Falkenhorst“ verrät, wo die Mandantin arbeitet.",
      aufgabe: "Markieren Sie im Schreiben das Wort „Falkenhorst“, zum Beispiel mit einem Doppelklick darauf.",
      vorher: async (app) => { if (app.state.docIndex !== 0) { app.state.docIndex = 0; app.render(); } },
      vormachen: (app) => app.markiereWort("Falkenhorst") },
    { kapitel: "markieren", ziel: "markier-zuordnung", art: "zeigen", seit: "0.4.0", titel: "Ersetzen durch",
      text: "Meist bekommt ein markiertes Wort einen neuen Platzhalter. Ist es ein Spitzname oder Kürzel einer schon gefundenen Person oder Firma, wählen Sie hier deren Platzhalter. „Abbrechen“ oder Esc schließt das Fenster, ohne etwas zu ändern.",
      vorher: async (app) => { if (!$('[data-tour="markier-zuordnung"]')) { await app.markiereWort("Falkenhorst"); await warte(500); } } },
    { kapitel: "markieren", ziel: "markierfenster", art: "tun", warten: "markiert", bedingung: (d) => /falkenhorst/i.test(d.begriff || ""), seit: "0.4.0",
      titel: "Art wählen, überall ersetzen", text: "Lokanon schlägt eine Art vor und zeigt, wie oft der Begriff vorkommt, hier auch in der E-Mail.",
      aufgabe: "Wählen Sie „Projekt oder Kürzel“ und dann „Überall ersetzen“.",
      vormachen: async () => { await klick('[data-tour="markierfenster"] [data-k="PROJEKT"]'); await warte(500); await klick('[data-tour="markier-ueberall"]'); } },
    { kapitel: "markieren", ziel: "dokument", art: "tun", warten: "markiert", bedingung: (d) => d.begriff === "48213", seit: "0.4.0",
      titel: "Regel statt Nummer", text: "Auch die Mandantennummer 48213 fehlt. Weil davor „Mandantennr.:“ steht, kann Lokanon später die Bezeichnung lernen statt der Nummer.",
      aufgabe: "Markieren Sie 48213, wählen Sie „Kennnummer“ und dann „Ersetzen“.",
      vormachen: async (app) => { await app.markiereWort("48213"); await warte(500); await klick('[data-tour="markierfenster"] [data-k="KENNNUMMER"]'); await warte(500); await klick('[data-tour="markier-ueberall"]'); } },
    { kapitel: "markieren", ziel: "befehl-rueckgaengig", art: "zeigen", seit: "0.3.0", titel: "Rückgängig",
      text: "Jede Änderung beim Prüfen lässt sich mit „Rückgängig“ oder Strg+Z zurücknehmen." },
    { kapitel: "markieren", ziel: "nachtrag", art: "zeigen", seit: "0.3.0", titel: "Oder eintippen",
      text: "Begriffe lassen sich auch hier eintragen. Lokanon sucht sie dann in allen Dateien." },
    // 4 Anonymisieren
    { kapitel: "anonymisieren", ziel: "befehl-anonymisieren", art: "tun", warten: "anonymisiert", seit: "0.4.0", titel: "Kopien erstellen",
      text: "Wenn alles stimmt, schreibt dieser Knopf die anonymisierten Kopien; er zeigt, wie viele Angaben ersetzt werden. Denselben Knopf gibt es unten am Ende der Liste. Danach prüft Lokanon, ob noch Originaltext in den Kopien steht.",
      aufgabe: "Klicken Sie auf „Anonymisierte Kopien erstellen“.", vormachen: () => klick('[data-tour="befehl-anonymisieren"]') },
    { kapitel: "anonymisieren", ziel: "ergebnis-dateien", art: "zeigen", seit: "0.3.0", titel: "Gegengeprüft",
      text: "Jede Kopie ist gegengeprüft. Fände Lokanon noch einen Namen, gäbe es keine Kopie, sondern einen Hinweis, woran es lag und was zu tun ist." },
    { kapitel: "anonymisieren", ziel: "datei-oeffnen", art: "zeigen", seit: "0.4.0", titel: "Kopie öffnen",
      text: "„Öffnen“ zeigt eine Kopie direkt im passenden Programm, etwa Word. „Ordner öffnen“ oben zeigt, wo die Kopien liegen." },
    { kapitel: "anonymisieren", ziel: "befehl-ki", art: "zeigen", seit: "0.3.0", titel: "Für die KI",
      text: "Diese Anweisung sagt der KI, dass sie die Platzhalter stehen lassen soll. Ein- und ausschalten unter Einstellungen → Erweitert." },
    { kapitel: "anonymisieren", ziel: "befehl-zurueck", art: "zeigen", seit: "0.3.0", titel: "Antwort zurückübersetzen",
      text: "Die Antwort der KI enthält Platzhalter. Hier setzt Lokanon die Originale wieder ein, nur auf diesem PC." },
    // 5 Merken
    { kapitel: "merken", ziel: "merken", art: "zeigen", seit: "0.4.0", titel: "Künftig vorschlagen?",
      text: "Was Sie selbst markiert haben, kann Lokanon sich merken und in künftigen Dokumenten vorschlagen. Lokanon fragt einmal am Ende, nicht bei jeder Markierung." },
    { kapitel: "merken", ziel: "merken-fall", art: "zeigen", seit: "0.4.0", titel: "Der Fall", hilfe: "fall" },
    { kapitel: "merken", ziel: "merken-liste", art: "zeigen", seit: "0.4.0", titel: "Was gemerkt wird",
      text: "Projekte und Kürzel haben keinen Personenbezug und keine Frist. Bei der Mandantennummer lernt Lokanon die Bezeichnung „Mandantennr.“ statt der Nummer, also keine Personendaten." },
    { kapitel: "merken", ziel: "merken-warum", art: "zeigen", seit: "0.4.0", titel: "Warum?", hilfe: "speichern_warum" },
    { kapitel: "merken", ziel: "merken-ok", art: "tun", warten: "gemerkt", seit: "0.4.0", titel: "Merken",
      text: "Bestätigen Sie mit einem Klick. Einzelnes lässt sich vorher abwählen.", aufgabe: "Klicken Sie auf „Merken“.", vormachen: () => klick('[data-tour="merken-ok"]') },
    // 6 Fälle und Einstellungen
    { kapitel: "faelle", ziel: "nav-faelle", art: "tun", warten: "ansicht-faelle", seit: "0.4.0", titel: "Fälle und gelernte Angaben",
      text: "Hier steht alles, was Lokanon sich gemerkt hat, nach Fall geordnet.", aufgabe: "Öffnen Sie „Fälle und gelernte Angaben“.",
      ueberspringen: (app) => app.state.ansicht === "faelle", vormachen: () => klick('[data-tour="nav-faelle"]') },
    { kapitel: "faelle", ziel: "faelle", art: "zeigen", seit: "0.4.0", titel: "Ihre Fälle",
      text: "Je Fall: wie viele Angaben, wann sie gelöscht werden und ob das Mandat noch läuft. Ein Klick klappt den Fall auf." },
    { kapitel: "faelle", ziel: "loeschprotokoll", art: "zeigen", seit: "0.4.0", titel: "Löschprotokoll", hilfe: "loeschprotokoll" },
    { kapitel: "faelle", ziel: "nav-einstellungen", art: "tun", warten: "ansicht-einstellungen", seit: "0.3.0", titel: "Einstellungen",
      text: "Hier stellen Sie Ihre Kanzlei, die Erkennung und die Ausgabe ein.", aufgabe: "Öffnen Sie die Einstellungen.", vormachen: () => klick('[data-tour="nav-einstellungen"]') },
    // „Neu in …“ überspringt den Schritt „Einstellungen“ (seit 0.3.0): dann selbst dorthin wechseln
    { kapitel: "faelle", ziel: "aufbewahrung", art: "zeigen", seit: "0.4.0", titel: "Aufbewahrung", hilfe: "aufbewahrung",
      vorher: async (app) => { if (app.state.ansicht !== "einstellungen") app.zeige("einstellungen", "aufbewahrung"); } },
    // 7 Gespeicherte Angaben
    { kapitel: "gespeichert", ziel: "nav-faelle", art: "zeigen", seit: "0.4.0", titel: "Warum Lokanon sich etwas merkt", hilfe: "speichern" },
    { kapitel: "gespeichert", ziel: "nav-faelle", art: "tun", warten: "ansicht-faelle", seit: "0.4.0", titel: "Die Übersicht",
      text: "Im Übungsvorgang gibt es drei erfundene Fälle.", aufgabe: "Öffnen Sie „Fälle und gelernte Angaben“.",
      ueberspringen: (app) => app.state.ansicht === "faelle", vormachen: () => klick('[data-tour="nav-faelle"]') },
    { kapitel: "gespeichert", ziel: "fall", name: "3 O 1120/26", art: "tun", warten: "fall-auf", bedingung: (d) => d.name === "3 O 1120/26", seit: "0.4.0",
      titel: "Warum ein Fall", hilfe: "fall", aufgabe: "Klappen Sie den Fall 3 O 1120/26 auf.",
      ueberspringen: (app) => [...app.state.auf].some((id) => { const f = (app.state.faelle || { faelle: [] }).faelle.find((x) => x.id === id); return f && f.name === "3 O 1120/26"; }),
      vormachen: () => klick('[data-tour="fall"][data-name="3 O 1120/26"] .fall-kopf') },
    { kapitel: "gespeichert", ziel: "fall", name: "3 O 1120/26", art: "tun", warten: "fall-verlaengert", seit: "0.4.0",
      titel: "Warum eine Frist", hilfe: "frist", aufgabe: "Das Mandat läuft noch: Klicken Sie auf „Verlängern“ und wählen Sie „Bis auf Widerruf“.",
      vormachen: async () => { await klick('[data-tour="fall"][data-name="3 O 1120/26"] [data-tour="fall-verlaengern"]'); await warte(300); await klick('[data-tour="verlaengern-widerruf"]'); } },
    { kapitel: "gespeichert", ziel: "fall", name: "2 O 77/25", art: "tun", warten: "fall-abgeschlossen", seit: "0.4.0",
      titel: "Fall abgeschlossen", hilfe: "abschliessen", aufgabe: "Klappen Sie den Fall 2 O 77/25 auf und klicken Sie auf „Fall abgeschlossen“.",
      vormachen: async () => { if (!$('[data-tour="fall"][data-name="2 O 77/25"] [data-tour="fall-abschliessen"]')) await klick('[data-tour="fall"][data-name="2 O 77/25"] .fall-kopf'); await warte(300); await klick('[data-tour="fall"][data-name="2 O 77/25"] [data-tour="fall-abschliessen"]'); } },
    { kapitel: "gespeichert", ziel: "fristhinweis", art: "zeigen", seit: "0.4.0", titel: "Der Hinweis vor dem Löschen",
      text: "30 Tage vor dem Löschen erinnert Lokanon an jeden Fall, hier an 9 O 88/25. Mit „Verlängern“ behalten Sie die Angaben. Tun Sie nichts, löscht Lokanon sie am angegebenen Tag." },
    { kapitel: "gespeichert", ziel: "suche", art: "tun", warten: "suche", seit: "0.4.0", titel: "Ein Löschwunsch",
      text: "Frau Brinkhoff möchte, dass ihre Daten gelöscht werden.", aufgabe: "Suchen Sie nach „Brinkhoff“.",
      vormachen: async () => { const i = $("#suche"); if (i) { i.value = "Brinkhoff"; await klick("#suche-go"); } } },
    { kapitel: "gespeichert", ziel: "ueberall-loeschen", art: "tun", warten: "loeschdialog", seit: "0.4.0", titel: "Überall löschen", hilfe: "ueberall_loeschen",
      aufgabe: "Klicken Sie auf „Brinkhoff überall löschen“.", vormachen: () => klick('[data-tour="ueberall-loeschen"]') },
    { kapitel: "gespeichert", ziel: "loeschdialog", art: "tun", warten: "geloescht", seit: "0.4.0", titel: "Vorher sehen, was gelöscht wird",
      text: "Der Dialog zeigt alles, was zum Fall gehört: gelernte Angaben, Schlüssel, Testfälle. Ihre Originale bleiben. Beim Wunsch des Mandanten lässt sich nichts abwählen.",
      aufgabe: "Klicken Sie auf den roten Knopf.", vormachen: async () => { await klick('[data-tour="loeschen-ok"]'); await warte(300); const b = $('[data-tour="loeschen-ok"]'); if (b) b.click(); } },
    { kapitel: "gespeichert", ziel: "nachweis-oeffnen", art: "tun", warten: "nachweis", seit: "0.4.0", titel: "Der Nachweis", hilfe: "loeschprotokoll",
      aufgabe: "Öffnen Sie den Nachweis.", vormachen: () => klick('[data-tour="nachweis-oeffnen"]') },
    { kapitel: "gespeichert", ziel: null, art: "zeigen", seit: "0.4.0", titel: "Verschlüsselt, nur hier", hilfe: "verschluesselt",
      vorher: async (app) => app.schliesse() },
  ];
  window.LokanonDrehbuch = { kapitel, schritte };
})();
