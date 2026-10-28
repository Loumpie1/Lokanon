import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Caption } from "../../components/Caption";
import { Lock } from "../../components/Icons";
import { colors, easeInOut, fonts, layout, tween } from "../../theme";
import { vk } from "../../texts_vk";
import { Bullets, Card, SceneHead, rise } from "./ui";

/** Akt 3, Szene 2 (8 s): zwei Sichten, das Schloss schließt sich. */
export const Schluessel: React.FC = () => {
  const f = useCurrentFrame();
  const t = vk.schluessel;
  const w = (1680 - 32) / 2;
  const closed = tween(f, [110, 134], [0, 1], easeInOut);
  const Pane: React.FC<{ x: number; at: number; wer: string; zitat: string; punkte: readonly string[]; you?: boolean }> = ({ x, at, wer, zitat, punkte, you }) => (
    <Card style={{ position: "absolute", left: x, top: 330, width: w, height: 480, padding: "34px 38px", border: you ? `2.5px solid ${colors.accent}` : undefined, display: "flex", flexDirection: "column", gap: 18, ...rise(f, at, 20, 28) }}>
      <div style={{ fontSize: 20, letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 700, color: you ? colors.accent : colors.muted, display: "flex", alignItems: "center", gap: 14 }}>
        {you ? <Lock size={34} color={colors.accent} closed={closed} /> : null}
        {wer}
      </div>
      <div style={{ fontFamily: fonts.serif, fontSize: 32, lineHeight: 1.3, color: colors.text, minHeight: 130 }}>{zitat}</div>
      <Bullets f={f} at={at + 24} items={punkte} size={24} color={colors.muted} />
    </Card>
  );
  return (
    <AbsoluteFill style={{ fontFamily: fonts.sans }}>
      <SceneHead f={f} eyebrow={t.eyebrow} title={t.titel} />
      <Pane x={layout.margin} at={30} {...t.links} />
      <Pane x={layout.margin + w + 32} at={50} {...t.rechts} you />
      <Caption text={t.caption} inAt={140} outAt={240} />
    </AbsoluteFill>
  );
};
