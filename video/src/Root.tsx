import React from "react";
import { Composition } from "remotion";
import { LokanonTeaser } from "./LokanonTeaser";
import { LokanonVisitenkarte, VK_FRAMES } from "./LokanonVisitenkarte";
import { FPS, TOTAL_FRAMES } from "./theme";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="LokanonTeaser"
      component={LokanonTeaser}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={1920}
      height={1080}
    />
    <Composition
      id="LokanonVisitenkarte"
      component={LokanonVisitenkarte}
      durationInFrames={VK_FRAMES}
      fps={FPS}
      width={1920}
      height={1080}
    />
  </>
);
