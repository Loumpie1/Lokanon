import React from "react";
import { colors, fonts, layout, tween } from "../../theme";

export const THREAD = "#D13B5B"; // roter Faden = Farbe der Personen-Markierung
export const ACCENT_SOFT = "#DDF4EF";
export const WARN = "#9A5A09";
export const WARN_SOFT = "#FFF3DF";

/** Einblenden von unten: liefert opacity und transform ab Frame `at`. */
export const rise = (f: number, at: number, len = 18, dist = 22) => ({
  opacity: tween(f, [at, at + len]),
  transform: `translateY(${tween(f, [at, at + len + 4], [dist, 0])}px)`,
});

/** Zähler mit weichem Auslauf. */
export const countUp = (f: number, at: number, ziel: number, len = 40) => Math.round(ziel * tween(f, [at, at + len]));

/** Überschrift einer Szene: Vorzeile + Titel. */
export const SceneHead: React.FC<{
  f: number;
  eyebrow: string;
  title: string;
  at?: number;
  dark?: boolean;
  red?: boolean;
  width?: number;
}> = ({ f, eyebrow, title, at = 4, dark = false, red = true, width = 1100 }) => (
  <div style={{ position: "absolute", left: layout.margin, top: 150, width }}>
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        fontFamily: fonts.sans,
        fontSize: 22,
        fontWeight: 700,
        letterSpacing: "0.14em",
        textTransform: "uppercase",
        color: red ? (dark ? "#F0708A" : THREAD) : dark ? colors.accentLight : colors.accent,
        ...rise(f, at, 14, 10),
      }}
    >
      <span style={{ width: 34, height: 3, background: "currentColor", borderRadius: 2, display: "inline-block" }} />
      {eyebrow}
    </div>
    <div
      style={{
        marginTop: 14,
        fontFamily: fonts.serif,
        fontWeight: 700,
        fontSize: 62,
        lineHeight: 1.1,
        letterSpacing: "-0.01em",
        color: dark ? "#FFFFFF" : colors.text,
        ...rise(f, at + 6),
      }}
    >
      {title}
    </div>
  </div>
);

/** Weiße Karte mit Schatten. */
export const Card: React.FC<{ style?: React.CSSProperties; children: React.ReactNode }> = ({ style, children }) => (
  <div
    style={{
      background: colors.card,
      borderRadius: 14,
      border: `1px solid ${colors.bar}`,
      boxShadow: "0 10px 34px rgba(22,54,92,0.10)",
      boxSizing: "border-box",
      ...style,
    }}
  >
    {children}
  </div>
);

/** Aufzählung mit kleinem Punkt, gestaffelt eingeblendet. */
export const Bullets: React.FC<{ f: number; at: number; items: readonly string[]; size?: number; color?: string; gap?: number; dot?: string }> = ({
  f,
  at,
  items,
  size = 24,
  color = colors.text,
  gap = 12,
  dot = colors.accent,
}) => (
  <div style={{ display: "flex", flexDirection: "column", gap }}>
    {items.map((t, i) => (
      <div key={t} style={{ display: "flex", gap: 14, alignItems: "flex-start", fontSize: size, lineHeight: 1.35, color, ...rise(f, at + i * 10, 14, 12) }}>
        <span style={{ width: 9, height: 9, borderRadius: 5, background: dot, marginTop: size * 0.5, flexShrink: 0 }} />
        <span>{t}</span>
      </div>
    ))}
  </div>
);
