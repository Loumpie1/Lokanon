import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Lockup } from "../../components/Lockup";
import { colors, easeInOut, fonts, tween } from "../../theme";
import { vk } from "../../texts_vk";
import { rise } from "./ui";

/** Szene 1 (5 s, dunkel): Schild zeichnet sich, Wortmarke, Unterzeile, drei Handschriften. */
export const VkIntro: React.FC = () => {
  const f = useCurrentFrame();
  const draw = tween(f, [6, 50], [0, 1], easeInOut);
  const check = tween(f, [44, 62]);
  const fill = tween(f, [48, 72]);
  const wordOpacity = tween(f, [44, 70]);
  const wordShift = tween(f, [44, 74], [-24, 0]);
  const out = tween(f, [134, 150], [1, 0]);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: out }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 40 }}>
        <Lockup size={150} draw={draw} check={check} fill={fill} wordOpacity={wordOpacity} wordShift={wordShift} />
        <div style={{ fontFamily: fonts.sans, fontSize: 46, color: "rgba(255,255,255,0.88)", ...rise(f, 64, 22, 16) }}>{vk.introUnterzeile}</div>
        <div style={{ display: "flex", gap: 16, marginTop: 10 }}>
          {vk.credits.map((c, i) => (
            <div
              key={c.k}
              style={{
                display: "flex",
                gap: 10,
                alignItems: "center",
                padding: "12px 24px",
                borderRadius: 999,
                border: "1.5px solid rgba(255,255,255,0.3)",
                background: "rgba(255,255,255,0.06)",
                fontFamily: fonts.sans,
                fontSize: 24,
                color: "rgba(255,255,255,0.92)",
                ...rise(f, 88 + i * 10, 16, 14),
              }}
            >
              <b style={{ color: colors.accentLight }}>{c.k}</b>
              {c.v}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
