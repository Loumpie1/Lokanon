import React from "react";
import { useCurrentFrame } from "remotion";
import { colors, fonts, inOut, layout, tween } from "../theme";

/** Große Bildunterschrift am unteren Rand, blendet ein ab `inAt`, aus bis `outAt`. */
export const Caption: React.FC<{ text: string; inAt: number; outAt: number; dark?: boolean }> = ({
  text,
  inAt,
  outAt,
  dark = false,
}) => {
  const frame = useCurrentFrame();
  const opacity = inOut(frame, inAt, outAt, 16);
  const y = tween(frame, [inAt, inAt + 18], [18, 0]);
  return (
    <div
      style={{
        position: "absolute",
        left: layout.margin,
        right: layout.margin,
        top: layout.captionY,
        textAlign: "center",
        fontFamily: fonts.serif,
        fontWeight: 600,
        fontSize: layout.captionSize,
        lineHeight: 1.25,
        color: dark ? "#FFFFFF" : colors.text,
        opacity,
        transform: `translateY(${y}px)`,
        letterSpacing: "-0.005em",
      }}
    >
      {text}
    </div>
  );
};
