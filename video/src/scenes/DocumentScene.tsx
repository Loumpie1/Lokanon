import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Caption } from "../components/Caption";
import { Document, type MarkStates } from "../components/Document";
import { Toggle } from "../components/Toggle";
import { colors, easeInOut, fonts, inOut, layout, lerp, tween } from "../theme";
import { legende, marks, texts, type MarkId, type MarkKind } from "../texts";

// Zeitpunkte (Frames ab Szenenbeginn, 30 fps)
const HL: Record<MarkId, number> = { name: 28, adresse: 40, ort: 48, az: 60, anrede: 72, gericht: 84 };
const MO: Record<MarkId, number> = { name: 170, adresse: 180, ort: 188, az: 196, anrede: 204, gericht: 212 };
const TOGGLE_AT = 250; // Schalter kippt auf "bleibt stehen"
const PANEL_SWAP = 152; // Legende → Prüfkarten

const Dot: React.FC<{ kind: MarkKind; size?: number }> = ({ kind, size = 16 }) => (
  <span
    style={{
      display: "inline-block",
      width: size,
      height: size,
      borderRadius: size / 2,
      background: colors.mark[kind],
      border: `2px solid ${colors.markBorder[kind]}`,
      boxSizing: "border-box",
      flexShrink: 0,
    }}
  />
);

const Legend: React.FC<{ f: number }> = ({ f }) => {
  const counts: Record<MarkKind, { at: number[] }> = {
    person: { at: [HL.name, HL.anrede] },
    adresse: { at: [HL.adresse, HL.ort] },
    nummer: { at: [HL.az] },
    firma: { at: [HL.gericht] },
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{ fontFamily: fonts.serif, fontWeight: 600, fontSize: 32, color: colors.primary, marginBottom: 10 }}>
        {texts.legendeTitel}
      </div>
      {legende.map((row) => {
        const times = counts[row.kind].at;
        const first = times[0];
        const count = times.filter((t) => f >= t + 4).length;
        const lastChange = times.filter((t) => f >= t + 4).pop() ?? first;
        const appear = tween(f, [first, first + 16]);
        const pop = 1 + 0.18 * (1 - tween(f, [lastChange + 4, lastChange + 16]));
        return (
          <div
            key={row.kind}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "18px 28px",
              background: colors.card,
              borderRadius: 12,
              border: `1px solid ${colors.bar}`,
              fontSize: 28,
              color: colors.text,
              opacity: appear,
              transform: `translateX(${(1 - appear) * 24}px)`,
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <Dot kind={row.kind} />
              {row.label}
            </span>
            <span
              style={{
                fontWeight: 600,
                color: colors.primary,
                display: "inline-block",
                transform: `scale(${pop})`,
                minWidth: 36,
                textAlign: "right",
              }}
            >
              {count}
            </span>
          </div>
        );
      })}
    </div>
  );
};

const cards: MarkId[] = ["name", "adresse", "az", "gericht"];

const ReviewCards: React.FC<{ f: number }> = ({ f }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
    <div style={{ fontFamily: fonts.serif, fontWeight: 600, fontSize: 32, color: colors.primary, marginBottom: 10 }}>
      {texts.pruefenTitel}
    </div>
    {cards.map((id, i) => {
      const appear = tween(f, [PANEL_SWAP + 6 + i * 6, PANEL_SWAP + 24 + i * 6]);
      const isGericht = id === "gericht";
      const on = isGericht ? tween(f, [TOGGLE_AT, TOGGLE_AT + 12], [1, 0], easeInOut) : 1;
      const swap = isGericht ? tween(f, [TOGGLE_AT + 4, TOGGLE_AT + 14]) : 0;
      return (
        <div
          key={id}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "20px 28px",
            background: colors.card,
            borderRadius: 12,
            border: `1px solid ${isGericht && swap > 0.5 ? colors.accent : colors.bar}`,
            boxShadow: isGericht ? `0 0 0 ${3 * swap}px rgba(14,159,138,${0.18 * swap})` : undefined,
            opacity: appear,
            transform: `translateY(${(1 - appear) * 16}px)`,
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 28, fontWeight: 600, color: colors.text }}>
              <Dot kind={marks[id].kind} />
              {marks[id].text}
            </span>
            <span style={{ fontSize: 23, color: colors.muted, paddingLeft: 30, position: "relative", height: 30 }}>
              <span style={{ position: "absolute", left: 30, top: 0, opacity: 1 - swap, whiteSpace: "nowrap" }}>
                →{" "}
                <span
                  style={{
                    display: "inline-block",
                    padding: "1px 10px",
                    borderRadius: 7,
                    background: colors.mark[marks[id].kind],
                    border: `1.5px solid ${colors.markBorder[marks[id].kind]}`,
                    color: colors.text,
                    fontWeight: 600,
                    fontSize: 21,
                    lineHeight: "24px",
                  }}
                >
                  {marks[id].ph}
                </span>
              </span>
              <span style={{ position: "absolute", left: 30, top: 0, opacity: swap, whiteSpace: "nowrap" }}>
                {texts.bleibtStehen}
              </span>
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, minWidth: 150 }}>
            <Toggle on={on} width={68} />
            <span style={{ fontSize: 21, color: lerp(0, 1, swap) > 0.5 ? colors.muted : colors.accent, position: "relative", height: 26 }}>
              <span style={{ position: "absolute", left: "50%", transform: "translateX(-50%)", opacity: 1 - swap, whiteSpace: "nowrap", color: colors.accent }}>
                {texts.wirdErsetzt}
              </span>
              <span style={{ position: "absolute", left: "50%", transform: "translateX(-50%)", opacity: swap, whiteSpace: "nowrap", color: colors.muted }}>
                {texts.bleibtStehen}
              </span>
            </span>
          </div>
        </div>
      );
    })}
  </div>
);

/** Szenen 2 und 3 (4–15 s): Erkennen, dann Prüfen mit Schalter. */
export const DocumentScene: React.FC = () => {
  const f = useCurrentFrame();
  const hl = (id: MarkId) => tween(f, [HL[id], HL[id] + 16]);
  const mo = (id: MarkId) => tween(f, [MO[id], MO[id] + 16], [0, 1], easeInOut);
  const revert = tween(f, [TOGGLE_AT + 2, TOGGLE_AT + 18], [0, 1], easeInOut);

  const states: MarkStates = {
    name: { highlight: hl("name"), morph: mo("name"), kept: 0 },
    adresse: { highlight: hl("adresse"), morph: mo("adresse"), kept: 0 },
    ort: { highlight: hl("ort"), morph: mo("ort"), kept: 0 },
    az: { highlight: hl("az"), morph: mo("az"), kept: 0 },
    anrede: { highlight: hl("anrede"), morph: mo("anrede"), kept: 0 },
    gericht: {
      highlight: hl("gericht"),
      morph: mo("gericht") * (1 - revert),
      kept: tween(f, [TOGGLE_AT + 6, TOGGLE_AT + 22]),
    },
  };

  const docIn = tween(f, [0, 18]);
  const panelIn = tween(f, [6, 24]);
  const legendOpacity = inOut(f, 6, PANEL_SWAP + 8, 14);
  const cardsOpacity = tween(f, [PANEL_SWAP + 4, PANEL_SWAP + 18]);
  const panelOut = tween(f, [316, 330], [1, 0]);

  return (
    <AbsoluteFill style={{ fontFamily: fonts.sans }}>
      <div
        style={{
          position: "absolute",
          left: layout.doc.x,
          top: layout.doc.y,
          opacity: docIn,
          transform: `translateY(${(1 - docIn) * 16}px)`,
        }}
      >
        <Document states={states} />
      </div>

      <div
        style={{
          position: "absolute",
          left: layout.panel.x,
          top: layout.panel.y,
          width: layout.panel.w,
          height: layout.panel.h,
          opacity: panelIn * panelOut,
        }}
      >
        <div style={{ position: "absolute", inset: 0, opacity: legendOpacity }}>
          <Legend f={f} />
        </div>
        <div style={{ position: "absolute", inset: 0, opacity: cardsOpacity }}>
          {f > PANEL_SWAP ? <ReviewCards f={f} /> : null}
        </div>
      </div>

      <Caption text={texts.caption2} inAt={10} outAt={PANEL_SWAP} />
      <Caption text={texts.caption3} inAt={PANEL_SWAP + 10} outAt={330} />
    </AbsoluteFill>
  );
};
