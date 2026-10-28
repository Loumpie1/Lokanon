import { Easing, interpolate } from "remotion";

export const FPS = 30;
export const TOTAL_FRAMES = 30 * FPS; // 30 Sekunden

export const colors = {
  primary: "#16365C",
  primaryGlow: "#1E4A7A",
  action: "#1F5FA8",
  accent: "#0E9F8A",
  accentLight: "#7FD9CB",
  bg: "#F6F8FB",
  text: "#1A2433",
  muted: "#5B6678",
  line: "#D5DBE3",
  bar: "#E3E8EF",
  card: "#FFFFFF",
  bubble: "#EEF2F7",
  mark: {
    person: "#FFD6D6",
    firma: "#D6E4FF",
    adresse: "#D9F2E3",
    nummer: "#FFF3C4",
  },
  markBorder: {
    person: "#E09C9C",
    firma: "#8FAEE8",
    adresse: "#8CCDAA",
    nummer: "#DEC46A",
  },
} as const;

export const fonts = {
  sans: '"Source Sans 3", "Segoe UI", Arial, sans-serif',
  serif: '"Source Serif 4", Georgia, serif',
  sansFamily: "Source Sans 3",
  serifFamily: "Source Serif 4",
} as const;

export const easeOut = Easing.bezier(0.22, 1, 0.36, 1);
export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);

/** Ruhige Interpolation mit Klemmung an beiden Enden. */
export const tween = (
  frame: number,
  input: [number, number],
  output: [number, number] = [0, 1],
  easing: (t: number) => number = easeOut,
) =>
  interpolate(frame, input, output, {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing,
  });

/** 0 → 1 ab `start`, 1 → 0 ab `end`, jeweils über `len` Frames. */
export const inOut = (frame: number, start: number, end: number, len = 14) =>
  Math.min(tween(frame, [start, start + len]), tween(frame, [end - len, end], [1, 0]));

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

// Layout 1920 × 1080, sichere Ränder 120 / 60
export const layout = {
  margin: 120,
  headerY: 58,
  doc: { x: 120, y: 130, w: 840, h: 720, pad: 56, fontSize: 26, lineHeight: 40 },
  panel: { x: 1040, y: 130, w: 760, h: 720 },
  captionY: 905,
  captionSize: 50,
} as const;
