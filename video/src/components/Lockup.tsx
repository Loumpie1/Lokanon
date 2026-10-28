import React from "react";
import { fonts } from "../theme";
import { texts } from "../texts";
import { Shield } from "./Icons";

/** Schild + Wortmarke nebeneinander. */
export const Lockup: React.FC<{
  size: number;
  color?: string;
  shieldStroke?: string;
  draw?: number;
  check?: number;
  fill?: number;
  wordOpacity?: number;
  wordShift?: number;
}> = ({
  size,
  color = "#FFFFFF",
  shieldStroke = "#FFFFFF",
  draw = 1,
  check = 1,
  fill = 1,
  wordOpacity = 1,
  wordShift = 0,
}) => (
  <div style={{ display: "flex", alignItems: "center", gap: size * 0.26 }}>
    <Shield
      size={size * 1.05}
      draw={draw}
      check={check}
      fill={fill}
      stroke={shieldStroke}
      strokeWidth={size > 60 ? 6 : 8}
    />
    <div
      style={{
        fontFamily: fonts.serif,
        fontWeight: 700,
        fontSize: size,
        lineHeight: 1,
        color,
        letterSpacing: "-0.01em",
        opacity: wordOpacity,
        transform: `translateX(${wordShift}px)`,
        paddingBottom: size * 0.08,
      }}
    >
      {texts.wortmarke}
    </div>
  </div>
);
