import React from "react";
import { AbsoluteFill, Sequence, interpolate, interpolateColors, useCurrentFrame } from "remotion";
import { Header } from "./components/Header";
import { useFontsReady } from "./fonts";
import { ChatScene } from "./scenes/ChatScene";
import { DocumentScene } from "./scenes/DocumentScene";
import { Intro } from "./scenes/Intro";
import { Outro } from "./scenes/Outro";
import { colors, fonts } from "./theme";

// Szenenstart in Frames (30 fps)
export const SCENES = {
  intro: { from: 0, duration: 120 },
  document: { from: 120, duration: 330 },
  chat: { from: 450, duration: 330 },
  outro: { from: 780, duration: 120 },
} as const;

const DARK_TO_LIGHT: [number, number] = [106, 128];
const LIGHT_TO_DARK: [number, number] = [768, 790];

export const LokanonTeaser: React.FC = () => {
  const frame = useCurrentFrame();
  const ready = useFontsReady();

  const stops = [DARK_TO_LIGHT[0], DARK_TO_LIGHT[1], LIGHT_TO_DARK[0], LIGHT_TO_DARK[1]];
  const background = interpolateColors(frame, stops, [colors.primary, colors.bg, colors.bg, colors.primary]);
  const glow = interpolate(frame, stops, [1, 0, 0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background, fontFamily: fonts.sans }}>
      <AbsoluteFill
        style={{
          opacity: glow,
          background: `radial-gradient(ellipse 60% 55% at 50% 42%, ${colors.primaryGlow} 0%, rgba(30,74,122,0) 70%)`,
        }}
      />
      {ready ? (
        <>
          <Sequence from={SCENES.intro.from} durationInFrames={SCENES.intro.duration} name="1 Intro">
            <Intro />
          </Sequence>
          <Sequence from={SCENES.document.from} durationInFrames={SCENES.document.duration + SCENES.chat.duration} name="Kopfzeile">
            <Header />
          </Sequence>
          <Sequence from={SCENES.document.from} durationInFrames={SCENES.document.duration} name="2+3 Dokument">
            <DocumentScene />
          </Sequence>
          <Sequence from={SCENES.chat.from} durationInFrames={SCENES.chat.duration} name="4+5 Chat">
            <ChatScene />
          </Sequence>
          <Sequence from={SCENES.outro.from} durationInFrames={SCENES.outro.duration} name="6 Abspann">
            <Outro />
          </Sequence>
        </>
      ) : null}
    </AbsoluteFill>
  );
};
