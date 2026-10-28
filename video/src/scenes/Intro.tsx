import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Lockup } from "../components/Lockup";
import { easeInOut, fonts, tween } from "../theme";
import { texts } from "../texts";

/** Szene 1 (0–4 s): Schild zeichnet sich, Wortmarke und Unterzeile blenden ein. */
export const Intro: React.FC = () => {
  const f = useCurrentFrame();
  const draw = tween(f, [6, 50], [0, 1], easeInOut);
  const check = tween(f, [44, 62]);
  const fill = tween(f, [48, 72]);
  const wordOpacity = tween(f, [44, 70]);
  const wordShift = tween(f, [44, 74], [-24, 0]);
  const subOpacity = tween(f, [62, 86]);
  const subY = tween(f, [62, 90], [16, 0]);
  const out = tween(f, [104, 118], [1, 0]);

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: out }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 44 }}>
        <Lockup size={150} draw={draw} check={check} fill={fill} wordOpacity={wordOpacity} wordShift={wordShift} />
        <div
          style={{
            fontFamily: fonts.sans,
            fontSize: 46,
            fontWeight: 400,
            color: "rgba(255,255,255,0.88)",
            opacity: subOpacity,
            transform: `translateY(${subY}px)`,
            letterSpacing: "0.005em",
          }}
        >
          {texts.introUnterzeile}
        </div>
      </div>
    </AbsoluteFill>
  );
};
