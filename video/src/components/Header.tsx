import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts, inOut, layout } from "../theme";
import { texts } from "../texts";
import { Lock } from "./Icons";
import { Lockup } from "./Lockup";

/** Schmale Kopfzeile in den hellen Szenen. */
export const Header: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = inOut(frame, 2, durationInFrames, 14);
  return (
    <div
      style={{
        position: "absolute",
        left: layout.margin,
        right: layout.margin,
        top: layout.headerY,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        opacity,
        fontFamily: fonts.sans,
      }}
    >
      <Lockup size={30} color={colors.primary} shieldStroke={colors.primary} />
      <div style={{ display: "flex", alignItems: "center", gap: 12, color: colors.muted, fontSize: 24 }}>
        <Lock size={24} color={colors.accent} />
        <span>{texts.kopfzeileRechts}</span>
      </div>
    </div>
  );
};
