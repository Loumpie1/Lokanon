import React from "react";
import { AbsoluteFill, Sequence, interpolateColors, useCurrentFrame, useVideoConfig } from "remotion";
import { Header } from "./components/Header";
import { useFontsReady } from "./fonts";
import { ChatScene } from "./scenes/ChatScene";
import { DocumentScene } from "./scenes/DocumentScene";
import { Ablauf } from "./scenes/vk/Ablauf";
import { AktTitel } from "./scenes/vk/AktTitel";
import { Bildschirme } from "./scenes/vk/Bildschirme";
import { Funktionen } from "./scenes/vk/Funktionen";
import { Grenzen } from "./scenes/vk/Grenzen";
import { Karten } from "./scenes/vk/Karten";
import { Konflikt } from "./scenes/vk/Konflikt";
import { Montag } from "./scenes/vk/Montag";
import { Schluessel } from "./scenes/vk/Schluessel";
import { VkIntro } from "./scenes/vk/VkIntro";
import { VkOutro } from "./scenes/vk/VkOutro";
import { colors, fonts, inOut, tween } from "./theme";
import { vk } from "./texts_vk";

type Szene = { id: string; duration: number; dark: boolean; node: React.ReactNode; header?: boolean };

/** Szenenfolge des Visitenkarten-Films (Frames bei 30 fps). */
const SZENEN: Szene[] = [
  { id: "Intro", duration: 150, dark: true, node: <VkIntro /> },
  { id: "Akt 1", duration: 60, dark: true, node: <AktTitel nr={vk.akte[0].nr} titel={vk.akte[0].titel} /> },
  { id: "Montag", duration: 300, dark: false, node: <Montag />, header: true },
  { id: "Konflikt", duration: 300, dark: false, node: <Konflikt />, header: true },
  { id: "Akt 2", duration: 60, dark: true, node: <AktTitel nr={vk.akte[1].nr} titel={vk.akte[1].titel} /> },
  { id: "Erkennen und Prüfen", duration: 330, dark: false, node: <DocumentScene />, header: true },
  { id: "Akt 3", duration: 60, dark: true, node: <AktTitel nr={vk.akte[2].nr} titel={vk.akte[2].titel} /> },
  { id: "KI und Rückübersetzung", duration: 330, dark: false, node: <ChatScene />, header: true },
  { id: "Schlüssel", duration: 240, dark: false, node: <Schluessel />, header: true },
  { id: "Funktionen", duration: 420, dark: true, node: <Funktionen /> },
  { id: "Ablauf", duration: 240, dark: false, node: <Ablauf />, header: true },
  { id: "Bildschirme", duration: 450, dark: false, node: <Bildschirme />, header: true },
  { id: "Grenzen", duration: 240, dark: false, node: <Grenzen />, header: true },
  { id: "Visitenkarten", duration: 360, dark: false, node: <Karten />, header: true },
  { id: "Epilog", duration: 240, dark: true, node: <VkOutro /> },
];

const starts = SZENEN.reduce<number[]>((acc, s, i) => [...acc, i === 0 ? 0 : acc[i - 1] + SZENEN[i - 1].duration], []);
export const VK_FRAMES = starts[starts.length - 1] + SZENEN[SZENEN.length - 1].duration;

const Fade: React.FC<{ children: React.ReactNode; len?: number }> = ({ children, len = 12 }) => {
  const f = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return <AbsoluteFill style={{ opacity: inOut(f, 0, durationInFrames, len) }}>{children}</AbsoluteFill>;
};

export const LokanonVisitenkarte: React.FC = () => {
  const frame = useCurrentFrame();
  const ready = useFontsReady();

  // Hintergrund: dunkel/hell je Szene, Übergang in den letzten 16 Frames der vorigen Szene
  let bgDark = SZENEN[0].dark ? 1 : 0;
  for (let i = 1; i < SZENEN.length; i++) {
    const from = starts[i];
    const t = tween(frame, [from - 16, from + 2]);
    bgDark = bgDark + ((SZENEN[i].dark ? 1 : 0) - bgDark) * t;
  }
  const background = interpolateColors(bgDark, [0, 1], [colors.bg, colors.primary]);

  return (
    <AbsoluteFill style={{ background, fontFamily: fonts.sans }}>
      <AbsoluteFill style={{ opacity: bgDark, background: `radial-gradient(ellipse 60% 55% at 50% 42%, ${colors.primaryGlow} 0%, rgba(30,74,122,0) 70%)` }} />
      {ready
        ? SZENEN.map((s, i) => (
            <Sequence key={s.id} from={starts[i]} durationInFrames={s.duration} name={s.id}>
              <Fade>
                {s.header ? <Header /> : null}
                {s.node}
              </Fade>
            </Sequence>
          ))
        : null}
    </AbsoluteFill>
  );
};
