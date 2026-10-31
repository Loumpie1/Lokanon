import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { colors, easeInOut, fonts, layout, tween } from "../../theme";
import { vk } from "../../texts_vk";
import { SceneHead, THREAD, rise } from "./ui";

/** Ablauf (8 s): Zielgruppen, dann drei Schritte, die eine Linie verbindet. */
export const Ablauf: React.FC = () => {
  const f = useCurrentFrame();
  const t = vk.ablauf;
  const cols = t.schritte.length;
  const w = (1680 - (cols - 1) * 40) / cols;
  const line = tween(f, [90, 190], [0, 1], easeInOut);
  return (
    <AbsoluteFill style={{ fontFamily: fonts.sans }}>
      <SceneHead f={f} eyebrow={t.eyebrow} title={t.titel} red={false} />
      <div style={{ position: "absolute", left: layout.margin, top: 330, display: "flex", gap: 14 }}>
        {t.chips.map((c, i) => (
          <div key={c} style={{ padding: "12px 26px", borderRadius: 999, background: colors.card, border: `1px solid ${colors.bar}`, boxShadow: "0 4px 14px rgba(22,54,92,0.08)", fontSize: 26, fontWeight: 600, color: colors.text, ...rise(f, 36 + i * 8, 16, 14) }}>
            {c}
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: layout.margin + 40, top: 476, width: 1680 - 80, height: 4, background: colors.bar, borderRadius: 2 }}>
        <div style={{ width: "100%", height: "100%", background: `linear-gradient(90deg, ${THREAD}, ${colors.accent})`, transform: `scaleX(${line})`, transformOrigin: "left center", borderRadius: 2 }} />
      </div>
      {t.schritte.map((s, i) => {
        const at = 84 + i * 30;
        return (
          <div key={s.titel} style={{ position: "absolute", left: layout.margin + i * (w + 40), top: 440, width: w, display: "flex", flexDirection: "column", gap: 16, ...rise(f, at, 18, 20) }}>
            <div style={{ width: 76, height: 76, borderRadius: 38, background: colors.card, border: `4px solid ${colors.bg}`, boxShadow: "0 6px 18px rgba(22,54,92,0.14)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: fonts.serif, fontWeight: 700, fontSize: 32, color: colors.primary }}>
              {i + 1}
            </div>
            <div style={{ fontFamily: fonts.serif, fontWeight: 600, fontSize: 32, color: colors.text }}>{s.titel}</div>
            <div style={{ fontSize: 23, lineHeight: 1.4, color: colors.muted }}>{s.text}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
