import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Caption } from "../components/Caption";
import { Document, finalStates } from "../components/Document";
import { Key, Lock } from "../components/Icons";
import { MorphSpan } from "../components/MorphSpan";
import { colors, easeInOut, fonts, inOut, layout, lerp, tween } from "../theme";
import { antwort, marks, texts } from "../texts";

const chat = layout.panel;
const THUMB_SCALE = 0.2;
const BUBBLE_FONT = 24;

/** Platzhalter-Chip (statisch) in Chat-Blasen. */
const Chip: React.FC<{ id: "az" | "name" | "adresse"; size?: number; morph?: number }> = ({
  id,
  size = BUBBLE_FONT,
  morph = 1,
}) => (
  <MorphSpan
    original={marks[id].text}
    placeholder={marks[id].ph}
    kind={marks[id].kind}
    highlight={1}
    morph={morph}
    fontSize={size}
  />
);

const AnswerText: React.FC<{ size: number; morph: { az: number; name: number; adresse: number } }> = ({
  size,
  morph,
}) => (
  <div style={{ fontSize: size, lineHeight: `${Math.round(size * 1.55)}px`, whiteSpace: "nowrap" }}>
    <div>
      {antwort.l1Vor}
      <Chip id="az" size={size} morph={morph.az} />
      {antwort.l1Nach}
    </div>
    <div>
      <Chip id="name" size={size} morph={morph.name} />
      {antwort.l2Nach}
    </div>
    <div>{antwort.l3}</div>
    <div>
      <Chip id="adresse" size={size} morph={morph.adresse} />
      {antwort.l4Nach}
    </div>
  </div>
);

/** Szenen 4 und 5 (15–26 s): Dokument fliegt in den Chat, Antwort kommt zurück und wird rückübersetzt. */
export const ChatScene: React.FC = () => {
  const g = useCurrentFrame();

  // Dokument fliegt als Miniatur in den Chat
  const fly = tween(g, [8, 46], [0, 1], easeInOut);
  const docX = lerp(layout.doc.x, chat.x + chat.w - 40 - layout.doc.w * THUMB_SCALE, fly);
  const docY = lerp(layout.doc.y, chat.y + 84, fly);
  const docScale = lerp(1, THUMB_SCALE, fly);
  const docOpacity = tween(g, [42, 54], [1, 0]);

  // Chatfenster: rückt in die Mitte, solange links nichts steht
  const chatIn = tween(g, [0, 22]);
  const centered =
    tween(g, [56, 90], [0, 1], easeInOut) - tween(g, [176, 208], [0, 1], easeInOut);
  const chatShift = tween(g, [0, 26], [60, 0]) + lerp(0, (1920 - chat.w) / 2 - chat.x, centered);
  const dim = tween(g, [180, 202]);
  const chatOpacity = chatIn * lerp(1, 0.4, dim);
  const chatScale = lerp(1, 0.97, dim);

  const userIn = tween(g, [46, 60]);
  const typing = inOut(g, 62, 98, 8);
  const answerIn = tween(g, [98, 114]);

  // Rückübersetzung links
  const cardIn = tween(g, [180, 200]);
  const cardShift = tween(g, [180, 204], [-30, 0]);
  const back = (at: number) => 1 - tween(g, [at, at + 18], [0, 1], easeInOut);
  const keyIn = tween(g, [232, 252]);
  const keyShift = tween(g, [232, 256], [-18, 0]);

  const sceneOut = tween(g, [316, 330], [1, 0]);

  return (
    <AbsoluteFill style={{ fontFamily: fonts.sans, opacity: sceneOut }}>
      {/* Chatfenster, neutral */}
      <div
        style={{
          position: "absolute",
          left: chat.x,
          top: chat.y,
          width: chat.w,
          height: chat.h,
          opacity: chatOpacity,
          transform: `translateX(${chatShift}px) scale(${chatScale})`,
          transformOrigin: "center",
          background: colors.card,
          borderRadius: 14,
          border: `1px solid ${colors.bar}`,
          boxShadow: "0 10px 34px rgba(22,54,92,0.10)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: 60,
            borderBottom: `1px solid ${colors.bar}`,
            display: "flex",
            alignItems: "center",
            padding: "0 22px",
            gap: 10,
            color: colors.muted,
            fontSize: 22,
          }}
        >
          {[0, 1, 2].map((i) => (
            <span key={i} style={{ width: 13, height: 13, borderRadius: 7, background: colors.line }} />
          ))}
          <span style={{ flex: 1, textAlign: "center", paddingRight: 60 }}>{texts.chatTitel}</span>
        </div>

        {/* Nutzer-Blase */}
        <div
          style={{
            position: "absolute",
            right: 40,
            top: 84,
            opacity: userIn,
            transform: `translateY(${(1 - userIn) * 8}px)`,
            background: colors.action,
            color: "#FFFFFF",
            borderRadius: "18px 18px 6px 18px",
            padding: "16px 22px",
            fontSize: BUBBLE_FONT,
            lineHeight: "38px",
            whiteSpace: "nowrap",
          }}
        >
          <div>
            {texts.frageL1} <Chip id="az" />
          </div>
          <div>
            {texts.frageL2} <Chip id="name" />.
          </div>
        </div>

        {/* Tipp-Anzeige */}
        <div
          style={{
            position: "absolute",
            left: 40,
            top: 214,
            opacity: typing,
            background: colors.bubble,
            borderRadius: "18px 18px 18px 6px",
            padding: "18px 22px",
            display: "flex",
            gap: 8,
          }}
        >
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              style={{
                width: 11,
                height: 11,
                borderRadius: 6,
                background: colors.muted,
                transform: `translateY(${Math.sin((g - 62) / 5 + i * 1.3) * 3}px)`,
                opacity: 0.6 + 0.4 * Math.max(0, Math.sin((g - 62) / 5 + i * 1.3)),
              }}
            />
          ))}
        </div>

        {/* Antwort-Blase */}
        <div
          style={{
            position: "absolute",
            left: 40,
            top: 214,
            opacity: answerIn,
            transform: `translateY(${(1 - answerIn) * 10}px)`,
            background: colors.bubble,
            color: colors.text,
            borderRadius: "18px 18px 18px 6px",
            padding: "16px 22px",
          }}
        >
          <AnswerText size={BUBBLE_FONT} morph={{ az: 1, name: 1, adresse: 1 }} />
        </div>

        {/* Eingabezeile */}
        <div
          style={{
            position: "absolute",
            left: 28,
            right: 28,
            bottom: 26,
            height: 56,
            borderRadius: 28,
            border: `1px solid ${colors.line}`,
            display: "flex",
            alignItems: "center",
            padding: "0 8px 0 24px",
            justifyContent: "space-between",
            color: colors.muted,
            fontSize: 22,
          }}
        >
          <span style={{ opacity: 0.8 }}>{texts.chatEingabe}</span>
          <span style={{ width: 40, height: 40, borderRadius: 20, background: colors.line }} />
        </div>
      </div>

      {/* Anonymisiertes Dokument (fliegt in den Chat) */}
      <div
        style={{
          position: "absolute",
          left: docX,
          top: docY,
          transform: `scale(${docScale})`,
          transformOrigin: "top left",
          opacity: docOpacity,
        }}
      >
        <Document states={finalStates} />
      </div>

      {/* Rückübersetzte Antwort */}
      <div
        style={{
          position: "absolute",
          left: layout.doc.x,
          top: layout.doc.y,
          width: layout.doc.w,
          opacity: cardIn,
          transform: `translateX(${cardShift}px)`,
          background: colors.card,
          borderRadius: 12,
          border: `1px solid ${colors.bar}`,
          boxShadow: "0 10px 34px rgba(22,54,92,0.10)",
          padding: "40px 48px 44px",
          boxSizing: "border-box",
          color: colors.text,
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 30 }}>
          <div style={{ fontFamily: fonts.serif, fontWeight: 600, fontSize: 34, color: colors.primary, lineHeight: 1.2 }}>
            {texts.antwortTitel}
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8, opacity: keyIn }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ display: "inline-flex", transform: `translateX(${keyShift}px)`, opacity: keyIn }}>
                <Key size={44} />
              </span>
              <Lock size={44} color={colors.primary} />
            </div>
            <span style={{ fontSize: 22, color: colors.muted, whiteSpace: "nowrap" }}>{texts.schluesselHinweis}</span>
          </div>
        </div>
        <AnswerText size={28} morph={{ az: back(216), name: back(230), adresse: back(244) }} />
      </div>

      <Caption text={texts.caption4} inAt={14} outAt={180} />
      <Caption text={texts.caption5} inAt={188} outAt={330} />
    </AbsoluteFill>
  );
};
