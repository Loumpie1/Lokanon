import React from "react";
import { interpolateColors } from "remotion";
import { lerp } from "../theme";

/** Schalter; `on` 0–1 (1 = eingeschaltet). */
export const Toggle: React.FC<{ on: number; width?: number }> = ({ on, width = 64 }) => {
  const h = width * 0.56;
  const knob = h - 8;
  const track = interpolateColors(on, [0, 1], ["#C3CBD6", "#0E9F8A"]);
  return (
    <div
      style={{
        width,
        height: h,
        borderRadius: h / 2,
        background: track,
        position: "relative",
        flexShrink: 0,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 4,
          left: lerp(4, width - knob - 4, on),
          width: knob,
          height: knob,
          borderRadius: knob / 2,
          background: "#FFFFFF",
          boxShadow: "0 1px 3px rgba(0,0,0,0.25)",
        }}
      />
    </div>
  );
};
