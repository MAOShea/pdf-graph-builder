#!/usr/bin/env python3
"""Report PDF stream leftover after masking contract section spans.

Usage (from repo root):
  backend\\venv\\Scripts\\python.exe backend\\check_content_remainder.py
  backend\\venv\\Scripts\\python.exe backend\\check_content_remainder.py --verbose
  backend\\venv\\Scripts\\python.exe backend\\check_content_remainder.py --json
  backend\\venv\\Scripts\\python.exe backend\\check_content_remainder.py --phase 3

No Neo4j. Same PDF load path as pdf-as-md / section materialization.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from src.content_remainder import format_report_text, run_content_remainder


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Contract section coverage vs PDF stream (content remainder)"
    )
    parser.add_argument("--game", default="mork-borg")
    parser.add_argument("--document", default="mork-borg.pdf")
    parser.add_argument(
        "--pdf-path",
        default=None,
        help="Override PDF path (default: resolve from document name)",
    )
    parser.add_argument(
        "--phase",
        type=int,
        default=None,
        help="Max passage-sections.json phase (inclusive). Default: all sections.",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=40,
        help="Ignore gaps whose stripped text is shorter than this (default 40).",
    )
    parser.add_argument("--verbose", action="store_true", help="Offsets + all warnings")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON output")
    args = parser.parse_args()

    report = run_content_remainder(
        game=args.game,
        document=args.document,
        phase=args.phase,
        pdf_path=args.pdf_path,
        min_chars=args.min_chars,
    )

    if args.as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report_text(report, verbose=args.verbose))

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
