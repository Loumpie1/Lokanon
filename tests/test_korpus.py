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

# Familie: (Recall, Precision) – Stand Basislinie 04.11.2026 (spaCy): 96/84, 75/88, 81/100, 78/93, 91/88
MINDESTWERTE = {
    "arzt_gutachten": (0.94, 0.82),
    "bescheid_formular": (0.73, 0.86),
    "lohn_konto_rechnung": (0.79, 0.97),
    "scans": (0.76, 0.90),
    "schriftsatz": (0.89, 0.86),
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
