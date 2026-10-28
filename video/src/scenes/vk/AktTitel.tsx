import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { easeInOut, fonts, tween } from "../../theme";

/** Akt-Tafel (2 s, dunkel): Nummer, Titel, der rote Faden zieht einmal durch. */
export const AktTitel: React.FC<{ nr: string; titel: string }> = ({ nr, titel }) => {
  const f = useCurrentFrame();
  const line = tween(f, [4, 40], [0, 1], easeInOut);
  const nrIn = tween(f, [8, 22]);
  const titelIn = tween(f, [14, 32]);
  const titelY = tween(f, [14, 36], [26, 0]);
  const out = tween(f, [48, 60], [1, 0]);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: out }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 26 }}>
        <div style={{ fontFamily: fonts.sans, fontSize: 28, fontWeight: 700, letterSpacing: "0.22em", textTransform: "uppercase", color: "#F0708A", opacity: nrIn }}>
          {nr}
        </div>
        <div style={{ fontFamily: fonts.serif, fontWeight: 700, fontSize: 96, color: "#FFFFFF", letterSpacing: "-0.01em", opacity: titelIn, transform: `translateY(${titelY}px)` }}>
          {titel}
        </div>
        <div style={{ width: 420, height: 4, borderRadius: 2, background: "#D13B5B", transform: `scaleX(${line})`, transformOrigin: "left center" }} />
      </div>
    </AbsoluteFill>
  );
};
