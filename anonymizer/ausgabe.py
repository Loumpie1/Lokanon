"""Ausgabe im gleichen Format: aus `Klage.docx` wird `Klage_anonymisiert.docx`, aus `Scan.pdf` eine geschwärzte
`Scan_anonymisiert.pdf`, aus `Liste.xlsx` eine bereinigte `Liste_anonymisiert.xlsx`, aus Text wird Text."""
from __future__ import annotations

import re
from pathlib import Path

from . import files as fio

TEXT_TYPEN = {"txt", "md"}


def dateiname_anonym(original: str, suffix: str = "_anonymisiert") -> str:
    p = Path(original)
    return f"{p.stem}{suffix}{p.suffix}"


def erzeuge(name: str, data: bytes | None, anonym_text: str, pairs: list[tuple[str, str]]) -> bytes:
    """Anonymisierte Fassung im Format der Originaldatei. Wirft ValueError, wenn die Gegenprüfung (PDF) scheitert
    oder das Format nicht geschrieben werden kann."""
    ext = name.lower().rsplit(".", 1)[-1] if "." in name else "txt"
    if ext in TEXT_TYPEN or data is None:
        return anonym_text.encode("utf-8")
    if ext == "csv":
        raw = data.decode("utf-8", errors="replace")
        return fio._replace_all(raw, pairs).encode("utf-8")
    if ext == "docx":
        return fio.write_docx(data, pairs)
    if ext == "xlsx":
        return fio.write_xlsx(data, pairs)
    if ext == "pdf":
        return fio.write_pdf(data, pairs)
    raise ValueError(f"Dateityp .{ext} kann nicht geschrieben werden.")


def leck_test(anonym_text: str, originale: list[str]) -> list[str]:
    """Originalbegriffe (ab 3 Zeichen), die im anonymisierten Text noch als ganzes Wort vorkommen."""
    rest = []
    for o in originale:
        if len(o) >= 3 and re.search(rf"(?<!\w){re.escape(o)}(?!\w)", anonym_text, flags=re.IGNORECASE):
            rest.append(o)
    return sorted(set(rest))
