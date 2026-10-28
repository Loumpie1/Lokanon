import React from "react";
import { colors, fonts, lerp } from "../theme";
import type { MarkKind } from "../texts";
import { textWidth } from "./measure";

type Props = {
  original: string;
  placeholder: string;
  kind: MarkKind;
  /** 0–1: Markierung (farbige Fläche) wächst von links hinter dem Originaltext. */
  highlight: number;
  /** 0–1: Originaltext → Platzhalter-Chip. */
  morph: number;
  /** 0–1: "bleibt stehen" (Fläche verschwindet, gestrichelte Linie). */
  kept?: number;
  fontSize: number;
  fontWeight?: number;
  color?: string;
};

/**
 * Ein Textstück im Fließtext, das sich in einen Platzhalter-Chip verwandeln
 * kann. Die Breite wird interpoliert, damit der Folgetext ruhig nachrückt.
 */
export const MorphSpan: React.FC<Props> = ({
  original,
  placeholder,
  kind,
  highlight,
  morph,
  kept = 0,
  fontSize,
  fontWeight = 400,
  color = colors.text,
}) => {
  const chipSize = fontSize * 0.86;
  const pad = fontSize * 0.42;
  const hiPad = fontSize * 0.22;
  const wOrig = textWidth(original, fontSize, fontWeight);
  const wChip = textWidth(placeholder, chipSize, 600, fonts.sansFamily, "0.01em") + 2 * pad;

  // Die Markierung bekommt links und rechts etwas Luft, die von Anfang an
  // zur Breite gehört, damit der Folgetext beim Einblenden nicht springt.
  const width = lerp(wOrig + 2 * hiPad, wChip, morph);
  const textLeft = lerp(hiPad, 0, morph);
  const pillLeft = 0;
  const pillWidth = width;
  const pillHeight = lerp(fontSize * 1.3, fontSize * 1.42, morph);
  const radius = lerp(fontSize * 0.18, fontSize * 0.3, morph);
  const pillScale = Math.max(0, highlight);
  const pillOpacity = 1 - kept;

  return (
    <span
      style={{
        display: "inline-block",
        position: "relative",
        width,
        verticalAlign: "baseline",
        whiteSpace: "nowrap",
      }}
    >
      {/* Platzhalter für Zeilenhöhe und Grundlinie */}
      <span style={{ display: "inline-block", width: 0, visibility: "hidden" }}>Hg</span>

      {/* Farbfläche: Markierung bzw. Chip-Hintergrund */}
      <span
        style={{
          position: "absolute",
          left: pillLeft,
          top: "50%",
          width: pillWidth,
          height: pillHeight,
          transform: `translateY(-50%) scaleX(${pillScale})`,
          transformOrigin: "left center",
          borderRadius: radius,
          background: colors.mark[kind],
          border: `1.5px solid ${colors.markBorder[kind]}`,
          boxSizing: "border-box",
          opacity: pillOpacity,
        }}
      />

      {/* Originaltext */}
      <span
        style={{
          position: "absolute",
          left: textLeft,
          top: 0,
          opacity: 1 - morph,
          transform: `translateY(${-fontSize * 0.25 * morph}px)`,
          color,
          fontWeight,
        }}
      >
        {original}
      </span>

      {/* gestrichelte Linie bei "bleibt stehen" */}
      <span
        style={{
          position: "absolute",
          left: textLeft,
          width: wOrig,
          bottom: fontSize * 0.05,
          borderBottom: `2px dashed ${colors.muted}`,
          opacity: kept,
        }}
      />

      {/* Platzhalter-Chip-Text */}
      <span
        style={{
          position: "absolute",
          left: pad,
          top: "50%",
          transform: `translateY(calc(-50% + ${fontSize * 0.25 * (1 - morph)}px))`,
          opacity: morph,
          fontSize: chipSize,
          fontWeight: 600,
          letterSpacing: "0.01em",
          color: colors.text,
          lineHeight: 1,
        }}
      >
        {placeholder}
      </span>
    </span>
  );
};
