#!/usr/bin/env python3
"""Verify rulebook heading lines on pages from the p.75 index."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fitz import open as fitz_open
from src.table_pipeline import load_pdf_text_by_page, resolve_pdf_path

# RULES entries from index page 75 (page, title)
RULES_INDEX = [
    (27, "Abilities"),
    (43, "Arcane catastrophes"),
    (23, "Armor"),
    (30, "Attack"),
    (40, "Bad habit"),
    (29, "Broken (0 HP)"),
    (39, "Broken bodies"),
    (17, "Calendar of Nechrubel"),
    (28, "Carrying capacity"),
    (30, "Combat"),
    (21, "Create a character"),
    (31, "Crit"),
    (30, "Defence"),
    (24, "Equipment"),
    (50, "Esoteric hermit"),
    (46, "Fanged deserter"),
    (31, "Fumble"),
    (33, "Getting better (or worse)"),
    (48, "Gutterborn scum"),
    (54, "Heretical priest"),
    (63, "Hirelings"),
    (29, "Hit Points"),
    (31, "Infection"),
    (30, "Initiative"),
    (30, "Melee attack"),
    (32, "Morale"),
    (56, "Occult herbmaster"),
    (37, "Omens"),
    (63, "Outcasts"),
    (34, "Powers"),
    (30, "Ranged attack"),
    (32, "Reaction"),
    (31, "Resting"),
    (34, "Scrolls"),
    (21, "Starting equipment"),
    (38, "Terrible traits"),
    (28, "Tests"),
    (41, "Troubling tales"),
    (30, "Violence"),
    (23, "Weapons"),
    (52, "Wretched royalty"),
]


def heading_lines(page_text: str, min_size: float | None = None) -> list[str]:
    """First non-header lines that look like section titles."""
    lines = []
    for raw in page_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.match(r"^M.?RK BORG", line, re.I):
            continue
        if re.match(r"^\d{1,3}$", line):
            continue
        lines.append(line)
    return lines[:8]


def main() -> None:
    pdf = resolve_pdf_path("mork-borg.pdf")
    by_page = load_pdf_text_by_page(pdf)

    # Group by page for probe
    pages_to_check = sorted({p for p, _ in RULES_INDEX if p <= 45})
    print("=== heading lines on key pages ===")
    for pn in pages_to_check:
        text = by_page.get(pn, "")
        lines = heading_lines(text)
        print(f"\n--- p.{pn} ---")
        for ln in lines:
            print(f"  {ln!r}")

    print("\n=== index title vs page first lines ===")
    for page, title in sorted(RULES_INDEX, key=lambda x: (x[0], x[1])):
        if page > 45:
            continue
        text = by_page.get(page, "")
        lines = heading_lines(text)
        hit = any(title.lower() in ln.lower() or ln.lower() in title.lower() for ln in lines)
        print(f"p.{page:2d} index={title!r:30s} lines={lines[:3]!r} match={hit}")


if __name__ == "__main__":
    main()
