"""Contract section coverage vs normalized PDF stream (content remainder).

Masks every resolved ``passage-sections.json`` span on the shared extract stream
and reports leftover intervals. Pages listed in ``content_remainder.ignore_pages``
(e.g. index / reference sheet) are excluded from gap math and the coverage
denominator. No Neo4j — this is contract→PDF hygiene, not table/KG completeness
(see ``check_coverage`` / ``section_gates``).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.document_extract import DocumentExtract, ResolvedSection, load_document_extract
from src.section_chunking import _page_span_offsets, page_range_for_span


@dataclass
class RemainderGap:
    start: int
    end: int
    chars: int
    page_start: int | None
    page_end: int | None
    preview: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RemainderReport:
    game: str
    document: str
    phase: int | None
    stream_chars: int
    eligible_chars: int
    ignored_chars: int
    ignore_pages: list[int]
    covered_chars: int
    sections_matched: int
    gaps: list[RemainderGap] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    min_chars: int = 40
    ok: bool = True

    @property
    def covered_ratio(self) -> float:
        if self.eligible_chars <= 0:
            return 1.0
        return self.covered_chars / self.eligible_chars

    def to_dict(self) -> dict[str, Any]:
        return {
            "game": self.game,
            "document": self.document,
            "phase": self.phase,
            "stream_chars": self.stream_chars,
            "eligible_chars": self.eligible_chars,
            "ignored_chars": self.ignored_chars,
            "ignore_pages": list(self.ignore_pages),
            "covered_chars": self.covered_chars,
            "covered_ratio": round(self.covered_ratio, 4),
            "sections_matched": self.sections_matched,
            "gap_count": len(self.gaps),
            "gaps": [g.to_dict() for g in self.gaps],
            "warnings": list(self.warnings),
            "min_chars": self.min_chars,
            "ok": self.ok,
        }


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge half-open [start, end) intervals; drop empty / inverted."""
    cleaned = sorted((s, e) for s, e in intervals if e > s)
    if not cleaned:
        return []
    merged: list[tuple[int, int]] = [cleaned[0]]
    for start, end in cleaned[1:]:
        last_s, last_e = merged[-1]
        if start <= last_e:
            merged[-1] = (last_s, max(last_e, end))
        else:
            merged.append((start, end))
    return merged


def covered_intervals_from_sections(
    sections: list[ResolvedSection],
) -> list[tuple[int, int]]:
    """Same cover as pdf-as-md document mode: heading through content_end."""
    return merge_intervals(
        [(item.heading_start, item.content_end) for item in sections]
    )


def ignore_page_intervals(
    page_spans: list[dict[str, int]],
    ignore_pages: list[int],
) -> list[tuple[int, int]]:
    """Whole-page [start, end) intervals for pages to exclude from remainder."""
    intervals: list[tuple[int, int]] = []
    for page in ignore_pages:
        try:
            page_n = int(page)
        except (TypeError, ValueError):
            continue
        offs = _page_span_offsets(page_spans, page_n, page_n)
        if offs is not None:
            intervals.append(offs)
    return merge_intervals(intervals)


def gaps_in_stream(
    stream_len: int,
    covered: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Return uncovered [start, end) intervals inside ``[0, stream_len)``."""
    if stream_len <= 0:
        return []
    gaps: list[tuple[int, int]] = []
    cursor = 0
    for start, end in covered:
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < stream_len:
        gaps.append((cursor, stream_len))
    return gaps


def interval_length(intervals: list[tuple[int, int]]) -> int:
    return sum(e - s for s, e in intervals)


def subtract_intervals(
    base: list[tuple[int, int]],
    cut: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Return ``base`` intervals with ``cut`` removed (half-open)."""
    if not base:
        return []
    if not cut:
        return list(base)
    cut_m = merge_intervals(cut)
    out: list[tuple[int, int]] = []
    for b_start, b_end in merge_intervals(base):
        pieces = [(b_start, b_end)]
        for c_start, c_end in cut_m:
            next_pieces: list[tuple[int, int]] = []
            for p_start, p_end in pieces:
                if c_end <= p_start or c_start >= p_end:
                    next_pieces.append((p_start, p_end))
                    continue
                if p_start < c_start:
                    next_pieces.append((p_start, c_start))
                if c_end < p_end:
                    next_pieces.append((c_end, p_end))
            pieces = next_pieces
        out.extend(pieces)
    return merge_intervals(out)


def _preview(text: str, *, limit: int = 160) -> str:
    one_line = " ".join(text.split())
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 1] + "..."


def _ignore_pages_from_contract(contract: dict[str, Any]) -> list[int]:
    cfg = contract.get("content_remainder") or {}
    raw = cfg.get("ignore_pages") or []
    pages: list[int] = []
    for item in raw:
        try:
            pages.append(int(item))
        except (TypeError, ValueError):
            continue
    return sorted(set(pages))


def build_remainder_report(
    extract: DocumentExtract,
    *,
    phase: int | None,
    min_chars: int = 40,
    preview_limit: int = 160,
) -> RemainderReport:
    ignore_pages = _ignore_pages_from_contract(extract.contract)
    ignored = ignore_page_intervals(extract.page_spans, ignore_pages)
    section_cover = covered_intervals_from_sections(extract.sections)
    # Gap math: sections + ignored pages count as claimed.
    covered_for_gaps = merge_intervals([*section_cover, *ignored])
    raw_gaps = gaps_in_stream(len(extract.stream), covered_for_gaps)

    # Coverage ratio excludes ignore pages from both sides.
    eligible_cover = subtract_intervals(section_cover, ignored)
    ignored_chars = interval_length(ignored)
    eligible_chars = max(0, len(extract.stream) - ignored_chars)
    covered_chars = interval_length(eligible_cover)

    gaps: list[RemainderGap] = []
    for start, end in raw_gaps:
        text = extract.stream[start:end]
        stripped = text.strip()
        if len(stripped) < min_chars:
            continue
        page_start, page_end = page_range_for_span(
            extract.page_spans, start, end
        )
        gaps.append(
            RemainderGap(
                start=start,
                end=end,
                chars=len(stripped),
                page_start=page_start,
                page_end=page_end,
                preview=_preview(stripped, limit=preview_limit),
            )
        )

    return RemainderReport(
        game=extract.game,
        document=extract.file_name,
        phase=phase,
        stream_chars=len(extract.stream),
        eligible_chars=eligible_chars,
        ignored_chars=ignored_chars,
        ignore_pages=ignore_pages,
        covered_chars=covered_chars,
        sections_matched=len(extract.sections),
        gaps=gaps,
        warnings=list(extract.warnings),
        min_chars=min_chars,
        ok=len(gaps) == 0,
    )


def run_content_remainder(
    *,
    game: str = "mork-borg",
    document: str = "mork-borg.pdf",
    phase: int | None = None,
    pdf_path: str | None = None,
    min_chars: int = 40,
) -> RemainderReport:
    extract = load_document_extract(
        document,
        game=game,
        pdf_path=pdf_path,
        phase=phase,
    )
    return build_remainder_report(
        extract, phase=phase, min_chars=min_chars
    )


def format_report_text(report: RemainderReport, *, verbose: bool = False) -> str:
    phase_label = "all" if report.phase is None else str(report.phase)
    ignore_label = (
        ",".join(str(p) for p in report.ignore_pages)
        if report.ignore_pages
        else "none"
    )
    lines = [
        f"Content remainder — {report.document} (phase {phase_label})",
        f"Stream: {report.stream_chars} chars | "
        f"ignored pages [{ignore_label}]: {report.ignored_chars} | "
        f"eligible: {report.eligible_chars} | "
        f"covered: {report.covered_chars} "
        f"({100.0 * report.covered_ratio:.1f}%) | "
        f"sections: {report.sections_matched} | "
        f"gaps (>={report.min_chars} chars): {len(report.gaps)}",
        "",
    ]
    if report.gaps:
        for i, gap in enumerate(report.gaps, start=1):
            if gap.page_start is None:
                pages = "?"
            elif gap.page_start == gap.page_end:
                pages = f"p.{gap.page_start}"
            else:
                pages = f"p.{gap.page_start}-{gap.page_end}"
            lines.append(f"GAP {i}  {pages}  {gap.chars} chars")
            lines.append(f"  {gap.preview!r}")
            if verbose:
                lines.append(f"  offsets [{gap.start}, {gap.end})")
            lines.append("")
    else:
        lines.append("No unclassified remainder above threshold.")
        lines.append("")

    if report.warnings:
        lines.append(f"Warnings ({len(report.warnings)}):")
        show = report.warnings if verbose else report.warnings[:10]
        for w in show:
            lines.append(f"  - {w}")
        if not verbose and len(report.warnings) > 10:
            lines.append(f"  ... {len(report.warnings) - 10} more (use --verbose)")
        lines.append("")

    lines.append("PASS" if report.ok else "FAIL")
    return "\n".join(lines)
