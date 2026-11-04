"""Qualitätsuntergrenzen je Dokumentfamilie auf der Testsammlung testdaten/korpus (ohne GLiNER, nur spaCy + Regeln).

Die Werte werden nach jeder Verbesserung angehoben, damit nichts unbemerkt zurückfällt. Messung mit beiden Modellen:
python evaluate.py --config testdaten/kanzlei/config_eval.yaml testdaten/korpus/referenz.jsonl
"""
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluate import analyzer_fuer, auswerten, lade_faelle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# Familie: (Recall, Precision) – Basislinie 04.11.2026 (spaCy): 96/84, 75/88, 81/100, 78/93, 91/88
# Nach Tabellenaufbau, Feldern, Wörterbuch und OCR ohne Zeilen-Drehklassifikation: 100/96, 96/98, 98/100, 92/98, 93/100
MINDESTWERTE = {
    "arzt_gutachten": (0.98, 0.94),
    "bescheid_formular": (0.94, 0.96),
    "lohn_konto_rechnung": (0.96, 0.98),
    "scans": (0.90, 0.96),
    "schriftsatz": (0.91, 0.98),
}


@pytest.fixture(scope="module")
def ergebnis():
    cfg = yaml.safe_load((ROOT / "testdaten/kanzlei/config_eval.yaml").read_text(encoding="utf-8"))
    return auswerten(analyzer_fuer(cfg, ohne_gliner=True), cfg, lade_faelle([ROOT / "testdaten/korpus/referenz.jsonl"]))


@pytest.mark.parametrize("familie", sorted(MINDESTWERTE))
def test_korpus_mindestwerte(ergebnis, familie):
    z = ergebnis["familien"][familie]
    recall, precision = MINDESTWERTE[familie]
    assert z["recall"] >= recall, f"{familie}: Recall {z['recall']:.0%} < {recall:.0%}"
    assert z["precision"] >= precision, f"{familie}: Precision {z['precision']:.0%} < {precision:.0%}"
