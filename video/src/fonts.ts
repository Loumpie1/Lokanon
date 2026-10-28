import { useEffect, useState } from "react";
import { continueRender, delayRender, staticFile } from "remotion";
import { loadFont } from "@remotion/fonts";

const files: { family: string; file: string; weight: string }[] = [
  { family: "Source Sans 3", file: "source-sans-3-latin-400-normal.woff2", weight: "400" },
  { family: "Source Sans 3", file: "source-sans-3-latin-600-normal.woff2", weight: "600" },
  { family: "Source Sans 3", file: "source-sans-3-latin-700-normal.woff2", weight: "700" },
  { family: "Source Serif 4", file: "source-serif-4-latin-600-normal.woff2", weight: "600" },
  { family: "Source Serif 4", file: "source-serif-4-latin-700-normal.woff2", weight: "700" },
];

let pending: Promise<void> | null = null;

export const loadAllFonts = (): Promise<void> => {
  if (!pending) {
    pending = Promise.all(
      files.map((f) =>
        loadFont({
          family: f.family,
          url: staticFile(`fonts/${f.file}`),
          weight: f.weight,
          format: "woff2",
        }),
      ),
    ).then(() => undefined);
  }
  return pending;
};

/** Wartet, bis alle Schriften geladen sind; vorher wird nichts gezeichnet. */
export const useFontsReady = (): boolean => {
  const [ready, setReady] = useState(false);
  const [handle] = useState(() => delayRender("Schriften laden"));
  useEffect(() => {
    loadAllFonts()
      .catch((e) => console.error("Schriften konnten nicht geladen werden", e))
      .then(() => {
        setReady(true);
        continueRender(handle);
      });
  }, [handle]);
  return ready;
};
