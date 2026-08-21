"""Shared PDF document extract model (ingest + validation sinks).

Owns the parse/resolve path that ``tools/pdf-as-md`` and Neo4j materializers share:
normalized PDF stream, contract section spans, and lookup-table hits
(PDF ``extract_lookup_table`` — sequential stream, ``aligned_columns``, or
``split_italic`` — or manifest ``hand_authored.file`` substitution).

Sinks only choose where to write (Neo4j vs Markdown) — not how to parse.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.hand_authored_tables import load_hand_authored_table, skip_pdf_extract
from src.ingest_manifest import _project_root, load_ingest_manifest, load_passage_sections
from src.pdf_table_parser import (
    _find_header,
    _slice_body,
    extract_lookup_table,
    table_display_title,
)
from src.section_chunking import (
    _anchor_pattern,
    _regex_flags,
    build_page_indexed_stream,
    normalize_stream_text,
    page_range_for_span,
    resolve_section_span,
)
from src.table_pipeline import load_pdf_text_by_page, resolve_pdf_path

logger = logging.getLogger(__name__)


@dataclass
class ResolvedSection:
    section: dict[str, Any]
    heading_start: int
    content_start: int
    content_end: int
    page_start: int | None
    page_end: int | None
    end_at_eof: bool
    matched_heading: str


@dataclass
class TableHit:
    start: int
    end: int
    table: dict[str, Any]
    manifest_name: str
    source: str  # "pdf" | "hand_authored"
    note: str = ""


@dataclass
class DocumentExtract:
    """Normalized PDF stream + contract sections + warnings (no sink)."""

    file_name: str
    pdf_path: Path
    game: str
    contract: dict[str, Any]
    stream: str
    page_spans: list[dict[str, int]]
    sections: list[ResolvedSection] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def filter_sections_by_phase(
    all_sections: list[dict[str, Any]], phase: int | None
) -> list[dict[str, Any]]:
    if phase is None:
        return list(all_sections)
    return [s for s in all_sections if (s.get("phase") or 99) <= phase]


def load_document_extract(
    file_name: str,
    *,
    game: str = "mork-borg",
    pdf_path: str | None = None,
    phase: int | None = None,
) -> DocumentExtract:
    """
    Same text load as ``materialize_passage_sections``:

    resolve_pdf_path → load_pdf_text_by_page → build_page_indexed_stream
    → normalize_stream_text → resolve_section_span per contract section.
    """
    contract = load_passage_sections(game)
    anchor_matching = contract.get("anchor_matching") or {}
    normalize_ws = anchor_matching.get("normalize_whitespace", True)

    resolved = resolve_pdf_path(file_name, pdf_path=pdf_path)
    from src.section_chunking import filter_page_texts

    page_texts = filter_page_texts(
        load_pdf_text_by_page(resolved),
        contract.get("text_filters"),
        normalize_whitespace=normalize_ws,
    )
    stream, page_spans = build_page_indexed_stream(page_texts)

    sections_in = filter_sections_by_phase(contract.get("sections") or [], phase)
    matched, warnings = resolve_contract_sections(
        stream, page_spans, sections_in, anchor_matching
    )
    return DocumentExtract(
        file_name=file_name,
        pdf_path=resolved,
        game=game,
        contract=contract,
        stream=stream,
        page_spans=page_spans,
        sections=matched,
        warnings=warnings,
    )


def resolve_contract_sections(
    stream: str,
    page_spans: list[dict[str, int]],
    sections: list[dict[str, Any]],
    anchor_matching: dict[str, Any],
) -> tuple[list[ResolvedSection], list[str]]:
    matched: list[ResolvedSection] = []
    warnings: list[str] = []
    flags = _regex_flags(anchor_matching)
    for section in sections:
        section_id = section.get("id", "?")
        span = resolve_section_span(
            stream,
            section,
            anchor_matching=anchor_matching,
            page_spans=page_spans,
        )
        if span is None:
            hint = section.get("operator_page_hint", "?")
            warnings.append(
                f"start anchor not found for section {section_id!r} "
                f"(operator_page_hint={hint})"
            )
            continue
        content_start, content_end = span
        start_anchor = section.get("start_anchor") or {}
        if start_anchor.get("type") == "page_range":
            heading_start = content_start
            sp = start_anchor.get("start_page")
            ep = start_anchor.get("end_page", sp)
            matched_heading = f"pages {sp}-{ep}" if sp != ep else f"page {sp}"
            end_at_eof = False
        else:
            start_m = re.search(
                _anchor_pattern(start_anchor), stream, flags=flags
            )
            if start_m is None:
                warnings.append(f"start anchor vanished for section {section_id!r}")
                continue
            heading_start = start_m.start()
            matched_heading = start_m.group(0).strip()
            end_at_eof = content_end >= len(stream)
            if end_at_eof:
                hint = section.get("operator_page_hint", "?")
                warnings.append(
                    f"end anchor not found for section {section_id!r} "
                    f"(extended to EOF; operator_page_hint={hint})"
                )
        page_start, page_end = page_range_for_span(page_spans, heading_start, content_end)
        matched.append(
            ResolvedSection(
                section=section,
                heading_start=heading_start,
                content_start=content_start,
                content_end=content_end,
                page_start=page_start,
                page_end=page_end,
                end_at_eof=end_at_eof,
                matched_heading=matched_heading,
            )
        )
    matched.sort(key=lambda r: r.heading_start)
    return matched, warnings


def resolve_content_source_path(
    game: str, content_source: dict[str, Any]
) -> Path | None:
    rel = str(content_source.get("file") or "").strip()
    if not rel:
        return None
    path = Path(rel)
    if path.is_absolute() and path.is_file():
        return path
    candidate = _project_root() / "games" / game / rel
    if candidate.is_file():
        return candidate.resolve()
    candidate = _project_root() / rel
    if candidate.is_file():
        return candidate.resolve()
    return None


def load_content_source_payload(
    game: str, content_source: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    """Load hand-authored JSON for a section ``content_source``. Returns (data, error)."""
    path = resolve_content_source_path(game, content_source)
    if path is None:
        return None, f"content_source file not found: {content_source.get('file')!r}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"failed to load {path}: {exc}"
    if not isinstance(data, dict):
        return None, f"content_source root must be object: {path}"
    data["_resolved_path"] = str(path)
    return data, None


def content_source_plain_text(game: str, content_source: dict[str, Any]) -> str | None:
    """Plain text suitable for a section Chunk when skipping PDF (ingest path)."""
    data, err = load_content_source_payload(game, content_source)
    if err or not data:
        logger.warning("content_source: %s", err)
        return None
    parts: list[str] = []
    if data.get("title"):
        parts.append(str(data["title"]))
    for block in data.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "table":
            cols = block.get("columns") or []
            if cols and isinstance(cols[0], dict):
                headers = [str(c.get("name") or "?") for c in cols]
            else:
                headers = [str(c) for c in cols]
            parts.append("\t".join(headers))
            for row in block.get("rows") or []:
                if isinstance(row, (list, tuple)):
                    parts.append("\t".join(str(c) for c in row))
                else:
                    parts.append(str(row))
        elif block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
    if data.get("rows") and not data.get("blocks"):
        cols = data.get("columns") or []
        parts.append("\t".join(str(c) for c in cols))
        for row in data["rows"]:
            if isinstance(row, (list, tuple)):
                parts.append("\t".join(str(c) for c in row))
    return "\n".join(p for p in parts if p).strip() or None


def _iter_manifest_table_specs(
    game: str, names_filter: list[str] | None
) -> list[dict[str, Any]]:
    manifest = load_ingest_manifest(game)
    specs: list[dict[str, Any]] = []
    for spec in manifest.get("lookup_tables") or []:
        name = spec.get("name")
        if not name:
            continue
        if names_filter is not None and name not in names_filter:
            continue
        specs.append(spec)
    return specs


def _is_pdf_auto_spec(spec: dict[str, Any]) -> bool:
    if skip_pdf_extract(spec):
        return False
    status = (spec.get("pdf_extract") or {}).get("status")
    return status in ("verified", "partial")


def _is_hand_authored_substitute_spec(spec: dict[str, Any]) -> bool:
    ha = spec.get("hand_authored") or {}
    if not ha.get("file"):
        return False
    status = (spec.get("pdf_extract") or {}).get("status")
    if not (skip_pdf_extract(spec) or status == "hand-authored"):
        return False
    patterns = (spec.get("pdf_extract") or {}).get("header_patterns") or []
    return bool(patterns)


def resolve_tables_in_span(
    span_text: str,
    *,
    game: str = "mork-borg",
    names_filter: list[str] | None = None,
    pdf_path: str | Path | None = None,
    text_filters: dict[str, Any] | None = None,
) -> tuple[list[TableHit], list[str]]:
    """
    Find lookup tables in a text span (shared by ingest helpers and pdf-as-md).

    - verified/partial pdf_extract → extract_lookup_table (stream, aligned_columns, or split_italic)
    - hand_authored + header_patterns → load JSON; PDF shred for [start,end) skipped
    """
    warnings: list[str] = []
    if not span_text.strip():
        return [], warnings

    starts: list[tuple[int, str, dict[str, Any]]] = []
    for spec in _iter_manifest_table_specs(game, names_filter):
        pe = spec.get("pdf_extract") or {}
        patterns = pe.get("header_patterns") or []
        if not patterns:
            continue
        header = _find_header(span_text, patterns)
        if not header:
            continue
        if _is_pdf_auto_spec(spec):
            starts.append((header.start(), "pdf", spec))
        elif _is_hand_authored_substitute_spec(spec):
            starts.append((header.start(), "hand_authored", spec))

    starts.sort(key=lambda h: h[0])
    deduped: list[tuple[int, str, dict[str, Any]]] = []
    seen: set[int] = set()
    for start, source, spec in starts:
        if start in seen:
            warnings.append(
                f"duplicate header at {start} skipped {spec.get('name')!r} ({source})"
            )
            continue
        seen.add(start)
        deduped.append((start, source, spec))

    hits: list[TableHit] = []
    for i, (start, source, spec) in enumerate(deduped):
        name = str(spec["name"])
        pe = spec.get("pdf_extract") or {}
        next_start = deduped[i + 1][0] if i + 1 < len(deduped) else len(span_text)
        header = _find_header(span_text, pe.get("header_patterns") or [])
        if header is None:
            continue
        if pe.get("stop_before"):
            sliced = _slice_body(span_text, header.end(), pe.get("stop_before") or [])
            end = min(next_start, header.end() + len(sliced))
        else:
            end = next_start
            if source == "hand_authored" and end >= len(span_text) and (end - start) > 4000:
                warnings.append(
                    f"{name!r}: hand-authored region has no stop_before and extends to "
                    f"end of span ({end - start} chars) — set pdf_extract.stop_before"
                )

        if source == "pdf":
            table = extract_lookup_table(
                spec,
                text=span_text,
                pdf_path=pdf_path,
                page_number=None,
                allow_multi_page=True,
                text_filters=text_filters,
            )
            if not table:
                warnings.append(f"header matched but extract failed for {name!r}")
                continue
            pe_mode = pe.get("mode") or "sequential"
            note = f"via extract_lookup_table ({pe_mode})"
        else:
            table = load_hand_authored_table(spec)
            if not table:
                warnings.append(f"hand-authored load failed for {name!r}")
                continue
            if not table.get("title"):
                table["title"] = table_display_title(
                    spec, matched_header=header.group(0)
                )
            table["pdf_heading"] = " ".join(header.group(0).split())
            table["manifest_name"] = name
            note = "via manifest hand_authored.file"

        hits.append(
            TableHit(
                start=start,
                end=end,
                table=table,
                manifest_name=name,
                source=source,
                note=note,
            )
        )
    return hits, warnings


def section_body_text(
    extract: DocumentExtract,
    resolved: ResolvedSection,
) -> tuple[str, list[str]]:
    """
    Body text for a contract section as ingest should store it.

    Honors ``content_source.skip_pdf_text``; otherwise returns PDF span
    (heading through content_end).
    """
    warnings: list[str] = []
    section = resolved.section
    cs = section.get("content_source") if isinstance(section.get("content_source"), dict) else None
    if cs and cs.get("skip_pdf_text", True):
        plain = content_source_plain_text(extract.game, cs)
        if plain:
            heading = resolved.matched_heading
            return (f"{heading}\n{plain}" if heading else plain), warnings
        warnings.append(
            f"section {section.get('id')!r}: content_source failed — using PDF text"
        )
    return extract.stream[resolved.heading_start : resolved.content_end], warnings
