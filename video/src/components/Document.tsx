import React from "react";
import { colors, fonts, layout } from "../theme";
import { brief, marks, type MarkId } from "../texts";
import { MorphSpan } from "./MorphSpan";

export type MarkState = { highlight: number; morph: number; kept: number };
export type MarkStates = Record<MarkId, MarkState>;

const idle: MarkState = { highlight: 0, morph: 0, kept: 0 };
export const idleStates: MarkStates = {
  name: idle,
  adresse: idle,
  ort: idle,
  az: idle,
  anrede: idle,
  gericht: idle,
};

/** Endzustand nach Szene 3: alles ersetzt, das Gericht bleibt stehen. */
const done: MarkState = { highlight: 1, morph: 1, kept: 0 };
export const finalStates: MarkStates = {
  name: done,
  adresse: done,
  ort: done,
  az: done,
  anrede: done,
  gericht: { highlight: 1, morph: 0, kept: 1 },
};

const Line: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ height: layout.doc.lineHeight, lineHeight: `${layout.doc.lineHeight}px`, whiteSpace: "nowrap" }}>
    {children}
  </div>
);

const Gap: React.FC = () => <div style={{ height: 20 }} />;

const Bar: React.FC<{ w: number }> = ({ w }) => (
  <div style={{ height: layout.doc.lineHeight, display: "flex", alignItems: "center" }}>
    <div style={{ height: 13, width: `${w * 100}%`, borderRadius: 7, background: colors.bar }} />
  </div>
);

/** Stilisierter Musterbrief mit markierbaren Stellen. */
export const Document: React.FC<{ states: MarkStates }> = ({ states }) => {
  const M = (id: MarkId) => (
    <MorphSpan
      original={marks[id].text}
      placeholder={marks[id].ph}
      kind={marks[id].kind}
      highlight={states[id].highlight}
      morph={states[id].morph}
      kept={states[id].kept}
      fontSize={layout.doc.fontSize}
    />
  );

  return (
    <div
      style={{
        width: layout.doc.w,
        height: layout.doc.h,
        boxSizing: "border-box",
        padding: layout.doc.pad,
        background: colors.card,
        borderRadius: 12,
        border: `1px solid ${colors.bar}`,
        boxShadow: "0 10px 34px rgba(22,54,92,0.10)",
        fontFamily: fonts.sans,
        fontSize: layout.doc.fontSize,
        color: colors.text,
        overflow: "hidden",
      }}
    >
      <Line>{M("name")}</Line>
      <Line>{M("adresse")}</Line>
      <Line>{M("ort")}</Line>
      <Gap />
      <Line>
        {brief.azLabel}
        {M("az")}
      </Line>
      <Gap />
      <Line>
        {brief.anredeVor}
        {M("anrede")}
        {brief.anredeNach}
      </Line>
      <Gap />
      <Line>
        {brief.satz1Vor}
        {M("gericht")}
        {brief.satz1Nach}
      </Line>
      <Line>{brief.satz2}</Line>
      <Bar w={0.94} />
      <Bar w={0.88} />
      <Bar w={0.97} />
      <Bar w={0.52} />
      <Gap />
      <Line>{brief.gruss}</Line>
    </div>
  );
};
