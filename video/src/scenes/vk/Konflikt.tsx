import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { colors, fonts, layout, tween } from "../../theme";
import { vk } from "../../texts_vk";
import { ACCENT_SOFT, Card, SceneHead, THREAD, rise } from "./ui";

/** Akt 1, Szene 2 (10 s): drei Regeln, dann die Wende. */
export const Konflikt: React.FC = () => {
  const f = useCurrentFrame();
  const t = vk.konflikt;
  const w = (1680 - 2 * 28) / 3;
  const lift = tween(f, [196, 226], [0, -26]);
  return (
    <AbsoluteFill style={{ fontFamily: fonts.sans }}>
      <SceneHead f={f} eyebrow={t.eyebrow} title={t.titel} />
      {t.karten.map((k, i) => (
        <Card key={k.para} style={{ position: "absolute", left: layout.margin + i * (w + 28), top: 340, width: w, height: 330, padding: "30px 34px", borderTop: `4px solid ${THREAD}`, display: "flex", flexDirection: "column", gap: 12, ...rise(f, 34 + i * 12, 20, 30), transform: `translateY(${lift}px)` }}>
          <div style={{ fontFamily: fonts.serif, fontWeight: 700, fontSize: 44, color: THREAD, lineHeight: 1 }}>{k.para}</div>
          <div style={{ fontFamily: fonts.serif, fontWeight: 600, fontSize: 31, color: colors.text, lineHeight: 1.2 }}>{k.titel}</div>
          <div style={{ fontSize: 23, lineHeight: 1.4, color: colors.muted }}>{k.text}</div>
        </Card>
      ))}
      <div style={{ position: "absolute", left: layout.margin, top: 700, width: 1680, background: ACCENT_SOFT, borderRadius: 16, padding: "28px 36px", display: "flex", gap: 26, alignItems: "center", ...rise(f, 200, 20, 26) }}>
        <div style={{ fontFamily: fonts.serif, fontWeight: 700, fontSize: 70, color: colors.accent, lineHeight: 0.9 }}>?</div>
        <div style={{ fontSize: 30, lineHeight: 1.4, color: colors.text }}>{t.wende}</div>
      </div>
    </AbsoluteFill>
  );
};
