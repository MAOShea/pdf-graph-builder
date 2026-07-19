#!/usr/bin/env python3
"""Parse the three-column index on PDF page 75 (THE WORLD | CREATURES | RULES)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fitz import open as fitz_open
from src.table_pipeline import resolve_pdf_path

PAGE = 75
COLUMN_HEADERS = ("THE WORLD", "CREATURES", "RULES")


def _parse_index_lines(text: str) -> dict[str, list[dict[str, int | str]]]:
    """Split index page text into three column entry lists."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # Drop running header/footer
    cleaned: list[str] = []
    for ln in lines:
        if re.match(r"^M.?RK BORG", ln, re.I):
            continue
        if re.match(r"^Index$", ln, re.I):
            continue
        if re.match(r"^\d{1,3}$", ln) and cleaned and cleaned[-1] in COLUMN_HEADERS:
            continue
        cleaned.append(ln)

    columns: dict[str, list[dict]] = {h: [] for h in COLUMN_HEADERS}
    current: str | None = None
    entry_re = re.compile(r"^(\d{1,3})\s+(.+)$")

    for ln in cleaned:
        if ln in COLUMN_HEADERS:
            current = ln
            continue
        if current is None:
            continue
        m = entry_re.match(ln)
        if m:
            columns[current].append(
                {"page": int(m.group(1)), "title": m.group(2).strip()}
            )

    return columns


def main() -> None:
    pdf = resolve_pdf_path("mork-borg.pdf")
    doc = fitz_open(pdf)
    text = doc[PAGE - 1].get_text()
    doc.close()
    columns = _parse_index_lines(text)
    for header in COLUMN_HEADERS:
        print(f"=== {header} ({len(columns[header])} entries) ===")
        for entry in columns[header]:
            print(f"  p.{entry['page']:2d}  {entry['title']}")
    print("\n=== JSON snippet ===")
    print(
        json.dumps(
            {"page": PAGE, "columns": columns},
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
