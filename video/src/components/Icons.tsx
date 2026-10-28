import React from "react";
import { colors } from "../theme";

/** Schild-Symbol der Marke; `draw` 0–1 zeichnet den Umriss, `fill` 0–1 blendet die Füllung ein. */
export const Shield: React.FC<{
  size: number;
  draw?: number;
  check?: number;
  fill?: number;
  stroke?: string;
  strokeWidth?: number;
}> = ({ size, draw = 1, check = 1, fill = 1, stroke = "#FFFFFF", strokeWidth = 6 }) => (
  <svg width={size * (100 / 118)} height={size} viewBox="0 0 100 118" fill="none">
    <path
      d="M50 5 L92 20 V56 C92 84 72 104 50 113 C28 104 8 84 8 56 V20 Z"
      fill={colors.accent}
      fillOpacity={0.22 * fill}
      stroke={stroke}
      strokeWidth={strokeWidth}
      strokeLinejoin="round"
      pathLength={1}
      strokeDasharray={1}
      strokeDashoffset={1 - draw}
    />
    <path
      d="M33 59 L46 72 L68 44"
      stroke={stroke}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      pathLength={1}
      strokeDasharray={1}
      strokeDashoffset={1 - check}
    />
  </svg>
);

export const Lock: React.FC<{ size: number; color?: string; closed?: number }> = ({
  size,
  color = colors.muted,
  closed = 1,
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke={color}
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect x="4" y="10.5" width="16" height="10.5" rx="2.5" />
    <path
      d="M8 10.5 V7.5 a4 4 0 0 1 8 0 V10.5"
      style={{ transform: `translateY(${(1 - closed) * -3}px)` }}
    />
    <circle cx="12" cy="15.8" r="1.4" fill={color} stroke="none" />
  </svg>
);

export const Key: React.FC<{ size: number; color?: string }> = ({ size, color = colors.accent }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke={color}
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="7.5" cy="12" r="4.5" />
    <path d="M12 12 H21.5" />
    <path d="M18 12 V15.5" />
    <path d="M21 12 V15" />
  </svg>
);
