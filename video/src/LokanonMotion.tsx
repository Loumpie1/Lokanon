import React, { useEffect, useRef, useState } from "react";
import { AbsoluteFill, Audio, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * Brücke zur motion-anything-Seite (public/ma/index.html): Die Seite läuft in einem gleich-origin iframe und
 * folgt der „einfrierbaren Zeitleiste“ von motion-anything (window.__maTimeline.seek(t)). Remotion ruft seek()
 * je Bild auf und fotografiert dann – so werden auch Shader (WebGL) und Zähler bildgenau, nicht nur CSS.
 */
type MaWindow = Window & { __maTimeline?: { seek: (t: number) => void; duration: number; ready: Promise<void> } };

export const MA_SECONDS = 74;

export const LokanonMotion: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ref = useRef<HTMLIFrameElement>(null);
  const [loadHandle] = useState(() => delayRender("motion-anything-Seite laden"));
  const [loaded, setLoaded] = useState(false);
  const last = useRef<{ frame: number; handle: number | null }>({ frame: -1, handle: null });

  // Je neuem Bild ein Wartegriff, synchron im Render angelegt
  if (last.current.frame !== frame) {
    last.current = { frame, handle: delayRender(`seek ${frame}`) };
  }

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const onLoad = () => {
      const w = el.contentWindow as MaWindow | null;
      const ready = w?.__maTimeline?.ready ?? Promise.resolve();
      ready.then(() => {
        setLoaded(true);
        continueRender(loadHandle);
      });
    };
    el.addEventListener("load", onLoad);
    return () => el.removeEventListener("load", onLoad);
  }, [loadHandle]);

  useEffect(() => {
    if (!loaded) return;
    const w = ref.current?.contentWindow as MaWindow | null;
    try {
      w?.__maTimeline?.seek(frame / fps);
    } catch (e) {
      console.error(e);
    }
    const cur = last.current;
    if (cur.handle !== null) {
      const h = cur.handle;
      cur.handle = null;
      // zwei Bilder Zeit für Shader und Layout, dann freigeben
      requestAnimationFrame(() => requestAnimationFrame(() => continueRender(h)));
    }
  }, [frame, fps, loaded]);

  return (
    <AbsoluteFill style={{ background: "#0D2240" }}>
      {/* Tonspur, per Code erzeugt (tools/sound.py): Ambient-Bett plus Klänge auf die Schlüsselmomente */}
      <Audio src={staticFile("ma/audio/lokanon-motion.mp3")} />
      <iframe
        ref={ref}
        title="Lokanon Motion"
        src={staticFile("ma/index.html")}
        style={{ width: 1920, height: 1080, border: 0, display: "block" }}
      />
    </AbsoluteFill>
  );
};
