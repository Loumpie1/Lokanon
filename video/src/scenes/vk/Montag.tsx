import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Caption } from "../../components/Caption";
import { Document, idleStates, type MarkStates } from "../../components/Document";
import { colors, fonts, layout, tween } from "../../theme";
import { vk } from "../../texts_vk";
import { SceneHead, countUp, rise } from "./ui";

/** Akt 1, Szene 1 (10 s): Montag, Akte, Frist – und ein Name auf Seite 1. */
export const Montag: React.FC = () => {
  const f = useCurrentFrame();
  const t = vk.montag;
  const nameHl = tween(f, [150, 168]);
  const states: MarkStates = { ...idleStates, name: { highlight: nameHl, morph: 0, kept: 0 }, anrede: { highlight: tween(f, [164, 180]), morph: 0, kept: 0 } };
  const docIn = tween(f, [40, 62]);
  const pulse = 0.5 + 0.5 * Math.sin((f - 170) / 6);
  const ring = f > 170 ? 0.35 * pulse : 0;
  return (
    <AbsoluteFill style={{ fontFamily: fonts.sans }}>
      <SceneHead f={f} eyebrow={t.eyebrow} title={t.titel} width={820} />
      <div style={{ position: "absolute", left: layout.margin, top: 330, width: 800, fontSize: 30, lineHeight: 1.45, color: colors.muted, ...rise(f, 26) }}>{t.lede}</div>
      <div style={{ position: "absolute", left: layout.margin, top: 470, display: "flex", gap: 70 }}>
        {t.stats.map((s, i) => (
          <div key={s.label} style={{ display: "flex", flexDirection: "column", gap: 4, ...rise(f, 50 + i * 10) }}>
            <div style={{ fontFamily: fonts.serif, fontWeight: 700, fontSize: 92, lineHeight: 1, color: colors.primary, fontVariantNumeric: "tabular-nums" }}>{countUp(f, 60 + i * 10, s.wert)}</div>
            <div style={{ fontSize: 20, letterSpacing: "0.08em", textTransform: "uppercase", color: colors.muted, fontWeight: 600 }}>{s.label}</div>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: layout.margin, top: 680, width: 800, fontSize: 30, lineHeight: 1.45, color: colors.text, ...rise(f, 176) }}>
        <b>Und genau dieser Name macht die Cloud tabu.</b> Hier beginnt der rote Faden: die Person in der Akte.
      </div>
      <div style={{ position: "absolute", left: 1040, top: 150, transform: `scale(0.82)`, transformOrigin: "top left", opacity: docIn }}>
        <div style={{ position: "relative" }}>
          <Document states={states} />
          <div style={{ position: "absolute", left: 44, top: 44, width: 230, height: 60, borderRadius: 10, boxShadow: `0 0 0 10px rgba(209,59,91,${ring})`, pointerEvents: "none" }} />
        </div>
      </div>
      <Caption text={t.caption} inAt={196} outAt={300} />
    </AbsoluteFill>
  );
};
