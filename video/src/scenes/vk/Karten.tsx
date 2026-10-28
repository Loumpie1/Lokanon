import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { colors, easeInOut, fonts, layout, tween } from "../../theme";
import { vk } from "../../texts_vk";
import { SceneHead, THREAD, rise } from "./ui";

/** Drei Visitenkarten (12 s): kommen herein, drehen sich nacheinander um. */
export const Karten: React.FC = () => {
  const f = useCurrentFrame();
  const t = vk.karten;
  const w = (1680 - 2 * 36) / 3;
  const h = 520;
  return (
    <AbsoluteFill style={{ fontFamily: fonts.sans }}>
      <SceneHead f={f} eyebrow={t.eyebrow} title={t.titel} red={false} />
      {t.karten.map((k, i) => {
        const at = 34 + i * 12;
        const flipAt = 130 + i * 50;
        const rot = tween(f, [flipAt, flipAt + 30], [0, 180], easeInOut);
        const face: React.CSSProperties = { position: "absolute", inset: 0, borderRadius: 16, padding: "32px 34px", boxSizing: "border-box", backfaceVisibility: "hidden", display: "flex", flexDirection: "column", gap: 14 };
        return (
          <div key={k.rolle} style={{ position: "absolute", left: layout.margin + i * (w + 36), top: 330, width: w, height: h, perspective: 1600, ...rise(f, at, 20, 30) }}>
            <div style={{ position: "absolute", inset: 0, transformStyle: "preserve-3d", transform: `rotateY(${rot}deg)` }}>
              <div style={{ ...face, background: colors.card, border: `1px solid ${colors.bar}`, boxShadow: "0 10px 34px rgba(22,54,92,0.10)", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontSize: 20, letterSpacing: "0.14em", textTransform: "uppercase", fontWeight: 700, color: THREAD }}>{k.rolle}</div>
                  <div style={{ fontFamily: fonts.serif, fontWeight: 700, fontSize: 38, lineHeight: 1.12, color: colors.text, marginTop: 14 }}>{k.titel}</div>
                </div>
                <div style={{ fontSize: 25, lineHeight: 1.4, color: colors.muted }}>{k.text}</div>
                <div style={{ fontSize: 20, color: colors.muted, display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ width: 26, height: 26, borderRadius: 13, border: `1.5px solid ${colors.muted}`, display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 15 }}>↻</span>
                  Umdrehen
                </div>
              </div>
              <div style={{ ...face, background: colors.primary, color: "#fff", transform: "rotateY(180deg)" }}>
                <div style={{ fontFamily: fonts.serif, fontWeight: 600, fontSize: 30, color: colors.accentLight }}>{k.rueck}</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 6 }}>
                  {k.punkte.map((p) => (
                    <div key={p} style={{ display: "flex", gap: 12, fontSize: 23, lineHeight: 1.35 }}>
                      <span style={{ color: colors.accentLight }}>›</span>
                      <span>{p}</span>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: "auto", fontFamily: fonts.serif, fontStyle: "italic", fontSize: 24, color: "rgba(255,255,255,0.75)" }}>{k.sig}</div>
              </div>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
