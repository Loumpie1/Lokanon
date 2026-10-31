"""Lokanon-Bundle und Installer bauen.

Aufruf (Dev-venv, aus dem Projektordner):
    C:\\Users\\david\\Lokanon\\venv\\Scripts\\python.exe build\\build.py [--installer] [--version 1.0.0]
        [--work C:\\Users\\david\\Lokanon\\build] [--nur-schritt python|pakete|modelle|projekt|pruefen]

Ergebnis:  <work>\\app\\                              startfähiges Bundle (Standalone-Python + Pakete + Modelle + Projekt)
           <work>\\out\\Lokanon-Setup-<version>.exe    Installer (nur mit --installer)

Das Arbeitsverzeichnis liegt bewusst AUSSERHALB von OneDrive (ca. 2,5 GB, zehntausende Dateien).
Zur Laufzeit zeigt HF_HOME auf <app>\\models\\hf (GLiNER-Gewichte und Tokenizer); lokanon.py setzt die
Variable selbst, Lokanon.cmd zusätzlich für den Start von Hand.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from datetime import date
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parent
PROJEKT = BUILD_DIR.parent
WORK_DEFAULT = Path(os.environ.get("USERPROFILE", "C:/Users/david")) / "Lokanon" / "build"

# python-build-standalone (astral-sh): CPython 3.13, Windows x64, Variante install_only (bringt pip mit)
PBS_TAG = "20261026"
PBS_PY = "3.13.18"
PBS_NAME = f"cpython-{PBS_PY}+{PBS_TAG}-x86_64-pc-windows-msvc-install_only.tar.gz"
PBS_URL = f"https://github.com/astral-sh/python-build-standalone/releases/download/{PBS_TAG}/{PBS_NAME}"

SPACY_MODEL = "de_core_news_lg"
SPACY_WHEEL = ("https://github.com/explosion/spacy-models/releases/download/"
               "de_core_news_lg-3.8.0/de_core_news_lg-3.8.0-py3-none-any.whl")
GLINER_MODEL = "urchade/gliner_multi_pii-v1"
HF_REPOS = [GLINER_MODEL, "microsoft/mdeberta-v3-base"]  # GLiNER lädt seinen Tokenizer aus mdeberta
HF_CACHE = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
TORCH_INDEX = "https://download.pytorch.org/whl/cpu"
EXTRA_PAKETE = ["fastapi", "uvicorn", "pywebview", "python-multipart"]  # stehen auch in requirements.txt

PROJEKT_DATEIEN = ["anonymizer", "server", "ui", "assets", "static", "docs", "ki-anweisung",
                   "lokanon.py", "config.default.yaml", "README.md"]
FILME = ["lokanon-visitenkarte.mp4", "lokanon-motion.mp4", "lokanon-teaser.mp4"]
# Offensichtlich unnötige Teile unterhalb von <app>\python (dist-info bleibt unangetastet)
PRUNE = ["Lib/site-packages/torch/test", "Lib/site-packages/torch/include",
         "Lib/site-packages/torch/lib/*.lib", "Lib/test", "Lib/idlelib", "Lib/tkinter", "tcl",
         "Lib/site-packages/**/__pycache__", "**/*.pdb"]


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def run(cmd: list, **kw) -> None:
    log(" ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def groesse(pfad: Path) -> int:
    return sum(p.stat().st_size for p in pfad.rglob("*") if p.is_file())


def schritt_python(app: Path, dl: Path) -> Path:
    py = app / "python" / "python.exe"
    if py.exists():
        log("Standalone-Python vorhanden, überspringe Download.")
        return py
    archiv = dl / PBS_NAME
    if not archiv.exists():
        log(f"Lade {PBS_URL}")
        urllib.request.urlretrieve(PBS_URL, archiv)
    log(f"Entpacke nach {app}")
    with tarfile.open(archiv) as tf:  # Archiv enthält den Top-Level-Ordner python/
        tf.extractall(app, filter="data")
    if not py.exists():
        sys.exit("python.exe nach dem Entpacken nicht gefunden.")
    return py


def schritt_pakete(py: Path, dl: Path) -> None:
    req = [z.strip() for z in (PROJEKT / "requirements.txt").read_text(encoding="utf-8").splitlines()
           if z.strip() and not z.startswith("#")]
    req = [r for r in req if not r.lower().startswith("streamlit")]  # altes UI, nicht mehr nötig
    pip = [py, "-m", "pip", "install", "--no-warn-script-location", "--disable-pip-version-check"]
    run(pip + ["--upgrade", "pip"])
    run(pip + ["torch", "--index-url", TORCH_INDEX])  # CPU-Build zuerst, damit kein CUDA-Torch kommt
    run(pip + req + EXTRA_PAKETE)
    wheel = dl / SPACY_WHEEL.rsplit("/", 1)[1]
    if not wheel.exists() or wheel.stat().st_size < 10**6:  # pip bekommt von GitHub-Releases 0 Bytes
        log(f"Lade {SPACY_WHEEL}")
        urllib.request.urlretrieve(SPACY_WHEEL, wheel)
    run(pip + [wheel])
    run([py, "-c", "from rapidocr import RapidOCR; RapidOCR(); print('OCR ok')"])  # Modelle liegen im Paket
    log(f"python-Ordner: {groesse(py.parent) / 2**30:.2f} GB")


def _snapshot(py: Path, hf: Path, repo: str) -> None:
    run([py, "-c", f"from huggingface_hub import snapshot_download; snapshot_download({repo!r})"],
        env=dict(os.environ, HF_HOME=str(hf), HF_HUB_OFFLINE="0"))


def schritt_modelle(app: Path, py: Path) -> dict:
    hf = app / "models" / "hf"
    hub = hf / "hub"
    hub.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    for repo in HF_REPOS:
        name = "models--" + repo.replace("/", "--")
        ziel, quelle = hub / name, HF_CACHE / name
        if ziel.exists():
            log(f"{repo} bereits im Bundle.")
        elif quelle.exists():
            log(f"Kopiere {quelle} -> {ziel}")
            shutil.copytree(quelle, ziel, ignore=shutil.ignore_patterns("*.lock"))
            if any(p.is_symlink() for p in ziel.rglob("*")):  # Cache mit Symlinks: sauber neu laden
                shutil.rmtree(ziel)
                _snapshot(py, hf, repo)
        else:
            log(f"{repo} nicht im HF-Cache, lade herunter.")
            _snapshot(py, hf, repo)
        dateien = [p for p in ziel.rglob("*") if p.is_file()]
        manifest[repo] = {"ordner": ziel.relative_to(app).as_posix(), "dateien": len(dateien),
                          "mb": round(sum(p.stat().st_size for p in dateien) / 2**20, 1)}
    ver = subprocess.run([py, "-c", f"import {SPACY_MODEL};print({SPACY_MODEL}.__version__)"],
                         capture_output=True, text=True, check=True).stdout.strip()
    manifest[SPACY_MODEL] = {"ordner": f"python/Lib/site-packages/{SPACY_MODEL}", "version": ver}
    manifest["rapidocr"] = {"ordner": "python/Lib/site-packages/rapidocr/models", "hinweis": "im Paket enthalten"}
    return manifest


def _rmtree_geduldig(pfad: Path, versuche: int = 4) -> None:
    """rmtree für Windows: Ordner aus OneDrive tragen das Schreibschutz-Attribut (RemoveDirectory -> WinError 5),
    und Virenscanner halten frisch gelöschte Ordner kurz offen. Attribut entfernen, bei Bedarf wiederholen."""
    import stat
    import time

    def _freigeben(func, p, exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    for i in range(versuche):
        try:
            shutil.rmtree(pfad, onexc=_freigeben)
            return
        except PermissionError:
            if i == versuche - 1:
                raise
            time.sleep(2 * (i + 1))


def schritt_projekt(app: Path, version: str, manifest: dict) -> None:
    for name in PROJEKT_DATEIEN + [p.name for p in PROJEKT.glob("LICENSE*")]:
        q, z = PROJEKT / name, app / name
        if not q.exists():
            log(f"HINWEIS: {name} fehlt im Projekt, übersprungen (entsteht noch in der Hauptsession).")
            continue
        if z.is_dir():
            _rmtree_geduldig(z)
        elif z.exists():
            z.unlink()
        if q.is_dir():
            shutil.copytree(q, z, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
        else:
            shutil.copy2(q, z)
    # Filme der Produktvorstellung (nicht im Git, entstehen mit Remotion unter video/out)
    filme = app / "docs" / "marketing" / "filme"
    filme.mkdir(parents=True, exist_ok=True)
    for name in FILME:
        q = PROJEKT / "video" / "out" / name
        if q.exists():
            shutil.copy2(q, filme / name)
        else:
            log(f"HINWEIS: Film {name} fehlt unter video/out; Produktvorstellung ohne diesen Film.")
    (app / "VERSION").write_text(version + "\n", encoding="utf-8")
    (app / "models").mkdir(exist_ok=True)
    (app / "models" / "MANIFEST.json").write_text(
        json.dumps({"version": version, "datum": date.today().isoformat(), "python": PBS_PY,
                    "modelle": manifest}, indent=2, ensure_ascii=False), encoding="utf-8")
    (app / "Lokanon.cmd").write_text("\r\n".join([
        "@echo off",
        "rem Lokanon offline starten (alle Modelle liegen im Programmordner)",
        "set \"HF_HOME=%~dp0models\\hf\"",
        "set HF_HUB_OFFLINE=1",
        "set TRANSFORMERS_OFFLINE=1",
        "set TOKENIZERS_PARALLELISM=false",
        "cd /d \"%~dp0\"",
        "start \"\" \"%~dp0python\\pythonw.exe\" \"%~dp0lokanon.py\" %*", ""]), encoding="ascii")
    ico = app / "assets" / "lokanon.ico"
    if not ico.exists():
        ico.parent.mkdir(exist_ok=True)
        shutil.copy2(BUILD_DIR / "lokanon-platzhalter.ico", ico)
        log("HINWEIS: assets/lokanon.ico fehlte, Platzhalter-Icon aus build/ eingesetzt.")


def schritt_pruefen(app: Path) -> None:
    for muster in PRUNE:
        for p in (app / "python").glob(muster):
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
    log(f"Bundle-Größe: {groesse(app) / 2**30:.2f} GB")
    run([sys.executable, BUILD_DIR / "smoke_test.py", app])


def schritt_installer(work: Path, app: Path, version: str) -> Path:
    kandidaten = [shutil.which("ISCC.exe"),
                  Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
                  Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe")]
    iscc = next((Path(k) for k in kandidaten if k and Path(k).exists()), None)
    if not iscc:
        sys.exit("ISCC.exe nicht gefunden: winget install --id JRSoftware.InnoSetup -e")
    out = work / "out"
    out.mkdir(exist_ok=True)
    run([iscc, f"/DAppVersion={version}", f"/DAppDir={app}", f"/DOutDir={out}", BUILD_DIR / "lokanon.iss"])
    exe = out / f"Lokanon-Setup-{version}.exe"
    log(f"Installer: {exe} ({exe.stat().st_size / 2**30:.2f} GB)")
    return exe


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", type=Path, default=WORK_DEFAULT)
    ap.add_argument("--version", default=(BUILD_DIR / "VERSION").read_text(encoding="utf-8").strip()
                    if (BUILD_DIR / "VERSION").exists() else "0.1.0")
    ap.add_argument("--installer", action="store_true", help="danach Inno Setup aufrufen")
    ap.add_argument("--nur-schritt", choices=["python", "pakete", "modelle", "projekt", "pruefen"])
    a = ap.parse_args()
    work, app, dl = a.work, a.work / "app", a.work / "downloads"
    for d in (app, dl):
        d.mkdir(parents=True, exist_ok=True)
    s = a.nur_schritt
    py = schritt_python(app, dl)
    manifest: dict = {}
    if s in (None, "pakete"):
        schritt_pakete(py, dl)
    if s in (None, "modelle", "projekt"):
        manifest = schritt_modelle(app, py)
    if s in (None, "projekt"):
        schritt_projekt(app, a.version, manifest)
    if s in (None, "pruefen"):
        schritt_pruefen(app)
    if a.installer:
        schritt_installer(work, app, a.version)
    log("fertig.")


if __name__ == "__main__":
    main()
