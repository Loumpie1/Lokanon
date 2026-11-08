/* Hilfetexte und Kurzbegründungen: eine Quelle für Kontexthilfe (i), Abschlussfenster, Einführung und Anleitung.
   Regel (docs/entwicklung/hilfe-mitpflegen.md): Texte stehen nur hier. Wer eine Funktion ändert, passt den Text
   im selben Commit an; tests/test_hilfe.py prüft, dass jeder Schlüssel benutzt wird und jeder benutzte existiert.
   kurz: ein, zwei Sätze ohne Paragrafen. mehr: Rechtsgrundlage oder Hintergrund. kapitel: Einführungskapitel. */
window.LokanonHilfe = {
  speichern: {
    titel: "Warum Lokanon sich etwas merkt",
    kurz: "Damit Sie Übersehenes nur einmal markieren. Beim nächsten Dokument schlägt Lokanon es selbst vor, Sie können es wie jeden Vorschlag abwählen.",
    mehr: "Gespeichert wird nur, was Sie nach dem Anonymisieren bestätigen.",
    kapitel: "gespeichert",
  },
  speichern_warum: {
    titel: "Warum, warum so, warum so lange",
    kurz: "<ul><li><b>Merken:</b> Übersehenes nur einmal markieren, danach schlägt Lokanon es vor.</li><li><b>Frist:</b> Namen von Mandanten, Gegnern und Zeugen dürfen nur so lange gespeichert sein, wie sie gebraucht werden.</li><li><b>Verschlüsselt:</b> Sie unterliegen der Schweigepflicht. Ohne Ihr Windows-Konto kann niemand die Liste lesen.</li></ul>",
    mehr: "Speicherbegrenzung (Art. 5 Abs. 1 e DSGVO), Sicherheit der Verarbeitung (Art. 32 DSGVO), § 203 StGB.",
    kapitel: "gespeichert",
  },
  fall: {
    titel: "Warum ein Fall",
    kurz: "Damit Sie bei einem Löschwunsch alles zu einem Mandat auf einmal finden und zeigen können, woher eine Angabe stammt. Lokanon nimmt das Aktenzeichen aus dem Dokument; Sie können es ändern.",
    mehr: "Rechenschaftspflicht, Art. 5 Abs. 2 DSGVO. Nehmen Sie das Aktenzeichen, keine Namen.",
    kapitel: "gespeichert",
  },
  frist: {
    titel: "Warum eine Frist",
    kurz: "Namen von Mandanten, Gegnern und Zeugen dürfen nur so lange gespeichert sein, wie sie gebraucht werden. Die Frist läuft ab dem letzten Fund: Taucht eine Angabe in einem neuen Dokument auf, beginnt sie neu.",
    mehr: "Speicherbegrenzung, Art. 5 Abs. 1 e DSGVO. Standard 12 Monate, einstellbar unter Einstellungen → Aufbewahrung.",
    kapitel: "gespeichert",
  },
  verlaengern: {
    titel: "Verlängern",
    kurz: "Läuft ein Mandat länger, verlängern Sie den Fall um 6, 12 oder 24 Monate, oder „bis auf Widerruf“. Dann gilt keine Frist, bis Sie den Fall abschließen.",
    mehr: "30 Tage vor dem Löschen erinnert Lokanon beim Start an jeden betroffenen Fall.",
    kapitel: "gespeichert",
  },
  abschliessen: {
    titel: "Fall abgeschlossen",
    kurz: "Ist das Mandat beendet, markieren Sie den Fall als abgeschlossen. Ab dann läuft eine kurze Frist (Standard 3 Monate), danach löscht Lokanon die gelernten Angaben, Schlüssel und Testfälle des Falls.",
    mehr: "Die anonymisierten Kopien bleiben, sie enthalten keine Namen.",
    kapitel: "gespeichert",
  },
  verschluesselt: {
    titel: "Warum verschlüsselt",
    kurz: "Sie unterliegen der Schweigepflicht. Lokanon verschlüsselt alles, was Namen enthält, mit Ihrem Windows-Konto: Ohne Ihre Anmeldung kann niemand die Dateien lesen, auch nicht in einer Sicherungskopie.",
    mehr: "Sicherheit der Verarbeitung, Art. 32 DSGVO; § 203 StGB. Nichts davon verlässt den PC.",
    kapitel: "gespeichert",
  },
  loeschprotokoll: {
    titel: "Warum ein Löschprotokoll ohne Namen",
    kurz: "Es belegt, dass gelöscht wurde, ohne die gelöschten Namen wieder aufzuschreiben: Datum, Fallnummer, was und wie viel, Grund.",
    mehr: "Nachweis gegenüber Mandant und Aufsicht. „Nachweis“ erzeugt eine Bestätigung zum Ablegen in der Akte.",
    kapitel: "gespeichert",
  },
  handakte: {
    titel: "Warum nicht 6 Jahre wie die Handakte",
    kurz: "Die Liste gelernter Angaben ist ein Arbeitsmittel, nicht Teil der Handakte. Für sie gilt: so kurz wie möglich.",
    mehr: "§ 50 BRAO gilt für die Handakte.",
  },
  sicherung: {
    titel: "Und meine Datensicherung?",
    kurz: "Lokanon löscht seine eigenen Dateien. Sichern Sie den Lokanon-Datenordner (z. B. mit dem Dateiversionsverlauf), bleiben dort ältere Stände bis zum Ablauf Ihrer Sicherung. Sie sind verschlüsselt und nur unter Ihrem Windows-Konto lesbar.",
    mehr: "Datenordner: %USERPROFILE%\\Lokanon. Wer ihn von der Sicherung ausnimmt, hat nach dem Löschen nichts mehr davon.",
  },
  ueberall_loeschen: {
    titel: "Überall löschen",
    kurz: "Für einen Löschwunsch: Lokanon löscht die Angabe aus allen Fällen und dazu alle Fälle, in denen sie vorkommt, mit Schlüsseln, Vorgangsordnern und Testfällen. Vorher sehen Sie genau, was gelöscht wird.",
    mehr: "Recht auf Löschung, Art. 17 DSGVO. Danach erzeugt „Nachweis“ eine Bestätigung ohne Namen.",
    kapitel: "gespeichert",
  },
  originale_bleiben: {
    titel: "Warum die Originale bleiben",
    kurz: "Lokanon verändert und löscht Ihre Originaldateien nie. Sie gehören zur Akte und unterliegen Ihren eigenen Aufbewahrungsfristen.",
  },
  protokoll_bleibt: {
    titel: "Warum das Protokoll bleibt",
    kurz: "Das Protokoll enthält keine Namen, nur Platzhalter und Dateinummern. Es hilft bei Rückfragen und löscht sich nach 30 Tagen selbst.",
  },
  ki_kopien: {
    titel: "Kopien bei der KI",
    kurz: "Was Sie schon an ChatGPT, Claude oder eine andere KI gegeben haben, liegt beim Anbieter. Das kann Lokanon nicht löschen. Diese Kopien enthalten aber keine Namen, nur Platzhalter.",
  },
  stehen_lassen: {
    titel: "Künftig immer stehen lassen",
    kurz: "Für Fachbegriffe, die Lokanon für einen Namen hält. Lokanon merkt sich das Wort verschlüsselt, ohne Frist, weil es meist kein Personenbezug ist. Rückgängig unter Fälle und gelernte Angaben.",
  },
  regel: {
    titel: "Regel statt Name",
    kurz: "Steht vor dem markierten Wert eine Bezeichnung („Mandantennr.: 48213“), lernt Lokanon besser die Bezeichnung: Künftig wird jeder Wert dahinter vorgeschlagen. Gespeichert wird dabei keine Nummer und kein Name.",
    mehr: "Bei Nummern mit festem Aufbau („AZ-2026-0815“) lernt Lokanon das Muster. Datenminimierung, Art. 5 Abs. 1 c DSGVO.",
    kapitel: "markieren",
  },
  markieren: {
    titel: "Übersehenes markieren",
    kurz: "Klicken Sie auf „Übersehenes markieren“ (oder Taste M) und dann auf ein Wort im Dokument, oder überstreichen Sie mehrere Wörter. Ein Doppelklick geht immer. Lokanon sucht den Begriff in allen Dateien. Im Fenster an der Stelle wählen Sie die Art und den Platzhalter; „Abbrechen“ schließt es, ohne etwas zu ändern.",
    kapitel: "markieren",
  },
  aufbewahrung: {
    titel: "Aufbewahrung",
    kurz: "Hier stellen Sie ein, wie lange Lokanon gelernte Angaben behält. Schlüssel, Vorgangsordner und Testfälle gehören zum selben Fall und werden mit ihm gelöscht. Aufgeräumt wird automatisch beim Start.",
    mehr: "Fristen und Texte vor dem Einsatz mit Ihrer oder Ihrem Datenschutzbeauftragten abstimmen. Ein Mustertext fürs Verarbeitungsverzeichnis liegt im Pilot-Paket.",
    kapitel: "gespeichert",
  },
};
