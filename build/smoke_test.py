"""Rauchtest im Bundle (offline):  python build\\smoke_test.py <work>\\app   -> Exit 0 = bestanden."""
import os
import subprocess
import sys
from pathlib import Path

app = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "Lokanon" / "build" / "app").resolve()
py = app / "python" / "python.exe"
env = dict(os.environ, HF_HOME=str(app / "models" / "hf"), HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
           TOKENIZERS_PARALLELISM="false", PYTHONNOUSERSITE="1")
env.pop("PYTHONPATH", None)
code = (
    "import anonymizer.engine, anonymizer.ocr\n"
    "from anonymizer.engine import build_analyzer\n"
    "a = build_analyzer('de_core_news_lg', 'urchade/gliner_multi_pii-v1')\n"
    "r = a.analyze(text='Herr Max Mustermann wohnt in Berlin, IBAN DE89370400440532013000.', language='de')\n"
    "print('Treffer:', sorted({x.entity_type for x in r}))\n"
    "import fastapi, uvicorn, webview\n"
    "print('UI-Pakete ok')\n"
)
r = subprocess.run([str(py), "-c", code], cwd=app, env=env)
print("RAUCHTEST", "BESTANDEN" if r.returncode == 0 else "FEHLGESCHLAGEN")
sys.exit(r.returncode)
