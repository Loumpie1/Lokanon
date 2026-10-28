import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Caption } from "../../components/Caption";
import { colors, fonts, layout } from "../../theme";
import { vk } from "../../texts_vk";
import { SceneHead, countUp, rise } from "./ui";

const Icon: React.FC<{ name: string }> = ({ name }) => {
  const p: Record<string, React.ReactNode> = {
    pc: <><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" /></>,
    folder: <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />,
    toggle: <><rect x="2" y="7" width="20" height="10" rx="5" /><circle cx="15" cy="12" r="3" /></>,
    tag: <path d="M4 7h16M4 12h10M4 17h7" />,
    scan: <><path d="M4 4h10l6 6v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z" /><path d="M14 4v6h6M8 15h8" /></>,
    shield: <><path d="M12 3l8 4v5c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V7z" /><path d="M9 12l2 2 4-4" /></>,
    link: <path d="M4 12h16M14 6l6 6-6 6" />,
    key: <><circle cx="7.5" cy="12" r="4.5" /><path d="M12 12h9.5M18 12v3.5M21 12v3" /></>,
  };
  return (
    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      {p[name]}
    </svg>
  );
};

/** Produkt-Visitenkarte (14 s, dunkel): Kennzahlen, dann acht Funktionen. */
export const Funktionen: React.FC = () => {
  const f = useCurrentFrame();
  const t = vk.funktionen;
  const kw = (1680 - 3 * 20) / 4;
  const tw = kw;
  return (
    <AbsoluteFill style={{ fontFamily: fonts.sans }}>
      <SceneHead f={f} eyebrow={t.eyebrow} title={t.titel} dark red={false} />
      {t.kpis.map((k, i) => (
        <div key={k.label} style={{ position: "absolute", left: layout.margin + i * (kw + 20), top: 330, width: kw, height: 130, borderRadius: 14, background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.14)", padding: "18px 26px", boxSizing: "border-box", ...rise(f, 30 + i * 8, 18, 22) }}>
          <div style={{ fontFamily: fonts.serif, fontWeight: 700, fontSize: 56, lineHeight: 1, color: "#FFFFFF", fontVariantNumeric: "tabular-nums" }}>
            {countUp(f, 40 + i * 8, k.wert)}
            {k.einheit}
          </div>
          <div style={{ fontSize: 21, color: "rgba(255,255,255,0.7)", marginTop: 8 }}>{k.label}</div>
        </div>
      ))}
      {t.tiles.map((tile, i) => {
        const col = i % 4;
        const row = Math.floor(i / 4);
        return (
          <div key={tile.titel} style={{ position: "absolute", left: layout.margin + col * (tw + 20), top: 490 + row * 196, width: tw, height: 176, borderRadius: 14, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", padding: "20px 24px", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 8, ...rise(f, 120 + i * 9, 18, 24) }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, color: colors.accentLight }}>
              <span style={{ width: 44, height: 44, borderRadius: 10, background: "rgba(127,217,203,0.16)", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
                <Icon name={tile.icon} />
              </span>
              <span style={{ fontFamily: fonts.serif, fontWeight: 600, fontSize: 26, color: "#FFFFFF", lineHeight: 1.1 }}>{tile.titel}</span>
            </div>
            <div style={{ fontSize: 20, lineHeight: 1.35, color: "rgba(255,255,255,0.72)" }}>{tile.text}</div>
          </div>
        );
      })}
      <Caption text={t.caption} inAt={250} outAt={420} dark />
    </AbsoluteFill>
  );
};
