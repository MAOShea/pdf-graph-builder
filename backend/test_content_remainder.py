"""Unit tests for contract→stream content remainder (no PDF / Neo4j)."""

from __future__ import annotations

from pathlib import Path

from src.content_remainder import (
    RemainderGap,
    RemainderReport,
    build_remainder_report,
    covered_intervals_from_sections,
    gaps_in_stream,
    ignore_page_intervals,
    merge_intervals,
    subtract_intervals,
)
from src.document_extract import DocumentExtract, ResolvedSection


def _section(
    *,
    sid: str,
    heading_start: int,
    content_end: int,
    content_start: int | None = None,
) -> ResolvedSection:
    return ResolvedSection(
        section={"id": sid},
        heading_start=heading_start,
        content_start=content_start if content_start is not None else heading_start,
        content_end=content_end,
        page_start=1,
        page_end=1,
        end_at_eof=False,
        matched_heading=sid,
    )


def test_merge_intervals_overlaps_and_empty():
    assert merge_intervals([]) == []
    assert merge_intervals([(5, 5), (3, 1)]) == []
    assert merge_intervals([(0, 10), (8, 15), (20, 25)]) == [(0, 15), (20, 25)]
    assert merge_intervals([(10, 20), (0, 5)]) == [(0, 5), (10, 20)]


def test_gaps_in_stream_edges():
    assert gaps_in_stream(0, []) == []
    assert gaps_in_stream(100, []) == [(0, 100)]
    assert gaps_in_stream(100, [(0, 100)]) == []
    assert gaps_in_stream(100, [(10, 40), (60, 90)]) == [
        (0, 10),
        (40, 60),
        (90, 100),
    ]


def test_subtract_intervals():
    assert subtract_intervals([(0, 100)], [(40, 60)]) == [(0, 40), (60, 100)]
    assert subtract_intervals([(0, 50)], [(0, 50)]) == []
    assert subtract_intervals([(10, 20)], [(0, 5)]) == [(10, 20)]


def test_ignore_page_intervals():
    spans = [
        {"page_number": 1, "start": 0, "end": 10},
        {"page_number": 2, "start": 11, "end": 20},
        {"page_number": 3, "start": 21, "end": 30},
    ]
    assert ignore_page_intervals(spans, [2, 3]) == [(11, 20), (21, 30)]
    # Adjacent pages with no inter-page hole merge:
    tight = [
        {"page_number": 2, "start": 11, "end": 20},
        {"page_number": 3, "start": 20, "end": 30},
    ]
    assert ignore_page_intervals(tight, [2, 3]) == [(11, 30)]


def test_covered_from_sections_uses_heading_to_content_end():
    sections = [
        _section(sid="a", heading_start=10, content_start=15, content_end=50),
        _section(sid="b", heading_start=45, content_end=80),
    ]
    assert covered_intervals_from_sections(sections) == [(10, 80)]


def test_build_remainder_report_filters_tiny_gaps():
    mid = "Y" * 50
    stream = "AAAA" + mid + "BBBB" + " x " + "CCCC"
    extract = DocumentExtract(
        file_name="toy.pdf",
        pdf_path=Path(__file__),
        game="mork-borg",
        contract={},
        stream=stream,
        page_spans=[{"page_number": 1, "start": 0, "end": len(stream)}],
        sections=[
            _section(sid="front", heading_start=0, content_end=4),
            _section(sid="mid", heading_start=54, content_end=58),
            _section(sid="end", heading_start=61, content_end=65),
        ],
        warnings=["anchor miss toy"],
    )
    report = build_remainder_report(extract, phase=None, min_chars=40)
    assert len(report.gaps) == 1
    assert report.gaps[0].chars == 50
    assert report.gaps[0].preview == mid
    assert report.ok is False
    assert report.warnings == ["anchor miss toy"]

    quiet = build_remainder_report(extract, phase=None, min_chars=60)
    assert quiet.ok is True
    assert quiet.gaps == []


def test_ignore_pages_excluded_from_gaps_and_denominator():
    # page1 [0,20) uncovered noise; page2 [20,40) section; page3 [40,60) ignore
    stream = ("N" * 20) + ("S" * 20) + ("I" * 20)
    extract = DocumentExtract(
        file_name="toy.pdf",
        pdf_path=Path(__file__),
        game="mork-borg",
        contract={"content_remainder": {"ignore_pages": [3]}},
        stream=stream,
        page_spans=[
            {"page_number": 1, "start": 0, "end": 20},
            {"page_number": 2, "start": 20, "end": 40},
            {"page_number": 3, "start": 40, "end": 60},
        ],
        sections=[_section(sid="mid", heading_start=20, content_end=40)],
    )
    report = build_remainder_report(extract, phase=None, min_chars=10)
    assert report.ignore_pages == [3]
    assert report.ignored_chars == 20
    assert report.eligible_chars == 40
    assert report.covered_chars == 20
    assert len(report.gaps) == 1
    assert report.gaps[0].page_start == 1
    assert report.ok is False

    # Cover page 1 too → PASS; ignore page still out of denominator
    extract.sections = [
        _section(sid="a", heading_start=0, content_end=20),
        _section(sid="b", heading_start=20, content_end=40),
    ]
    ok = build_remainder_report(extract, phase=None, min_chars=10)
    assert ok.ok is True
    assert ok.gaps == []
    assert ok.eligible_chars == 40
    assert ok.covered_chars == 40
    assert abs(ok.covered_ratio - 1.0) < 1e-9


def test_format_and_to_dict_smoke():
    report = RemainderReport(
        game="mork-borg",
        document="toy.pdf",
        phase=3,
        stream_chars=100,
        eligible_chars=90,
        ignored_chars=10,
        ignore_pages=[75],
        covered_chars=90,
        sections_matched=2,
        gaps=[
            RemainderGap(
                start=10,
                end=20,
                chars=8,
                page_start=2,
                page_end=2,
                preview="leftover",
            )
        ],
        min_chars=40,
        ok=False,
    )
    d = report.to_dict()
    assert d["gap_count"] == 1
    assert d["covered_ratio"] == 1.0
    assert d["ignore_pages"] == [75]
    assert d["ok"] is False
