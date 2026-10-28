import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Caption } from "../../components/Caption";
import { colors, fonts, layout } from "../../theme";
import { vk } from "../../texts_vk";
import { Card, SceneHead, WARN, WARN_SOFT, rise } from "./ui";

/** Grenzen (8 s): vier Dinge, die Lokanon nicht verspricht. */
export const Grenzen: React.FC = () => {
  const f = useCurrentFrame();
  const t = vk.grenzen;
  const w = (1680 - 28) / 2;
  return (
    <AbsoluteFill style={{ fontFamily: fonts.sans }}>
      <SceneHead f={f} eyebrow={t.eyebrow} title={t.titel} red={false} />
      {t.punkte.map((p, i) => (
        <Card key={p.titel} style={{ position: "absolute", left: layout.margin + (i % 2) * (w + 28), top: 340 + Math.floor(i / 2) * 230, width: w, height: 200, padding: "28px 32px", display: "flex", gap: 22, alignItems: "flex-start", ...rise(f, 34 + i * 12, 20, 26) }}>
          <div style={{ width: 52, height: 52, borderRadius: 26, background: WARN_SOFT, color: WARN, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: fonts.serif, fontWeight: 700, fontSize: 30, flexShrink: 0 }}>!</div>
          <div>
            <div style={{ fontFamily: fonts.serif, fontWeight: 600, fontSize: 31, color: colors.text, marginBottom: 8 }}>{p.titel}</div>
            <div style={{ fontSize: 24, lineHeight: 1.4, color: colors.muted }}>{p.text}</div>
          </div>
        </Card>
      ))}
      <Caption text={t.caption} inAt={120} outAt={240} />
    </AbsoluteFill>
  );
};
