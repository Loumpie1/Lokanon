// Alle sichtbaren Texte des Videos. Hier ändern, dann neu rendern.

export const texts = {
  wortmarke: "Lokanon",

  // Szene 1 (0–4 s)
  introUnterzeile: "Mandatsunterlagen sicher mit KI bearbeiten",

  // Kopfzeile (Szenen 2–5)
  kopfzeileRechts: "Läuft lokal · keine Internetverbindung",

  // Bildunterschriften je Szene
  caption2: "Personendaten erkennen – lokal, ohne Internet",
  caption3: "Prüfen und entscheiden – mit einem Schalter",
  caption4: "Mit ChatGPT oder Claude arbeiten – ohne Namen preiszugeben",
  caption5: "Antwort zurückübersetzen – der Schlüssel bleibt bei Ihnen",

  // Szene 6 (26–30 s)
  claim: "Lokanon. Läuft auf Ihrem PC.",
  outroUnterzeile: "Pilotversion für Kanzleien",

  // Rechte Spalte, Szene 2 und 3
  legendeTitel: "Gefundene Personendaten",
  pruefenTitel: "Prüfen",
  wirdErsetzt: "wird ersetzt",
  bleibtStehen: "bleibt stehen",

  // Chat (Szene 4) – neutral, kein Anbieter
  chatTitel: "KI-Assistent",
  chatEingabe: "Nachricht eingeben …",
  frageL1: "Bitte prüfen Sie die Fristen im Verfahren",
  frageL2: "für",
  antwortTitel: "Antwort zurückübersetzt",
  schluesselHinweis: "Schlüssel nur auf diesem PC",
};

// Erfundene Beispieldaten im Musterbrief (keine echten Personen).
export type MarkKind = "person" | "firma" | "adresse" | "nummer";
export type MarkId = "name" | "adresse" | "ort" | "az" | "anrede" | "gericht";

export const marks: Record<MarkId, { text: string; ph: string; kind: MarkKind }> = {
  name: { text: "Sabine Winter", ph: "[PERSON_1]", kind: "person" },
  adresse: { text: "Eppinghofer Straße 47", ph: "[ADRESSE_1]", kind: "adresse" },
  ort: { text: "45468 Mülheim an der Ruhr", ph: "[ORT_1]", kind: "adresse" },
  az: { text: "14 VI 512/26", ph: "[AZ_1]", kind: "nummer" },
  anrede: { text: "Winter", ph: "[PERSON_1]", kind: "person" },
  gericht: { text: "Amtsgericht Mülheim", ph: "[FIRMA_1]", kind: "firma" },
};

export const brief = {
  azLabel: "Aktenzeichen: ",
  anredeVor: "Sehr geehrte Frau ",
  anredeNach: ",",
  satz1Vor: "im Verfahren vor dem ",
  satz1Nach: " haben wir",
  satz2: "fristgerecht Stellung genommen. Die Gegenseite hat",
  gruss: "Mit freundlichen Grüßen",
};

// KI-Antwort (Szene 4/5), zeilenweise, damit Chips kontrolliert umbrechen.
export const antwort = {
  l1Vor: "Im Verfahren ",
  l1Nach: " endet die Frist für",
  l2Nach: " am 14. April 2026.",
  l3: "Die Zustellung an die Anschrift",
  l4Nach: " sollte bis dahin erfolgen.",
};

export const legende: { kind: MarkKind; label: string }[] = [
  { kind: "person", label: "Person" },
  { kind: "adresse", label: "Adresse / Ort" },
  { kind: "nummer", label: "Nummern" },
  { kind: "firma", label: "Firma / Behörde" },
];
