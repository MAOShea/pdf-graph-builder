#!/usr/bin/env python3
"""Validate all passage-section anchors against the PDF text stream."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.ingest_manifest import load_passage_sections
from src.section_chunking import (
    build_page_indexed_stream,
    normalize_stream_text,
    resolve_section_span,
)
from src.table_pipeline import load_pdf_text_by_page, resolve_pdf_path


def main() -> int:
    contract = load_passage_sections("mork-borg")
    anchor_matching = contract.get("anchor_matching") or {}
    by_page = load_pdf_text_by_page(resolve_pdf_path("mork-borg.pdf"))
    stream, spans = build_page_indexed_stream(by_page)
    stream = normalize_stream_text(
        stream, normalize_whitespace=anchor_matching.get("normalize_whitespace", True)
    )

    failed = 0
    for section in contract.get("sections") or []:
        sid = section.get("id")
        span = resolve_section_span(stream, section, anchor_matching=anchor_matching)
        if span is None:
            print(f"FAIL  {sid}: start anchor not found (hint p.{section.get('operator_page_hint')})")
            failed += 1
            continue
        start, end = span
        text = stream[start:end].strip()
        chars = len(text)
        from src.section_chunking import page_range_for_span

        p0, p1 = page_range_for_span(spans, start, end)
        print(f"OK    {sid}: p.{p0}-{p1} chars={chars} title={section.get('title')!r}")
        if chars < 20:
            print(f"      WARN short section ({chars} chars)")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
