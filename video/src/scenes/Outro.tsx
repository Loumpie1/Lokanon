import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Lockup } from "../components/Lockup";
import { colors, fonts, tween } from "../theme";
import { texts } from "../texts";

/** Szene 6 (26–30 s): Wortmarke, Claim, Unterzeile. */
export const Outro: React.FC = () => {
  const o = useCurrentFrame();
  const lockOpacity = tween(o, [6, 28]);
  const lockScale = tween(o, [6, 34], [0.96, 1]);
  const claimOpacity = tween(o, [24, 46]);
  const claimY = tween(o, [24, 50], [20, 0]);
  const subOpacity = tween(o, [42, 64]);
  const subY = tween(o, [42, 68], [14, 0]);

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ opacity: lockOpacity, transform: `scale(${lockScale})` }}>
          <Lockup size={96} />
        </div>
        <div
          style={{
            marginTop: 64,
            fontFamily: fonts.serif,
            fontWeight: 600,
            fontSize: 76,
            lineHeight: 1.15,
            color: "#FFFFFF",
            opacity: claimOpacity,
            transform: `translateY(${claimY}px)`,
            letterSpacing: "-0.005em",
          }}
        >
          {texts.claim}
        </div>
        <div
          style={{
            marginTop: 22,
            fontFamily: fonts.sans,
            fontSize: 40,
            color: colors.accentLight,
            opacity: subOpacity,
            transform: `translateY(${subY}px)`,
          }}
        >
          {texts.outroUnterzeile}
        </div>
      </div>
    </AbsoluteFill>
  );
};
