import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { Caption } from "../../components/Caption";
import { colors, fonts, inOut, layout, tween } from "../../theme";
import { vk } from "../../texts_vk";
import { Bullets, rise } from "./ui";

const PER = 150; // Frames je Bildschirm
const FRAME = { x: 120, y: 150, w: 1120, h: 700 };

/** Bildschirme (15 s): drei echte Ansichten mit langsamer Fahrt und Stichpunkten. */
export const Bildschirme: React.FC = () => {
  const f = useCurrentFrame();
  const t = vk.bildschirme;
  return (
    <AbsoluteFill style={{ fontFamily: fonts.sans }}>
      {t.seiten.map((s, i) => {
        const l = f - i * PER;
        if (l < -16 || l > PER + 16) return null;
        const vis = inOut(l, 0, PER, 14);
        const zoom = tween(l, [0, PER], [1, 1.07], (x) => x);
        const ox = ["20% 15%", "70% 30%", "30% 75%"][i];
        return (
          <div key={s.datei} style={{ position: "absolute", inset: 0, opacity: vis }}>
            <div style={{ position: "absolute", left: FRAME.x, top: FRAME.y, width: FRAME.w, height: FRAME.h, borderRadius: 16, overflow: "hidden", background: colors.card, border: `1px solid ${colors.bar}`, boxShadow: "0 18px 50px rgba(22,54,92,0.18)" }}>
              <Img src={staticFile(s.datei)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})`, transformOrigin: ox }} />
            </div>
            <div style={{ position: "absolute", left: 1300, top: 190, width: 500, display: "flex", flexDirection: "column", gap: 22 }}>
              <div style={{ width: 58, height: 58, borderRadius: 29, background: colors.action, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: fonts.serif, fontWeight: 700, fontSize: 28, ...rise(l, 10, 14, 12) }}>
                {i + 1}
              </div>
              <div style={{ fontFamily: fonts.serif, fontWeight: 700, fontSize: 46, color: colors.text, lineHeight: 1.1, ...rise(l, 16) }}>{s.titel}</div>
              <Bullets f={l} at={30} items={s.punkte} size={25} color={colors.muted} gap={16} />
            </div>
          </div>
        );
      })}
      <Caption text={t.caption} inAt={6} outAt={3 * PER} />
    </AbsoluteFill>
  );
};
