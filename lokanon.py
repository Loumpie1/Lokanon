"""Lokanon starten: lokaler Server auf 127.0.0.1 + eigenes Programmfenster (pywebview / Edge WebView2).

    python lokanon.py            Programmfenster
    python lokanon.py --browser  im Standardbrowser öffnen (Fallback)
    python lokanon.py --port 8765

Die Sprachmodelle laden im Hintergrund; die Oberfläche zeigt den Fortschritt.
Ohne Konsole (pythonw) landen Meldungen und Fehler in %USERPROFILE%\\Lokanon\\lokanon.log.
"""
from __future__ import annotations

import argparse
import html
import os
import socket
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR))
# Offline-Betrieb: Modelle liegen lokal (Setup/Installer); keine Download-Versuche zur Laufzeit
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
if (APP_DIR / "models" / "hf").is_dir():
    os.environ.setdefault("HF_HOME", str(APP_DIR / "models" / "hf"))

DATEN_ORDNER = Path(os.environ.get("LOKANON_HOME") or Path.home() / "Lokanon")
LOG_DATEI = DATEN_ORDNER / "lokanon.log"
START_TIMEOUT = 600  # Sekunden; der erste Start nach der Installation kann (Virenscanner, kalter Cache) lange dauern

zustand: dict = {"fehler": None, "thread": None}


def log_einrichten() -> None:
    """Unter pythonw gibt es keine Konsole: Ausgaben in eine Protokolldatei umleiten."""
    if sys.stderr is not None and sys.stdout is not None:
        return
    try:
        DATEN_ORDNER.mkdir(parents=True, exist_ok=True)
        f = open(LOG_DATEI, "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = f
        print(f"\n=== Lokanon gestartet {time.strftime('%Y-%m-%d %H:%M:%S')} aus {APP_DIR} ===")
    except OSError:
        pass


def freier_port(start: int = 8765) -> int:
    for p in range(start, start + 50):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError("Kein freier Port gefunden.")


def server_starten(port: int) -> None:
    try:
        import uvicorn

        from server.app import app, modelle

        modelle.starten()
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    except BaseException as e:  # noqa: BLE001 - alles festhalten, damit das Fenster es anzeigen kann
        zustand["fehler"] = "".join(traceback.format_exception(e)).strip()
        print(zustand["fehler"], file=sys.stderr)
        raise


def warten_bis_bereit(port: int, timeout: float = START_TIMEOUT) -> bool:
    """Wartet, bis der Server antwortet. Bricht früher ab, wenn der Server-Thread gestorben ist."""
    import urllib.request

    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1).read()
            print(f"Server bereit nach {time.time() - t0:.0f} s auf Port {port}.")
            return True
        except Exception:
            th = zustand.get("thread")
            if zustand["fehler"] or (th is not None and not th.is_alive()):
                return False
            time.sleep(0.25)
    zustand["fehler"] = zustand["fehler"] or f"Der lokale Server hat nach {timeout:.0f} s nicht geantwortet."
    return False


_STIL = """
<style>
  :root { color-scheme: light; }
  html, body { height: 100%; margin: 0; }
  body { font: 16px/1.5 "Source Sans 3", "Segoe UI", system-ui, sans-serif; color: #1A2433; background: #F5F7FA;
         display: grid; place-items: center; }
  .k { width: min(460px, 90vw); text-align: center; }
  .marke { display: inline-flex; align-items: center; gap: 12px; color: #16365C; font-weight: 700; font-size: 28px;
           font-family: "Source Serif 4", Georgia, serif; margin-bottom: 28px; }
  h1 { font-size: 20px; margin: 0 0 8px; font-weight: 600; }
  p { margin: 0; color: #5B6778; }
  .balken { height: 4px; background: #DCE3EC; border-radius: 2px; overflow: hidden; margin: 28px auto 0; width: 240px; }
  .balken i { display: block; height: 100%; width: 40%; background: #1F5FA8; border-radius: 2px;
              animation: lauf 1.6s ease-in-out infinite; }
  @keyframes lauf { 0% { transform: translateX(-100%); } 100% { transform: translateX(600px); } }
  @media (prefers-reduced-motion: reduce) { .balken i { animation: none; width: 100%; opacity: .5; } }
  pre { text-align: left; font-size: 12px; background: #fff; border: 1px solid #DCE3EC; border-radius: 8px;
        padding: 12px; max-height: 240px; overflow: auto; white-space: pre-wrap; margin-top: 20px; }
  .fehler h1 { color: #B3261E; }
</style>
"""
_SCHILD = ('<svg width="34" height="38" viewBox="0 0 34 38" fill="none" aria-hidden="true">'
           '<path d="M17 2 3 7v11c0 9 6 15 14 18 8-3 14-9 14-18V7L17 2Z" stroke="#16365C" stroke-width="2.5" '
           'fill="#E3ECF7"/><path d="m11 19 4 4 8-9" stroke="#0E9F8A" stroke-width="2.5" stroke-linecap="round" '
           'stroke-linejoin="round"/></svg>')

SPLASH_HTML = f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Lokanon</title>{_STIL}</head>
<body><div class="k"><div class="marke">{_SCHILD}Lokanon</div>
<h1>Lokanon wird gestartet …</h1>
<p>Die Sprachmodelle werden geladen. Beim ersten Start nach der Installation kann das ein bis zwei Minuten dauern.</p>
<div class="balken"><i></i></div></div></body></html>"""


def fehler_html(text: str) -> str:
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Lokanon</title>{_STIL}</head>
<body><div class="k fehler"><div class="marke">{_SCHILD}Lokanon</div>
<h1>Lokanon konnte nicht gestartet werden</h1>
<p>Bitte schließen Sie das Fenster und starten Sie Lokanon erneut. Bleibt der Fehler, hilft die Protokolldatei
<br><b>{html.escape(str(LOG_DATEI))}</b></p>
<pre>{html.escape(text)}</pre></div></body></html>"""


def im_browser(url: str) -> None:
    if not warten_bis_bereit(url_port(url)):
        print(f"Der lokale Server ist nicht gestartet.\n{zustand['fehler']}", file=sys.stderr)
        sys.exit(1)
    webbrowser.open(url)
    print(f"Lokanon läuft unter {url} – Fenster mit Strg+C schließen.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return


def url_port(url: str) -> int:
    return int(url.rsplit(":", 1)[1].rstrip("/"))


def main() -> None:
    log_einrichten()
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", action="store_true", help="im Standardbrowser statt im Programmfenster öffnen")
    ap.add_argument("--serve", action="store_true", help="nur den lokalen Server starten (Entwicklung), nichts öffnen")
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()
    port = args.port or freier_port()
    if args.serve:
        print(f"Lokanon-Server unter http://127.0.0.1:{port}/ – beenden mit Strg+C.")
        server_starten(port)
        return
    th = threading.Thread(target=server_starten, args=(port,), daemon=True)
    zustand["thread"] = th
    th.start()
    url = f"http://127.0.0.1:{port}/"
    if args.browser:
        im_browser(url)
        return
    try:
        import webview

        from server.app import fenster
    except Exception as e:  # pywebview/WebView2 nicht verfügbar -> Browser
        print(f"Programmfenster nicht verfügbar ({e}); öffne Browser.", file=sys.stderr)
        im_browser(url)
        return

    webview.settings["ALLOW_DOWNLOADS"] = True  # ZIP und Schlüsseldatei aus dem Fenster speichern
    w = webview.create_window("Lokanon", html=SPLASH_HTML, width=1280, height=860, min_size=(960, 640),
                              background_color="#F5F7FA", text_select=True)
    fenster["webview"] = w

    def nachladen() -> None:
        if warten_bis_bereit(port):
            w.load_url(url)
        else:
            print(f"Der lokale Server ist nicht gestartet.\n{zustand['fehler']}", file=sys.stderr)
            w.load_html(fehler_html(zustand["fehler"] or "Unbekannter Fehler."))

    ico = APP_DIR / "assets" / "lokanon.ico"  # Windows (WinForms) braucht eine .ico-Datei
    webview.start(nachladen, private_mode=False, icon=str(ico) if ico.exists() else None)


if __name__ == "__main__":
    main()
