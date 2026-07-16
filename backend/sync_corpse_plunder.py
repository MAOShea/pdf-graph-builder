"""Sync games/mork-borg/hand-authored-overrides/corpse-plunder.txt -> corpse-plunder-d66.json.

Each data line uses two or more spaces between the d66 roll and the result text.
Only the first such run is treated as the column divider; double spaces inside the
result column are preserved.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROLL_RANGE = re.compile(r"^\d{1,2}[\-–]\d{1,2}$")
ROLL_SINGLE = re.compile(r"^\d{2}$")


def parse_row(line: str) -> tuple[str | int, str]:
    line = line.strip()
    if not line:
        raise ValueError("empty line")
    parts = re.split(r"\s{2,}", line, maxsplit=1)
    if len(parts) != 2:
        raise ValueError(
            f"expected 'roll  result' with two or more spaces as divider: {line!r}"
        )
    roll_raw, result = parts[0].strip(), parts[1].strip()
    roll_key = roll_raw.replace("\u2013", "-")
    if ROLL_RANGE.match(roll_key):
        return roll_key, result
    if ROLL_SINGLE.match(roll_key):
        return int(roll_key), result
    raise ValueError(f"unrecognized d66 roll: {roll_raw!r}")


def sync(txt_path: Path, json_path: Path) -> int:
    lines = txt_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError(f"empty file: {txt_path}")

    rows: list[list] = []
    for i, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        roll, result = parse_row(line)
        rows.append([roll, result])

    doc = {
        "_note": (
            "Generated from games/mork-borg/hand-authored-overrides/corpse-plunder.txt. "
            "Lines use two or more spaces between d66 roll and result. "
            "Run: .\\sync-corpse-plunder.ps1 then .\\ingest-hand-table.ps1"
        ),
        "source": "mork-borg",
        "manifest_table": "CorpsePlunderTable",
        "override_pdf": True,
        "section_id": "corpse-plunder-d66",
        "title": "Corpse plundering (d66)",
        "blocks": [
            {
                "type": "table",
                "title": "Corpse plundering",
                "columns": ["d66", "result"],
                "rows": rows,
            }
        ],
    }
    json_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(rows)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--txt",
        type=Path,
        default=root / "games/mork-borg/hand-authored-overrides/corpse-plunder.txt",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=root / "games/mork-borg/hand-authored-overrides/corpse-plunder-d66.json",
    )
    args = parser.parse_args()
    count = sync(args.txt, args.json)
    print(f"sync_corpse_plunder: {count} rows -> {args.json}")


if __name__ == "__main__":
    main()
