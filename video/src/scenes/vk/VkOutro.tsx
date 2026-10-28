import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Lockup } from "../../components/Lockup";
import { colors, fonts, tween } from "../../theme";
import { vk } from "../../texts_vk";
import { rise } from "./ui";

/** Epilog (8 s, dunkel): Pilotversion, Paketinhalt, Claim. */
export const VkOutro: React.FC = () => {
  const f = useCurrentFrame();
  const t = vk.outro;
  const claim = tween(f, [160, 184]);
  const rest = tween(f, [150, 172], [1, 0]);
  return (
    <AbsoluteFill style={{ fontFamily: fonts.sans }}>
      <div style={{ position: "absolute", inset: 0, opacity: rest }}>
        <div style={{ position: "absolute", left: 120, top: 150, ...rise(f, 6) }}>
          <Lockup size={60} />
        </div>
        <div style={{ position: "absolute", left: 120, top: 290, fontFamily: fonts.serif, fontWeight: 700, fontSize: 76, color: "#fff", letterSpacing: "-0.01em", ...rise(f, 18) }}>{t.titel}</div>
        <div style={{ position: "absolute", left: 120, top: 400, fontSize: 28, color: "rgba(255,255,255,0.72)", ...rise(f, 30) }}>{t.sub}</div>
        <div style={{ position: "absolute", left: 120, top: 490, width: 1100, display: "flex", flexDirection: "column", gap: 14 }}>
          {t.paket.map((p, i) => (
            <div key={p.tag} style={{ display: "flex", alignItems: "center", gap: 20, padding: "16px 22px", borderRadius: 12, background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.14)", ...rise(f, 48 + i * 10, 16, 18) }}>
              <span style={{ width: 70, height: 38, borderRadius: 8, background: "rgba(127,217,203,0.18)", color: colors.accentLight, display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 19, letterSpacing: "0.04em" }}>{p.tag}</span>
              <span style={{ fontSize: 27, color: "rgba(255,255,255,0.92)" }}>{p.text}</span>
            </div>
          ))}
        </div>
      </div>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: claim }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 48 }}>
          <Lockup size={110} />
          <div style={{ fontFamily: fonts.serif, fontWeight: 600, fontSize: 76, color: "#fff", transform: `translateY(${tween(f, [160, 190], [18, 0])}px)` }}>{t.claim}</div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
