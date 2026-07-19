#!/usr/bin/env python3
"""Dump PDF index page (default p.75) for passage-sections authoring."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fitz import open as fitz_open
from src.table_pipeline import resolve_pdf_path

PAGE = 75


def main() -> None:
    pdf = resolve_pdf_path("mork-borg.pdf")
    doc = fitz_open(pdf)
    page = doc[PAGE - 1]
    print(f"=== plain text page {PAGE} ===")
    print(page.get_text())
    print(f"=== dict spans page {PAGE} (font size | text) ===")
    d = page.get_text("dict")
    for block in d.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            parts = []
            for sp in line.get("spans", []):
                t = sp.get("text", "").strip()
                if t:
                    parts.append(f"[{sp.get('size', 0):.1f}] {t!r}")
            if parts:
                print(" | ".join(parts))
    doc.close()


if __name__ == "__main__":
    main()
