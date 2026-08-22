#!/usr/bin/env python3
"""Markdown sink for the shared document extract path (no Neo4j).

Parsing lives in ``backend/src/document_extract.py`` (same path ingest uses).
This tool only renders that model to ``.as.md`` for PDF comparison.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from src.document_extract import (  # noqa: E402
    DocumentExtract,
    ResolvedSection,
    load_content_source_payload,
    load_document_extract,
    resolve_tables_in_span,
)


def _passage_table_filters(
    game: str, section_id: str, passage_count: int
) -> list[list[str]] | None:
    """Per-passage table allowlists for known compound sections (optional classes)."""
    if section_id != "optional-classes":
        return None
    path = (
        _REPO_ROOT
        / "games"
        / game
        / "hand-authored-overrides"
        / "optional-classes.json"
    )
    if not path.is_file():
        return None
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    bundles = data.get("bundles") or []
    if len(bundles) != passage_count:
        return None
    return [list(b.get("contains_tables") or []) for b in bundles]


_SPLIT_HEAD_FLAGS = re.MULTILINE | re.IGNORECASE


def _md_escape_heading(text: str) -> str:
    return text.replace("\n", " ").strip()


def _heading_key(text: str) -> str:
    return " ".join(text.split()).casefold()


def _child_heading_from_part(part: str, split_pat: str) -> str | None:
    """First line of a split part is a child title when it matches passage_split."""
    lines = part.splitlines()
    if not lines:
        return None
    first = lines[0]
    if not re.search(split_pat, first, flags=_SPLIT_HEAD_FLAGS):
        return None
    return _md_escape_heading(first)


def _strip_leading_heading_block(text: str, heading: str | None) -> str:
    """Drop a PDF heading already emitted as ``##`` / ``###`` from the body start."""
    if not heading or not text:
        return text
    t_lines = text.lstrip("\n").splitlines()
    h_lines = [ln for ln in heading.splitlines() if ln.strip()]
    if not h_lines or len(t_lines) < len(h_lines):
        return text
    if any(
        _heading_key(t_lines[i]) != _heading_key(h_lines[i])
        for i in range(len(h_lines))
    ):
        return text
    return "\n".join(t_lines[len(h_lines) :]).lstrip("\n")


def _emit_body(text: str) -> str:
    return text.strip() + ("\n" if text.strip() else "")


_PDF_BULLET_GLYPHS = frozenset("\u2020\u2021\u2022\u2023\u2043")


def _fold_preview_text(text: str) -> str:
    return (
        (text or "")
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .casefold()
    )


def _is_pdf_bullet_marker_line(line: str) -> bool:
    visible = "".join(
        ch for ch in (line or "") if not ch.isspace() and ord(ch) >= 32
    )
    return bool(visible) and all(ch in _PDF_BULLET_GLYPHS for ch in visible)


def _line_starts_with_pdf_bullet(line: str) -> bool:
    if _is_pdf_bullet_marker_line(line):
        return True
    stripped = (line or "").lstrip()
    if stripped.startswith("\x07"):
        return True
    return bool(stripped) and stripped[0] in _PDF_BULLET_GLYPHS


def _clean_pdf_bullet_item(line: str) -> str:
    cleaned = "".join(
        ch
        for ch in (line or "")
        if ch.isprintable() and ch not in _PDF_BULLET_GLYPHS and ch != "\x07"
    )
    return cleaned.strip()


def _collect_pdf_bullet_runs(
    lines: list[str],
) -> list[tuple[int, int, list[str]]]:
    """Inclusive start, exclusive end, cleaned item texts. Marker-only + item pairs."""
    runs: list[tuple[int, int, list[str]]] = []
    i = 0
    n = len(lines)
    while i < n:
        if not (
            _is_pdf_bullet_marker_line(lines[i])
            or _line_starts_with_pdf_bullet(lines[i])
        ):
            i += 1
            continue
        start = i
        items: list[str] = []
        while i < n and lines[i].strip():
            ln = lines[i]
            if _is_pdf_bullet_marker_line(ln):
                i += 1
                continue
            if _line_starts_with_pdf_bullet(ln) or (
                i > start and _is_pdf_bullet_marker_line(lines[i - 1])
            ):
                text = _clean_pdf_bullet_item(ln)
                if text:
                    items.append(text)
                i += 1
                continue
            break
        if len(items) >= 2:
            runs.append((start, i, items))
        else:
            i = start + 1
    return runs


def _match_then_summary(item: str, then_rows: list[str]) -> str | None:
    needle = _fold_preview_text(item)
    if len(needle) < 8:
        return None
    for row in then_rows:
        hay = _fold_preview_text(row)
        if needle in hay or hay in needle:
            return row
    return None


def _replace_pdf_bullet_runs(
    text: str,
    *,
    game: str,
    section_id: str | None,
    warnings: list[str],
) -> str:
    """In-place: PDF dagger/BEL lists become a tagged markdown list (table-grid analogue).

    Render only. Does not parse bullets into Neo4j. Needs a spine citing the section.
    """
    if not text or not section_id:
        return text
    from src.spine_materialization import spine_operator_preview, spines_for_section

    spines = spines_for_section(game, section_id)
    if not spines:
        return text
    lines = text.splitlines()
    runs = _collect_pdf_bullet_runs(lines)
    if not runs:
        return text
    previews = [spine_operator_preview(s, text) for s in spines]
    out: list[str] = []
    cursor = 0
    for start, end, items in runs:
        out.extend(lines[cursor:start])
        scored: list[tuple[int, dict[str, Any]]] = []
        for preview in previews:
            then_rows = list(preview.get("then") or [])
            hits = sum(1 for it in items if _match_then_summary(it, then_rows))
            scored.append((hits, preview))
        scored.sort(key=lambda x: -x[0])
        preview = scored[0][1]
        then_rows = list(preview.get("then") or [])
        matched = 0
        rendered: list[str] = []
        for it in items:
            hit = _match_then_summary(it, then_rows)
            if hit:
                matched += 1
                rendered.append(f"- {hit}")
            else:
                rendered.append(f"- {it}")
                warnings.append(
                    f"section {section_id!r}: spine {preview.get('if_id')} "
                    f"list item not in THEN: {it!r}"
                )
        if_id = preview.get("if_id") or "?"
        procs = ", ".join(str(p) for p in (preview.get("procedures") or []) if p) or "?"
        out.append(
            f"> spine `{if_id}` FOR {procs} · {matched}/{len(items)} list items"
        )
        out.append(">")
        out.extend(f"> {row}" for row in rendered)
        cursor = end
    out.extend(lines[cursor:])
    body = "\n".join(out)
    if text.endswith("\n") and not body.endswith("\n"):
        body += "\n"
    return body


def _render_spine_preview_md(preview: dict[str, Any]) -> list[str]:
    """Operator panel: contracted If (not PDF-parsed). Same role as table markdown."""
    if_id = preview.get("if_id") or "?"
    procs = ", ".join(str(p) for p in (preview.get("procedures") or []) if p) or "?"
    ev_bits: list[str] = []
    for needle, ok in preview.get("evidence") or []:
        ev_bits.append(f"`{needle}` {'yes' if ok else 'MISSING'}")
    ev_line = " · ".join(ev_bits) if ev_bits else "(no text_contains_any)"
    lines = [
        f"> spine `{if_id}` FOR {procs} · contract (not PDF-parsed)",
        f"> evidence in this span: {ev_line}",
    ]
    then = [t for t in (preview.get("then") or []) if t]
    if then:
        lines.append(">")
        lines.append("> **THEN**")
        for row in then:
            lines.append(f"> - {row}")
    else_rows = [t for t in (preview.get("else") or []) if t]
    if else_rows:
        lines.append(">")
        lines.append("> **ELSE**")
        for row in else_rows:
            lines.append(f"> - {row}")
    lines.append("")
    return lines


def _append_spine_previews(
    lines: list[str],
    *,
    game: str,
    section_id: str,
    span_text: str,
    warnings: list[str],
) -> None:
    from src.spine_materialization import spine_operator_preview, spines_for_section

    spines = spines_for_section(game, section_id)
    if not spines:
        return
    for spine in spines:
        preview = spine_operator_preview(spine, span_text)
        lines.extend(_render_spine_preview_md(preview))
        missing = [n for n, ok in preview.get("evidence") or [] if not ok]
        for needle in missing:
            warnings.append(
                f"section {section_id!r}: spine {preview.get('if_id')} "
                f"evidence needle missing: {needle!r}"
            )


def _append_place_relation_previews(
    lines: list[str],
    *,
    game: str,
    section_id: str,
    span_text: str,
    warnings: list[str],
) -> None:
    from src.place_relation_materialization import (
        place_relation_operator_preview,
        place_relations_for_section,
    )

    grouped = place_relations_for_section(game, section_id)
    rows: list[tuple[str, dict]] = []
    for row in grouped.get("part_of") or []:
        rows.append(("part_of", row))
    for row in grouped.get("occurs_in_place") or []:
        rows.append(("occurs_in_place", row))
    if not rows:
        return
    for kind, row in rows:
        preview = place_relation_operator_preview(row, span_text, kind=kind)
        ev_bits = [
            f"`{needle}` {'yes' if ok else 'MISSING'}"
            for needle, ok in preview.get("evidence") or []
        ]
        ev_line = " · ".join(ev_bits) if ev_bits else "(no text_contains_any)"
        lines.append(
            f"> place `{preview.get('label')}` · contract (not PDF-parsed)"
        )
        lines.append(f"> evidence in this span: {ev_line}")
        lines.append("")
        for needle, ok in preview.get("evidence") or []:
            if not ok:
                warnings.append(
                    f"section {section_id!r}: place relation "
                    f"{preview.get('label')} evidence needle missing: {needle!r}"
                )


def _render_table_block(
    block: dict[str, Any], *, omit_title: str | None = None
) -> list[str]:
    lines: list[str] = []
    title = block.get("title")
    if title and not (
        omit_title and _heading_key(str(title)) == _heading_key(omit_title)
    ):
        lines.append(f"### {title}")
        lines.append("")
    columns = block.get("columns") or []
    rows = block.get("rows") or []
    italic_cols = {
        str(c) for c in (block.get("italic_columns") or []) if str(c).strip()
    }
    if not columns and rows and isinstance(rows[0], list):
        columns = [f"c{i}" for i in range(len(rows[0]))]
    if isinstance(columns, list) and columns and isinstance(columns[0], dict):
        headers = [str(c.get("name") or c.get("role") or "?") for c in columns]
    else:
        headers = [str(c) for c in columns]
    if not headers:
        return lines
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        if isinstance(row, dict):
            cells = [str(row.get(h, "")) for h in headers]
        elif isinstance(row, (list, tuple)):
            cells = [str(row[i]) if i < len(row) else "" for i in range(len(headers))]
        else:
            cells = [str(row)]
        cells = [c.replace("|", "\\|").replace("\n", " ") for c in cells]
        for i, header in enumerate(headers):
            if header in italic_cols and cells[i].strip():
                cells[i] = f"*{cells[i]}*"
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def _render_content_source_md(game: str, content_source: dict[str, Any]) -> tuple[str | None, str | None]:
    data, err = load_content_source_payload(game, content_source)
    if err or not data:
        return None, err
    path = data.get("_resolved_path", content_source.get("file"))
    out: list[str] = [
        f"> **content_source** `{path}` — PDF text skipped (same as ingest section_chunking).",
        "",
    ]
    if data.get("title"):
        out.append(f"**{data['title']}**")
        out.append("")
    blocks = data.get("blocks")
    if isinstance(blocks, list) and blocks:
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "table":
                out.extend(_render_table_block(block))
                out.append("")
            elif block.get("type") == "text":
                out.append(str(block.get("text") or "").strip())
                out.append("")
    elif isinstance(data.get("rows"), list):
        out.extend(
            _render_table_block(
                {
                    "title": data.get("title") or data.get("manifest_table"),
                    "columns": data.get("columns") or [],
                    "rows": data["rows"],
                }
            )
        )
        out.append("")
    return "\n".join(out).rstrip() + "\n", None


def _table_resolve_kwargs(extract: DocumentExtract) -> dict[str, Any]:
    return {
        "pdf_path": extract.pdf_path,
        "text_filters": (extract.contract or {}).get("text_filters"),
    }


def _render_span_with_tables(
    span_text: str,
    *,
    game: str,
    warnings: list[str],
    label: str,
    names_filter: list[str] | None = None,
    omit_heading: str | None = None,
    pdf_path: Path | None = None,
    text_filters: dict[str, Any] | None = None,
    section_id: str | None = None,
) -> str:
    hits, tw = resolve_tables_in_span(
        span_text,
        game=game,
        names_filter=names_filter,
        pdf_path=pdf_path,
        text_filters=text_filters,
    )
    for w in tw:
        warnings.append(f"{label}: {w}")
    if not hits:
        body = _emit_body(_strip_leading_heading_block(span_text, omit_heading))
        return _replace_pdf_bullet_runs(
            body, game=game, section_id=section_id, warnings=warnings
        )

    parts: list[str] = []
    cursor = 0
    stripped_head = False
    for hit in hits:
        before = span_text[cursor : hit.start]
        if omit_heading and not stripped_head:
            before = _strip_leading_heading_block(before, omit_heading)
            stripped_head = True
        before = before.strip()
        if before:
            parts.append(before)
            parts.append("")
        lead_in = str(hit.table.get("lead_in") or "").strip()
        if lead_in:
            parts.append(lead_in)
            parts.append("")
        display = str(hit.table.get("title") or hit.manifest_name).strip()
        parts.append(
            f"> `{hit.manifest_name}`"
            + (f" · PDF: {hit.table.get('pdf_heading')}" if hit.table.get("pdf_heading") else "")
            + f" {hit.note}"
        )
        parts.append("")
        parts.extend(
            _render_table_block(
                {
                    "title": display,
                    "columns": hit.table.get("columns") or [],
                    "rows": hit.table.get("rows") or [],
                    "italic_columns": hit.table.get("italic_columns") or [],
                },
                omit_title=omit_heading,
            )
        )
        parts.append("")
        cursor = max(cursor, hit.end)
    after = span_text[cursor:].strip()
    if after:
        parts.append(after)
        parts.append("")
    joined = "\n".join(parts).rstrip() + "\n"
    return _replace_pdf_bullet_runs(
        joined, game=game, section_id=section_id, warnings=warnings
    )


def _append_section_md(
    lines: list[str],
    item: ResolvedSection,
    extract: DocumentExtract,
    warnings: list[str],
) -> None:
    from src.section_chunking import split_passages

    section = item.section
    title = _md_escape_heading(str(section.get("title") or section.get("id") or "section"))
    sid = section.get("id", "?")
    content_source = (
        section.get("content_source")
        if isinstance(section.get("content_source"), dict)
        else None
    )
    pages = ""
    if item.page_start is not None:
        if item.page_end is not None and item.page_end != item.page_start:
            pages = f"{item.page_start}-{item.page_end}"
        else:
            pages = str(item.page_start)

    lines.append(f"## {title}")
    lines.append("")
    meta = f"`{sid}`"
    if section.get("index_title"):
        meta += f" · index: {section['index_title']}"
    if pages:
        meta += f" · pages≈{pages}"
    if section.get("operator_page_hint"):
        meta += f" · hint {section['operator_page_hint']}"
    if item.end_at_eof:
        meta += " · end→EOF"
    if item.matched_heading and item.matched_heading != title:
        meta += f" · PDF heading: {item.matched_heading}"
    if content_source:
        meta += " · content_source"
    lines.append(f"<!-- {meta} -->")
    lines.append("")

    if content_source and content_source.get("skip_pdf_text", True):
        rendered, err = _render_content_source_md(extract.game, content_source)
        if err:
            warnings.append(f"section {sid!r}: {err}")
            lines.append(f"> **content_source error:** {err}")
            lines.append("")
            lines.append(
                _emit_body(
                    _strip_leading_heading_block(
                        extract.stream[item.heading_start : item.content_end],
                        item.matched_heading,
                    )
                )
            )
        else:
            assert rendered is not None
            lines.append(rendered.rstrip())
            lines.append("")
        _append_spine_previews(
            lines,
            game=extract.game,
            section_id=str(sid),
            span_text=extract.stream[item.content_start : item.content_end],
            warnings=warnings,
        )
        _append_place_relation_previews(
            lines,
            game=extract.game,
            section_id=str(sid),
            span_text=extract.stream[item.content_start : item.content_end],
            warnings=warnings,
        )
        return

    raw_names = section.get("contains_lookup_tables") or []
    names_filter = [str(n) for n in raw_names if n] or None
    body = extract.stream[item.content_start : item.content_end]
    granularity = section.get("passage_granularity", "paragraph")
    split_cfg = section.get("passage_split") or {}
    split_pat = split_cfg.get("pattern") if granularity == "subheading_regex" else None

    if split_pat:
        parts = split_passages(body, "subheading_regex", split_pattern=split_pat)
        # Section-heading substitutes (e.g. OptionalClassesTable) sit before class bodies.
        # Probe with the first passage head as stop_before sentinel so we don't eat class prose.
        head_gap = extract.stream[item.heading_start : item.content_start]
        if not head_gap.endswith("\n"):
            head_gap += "\n"
        sentinel = (parts[0].splitlines()[0] + "\n") if parts and parts[0].splitlines() else ""
        head_md = _render_span_with_tables(
            head_gap + sentinel,
            game=extract.game,
            warnings=warnings,
            label=f"section {sid!r} heading",
            names_filter=names_filter,
            omit_heading=item.matched_heading,
            section_id=str(sid),
            **_table_resolve_kwargs(extract),
        ).rstrip()
        if sentinel.strip() and head_md.endswith(sentinel.strip()):
            head_md = head_md[: -len(sentinel.strip())].rstrip()
        if head_md.strip():
            lines.append(head_md)
            lines.append("")

        passage_table_filters = _passage_table_filters(extract.game, sid, len(parts))
        for i, part in enumerate(parts):
            child_heading = _child_heading_from_part(part, split_pat)
            first = child_heading or (
                part.splitlines()[0] if part.splitlines() else f"passage {i}"
            )
            lines.append(
                f"> `{sid}#p{i}` · PDF: {_md_escape_heading(first)} via passage_split"
            )
            lines.append("")
            if child_heading:
                lines.append(f"### {child_heading}")
                lines.append("")
            p_filter = passage_table_filters[i] if passage_table_filters else names_filter
            lines.append(
                _render_span_with_tables(
                    part,
                    game=extract.game,
                    warnings=warnings,
                    label=f"section {sid!r}#p{i}",
                    names_filter=p_filter,
                    omit_heading=child_heading,
                    section_id=str(sid),
                    **_table_resolve_kwargs(extract),
                ).rstrip()
            )
            lines.append("")
        _append_spine_previews(
            lines,
            game=extract.game,
            section_id=str(sid),
            span_text=body,
            warnings=warnings,
        )
        _append_place_relation_previews(
            lines,
            game=extract.game,
            section_id=str(sid),
            span_text=body,
            warnings=warnings,
        )
        return

    pdf_span = extract.stream[item.heading_start : item.content_end]
    lines.append(
        _render_span_with_tables(
            pdf_span,
            game=extract.game,
            warnings=warnings,
            label=f"section {sid!r}",
            names_filter=names_filter,
            omit_heading=item.matched_heading,
            section_id=str(sid),
            **_table_resolve_kwargs(extract),
        ).rstrip()
    )
    lines.append("")
    _append_spine_previews(
        lines,
        game=extract.game,
        section_id=str(sid),
        span_text=body,
        warnings=warnings,
    )
    _append_place_relation_previews(
        lines,
        game=extract.game,
        section_id=str(sid),
        span_text=body,
        warnings=warnings,
    )


def render_options(
    *,
    section_ids: list[str],
    pages_only: bool,
    sections_only: bool,
    no_entities: bool,
) -> tuple[str, bool, bool]:
    """Return ``(mode, clip_to_sections, skip_entities)``.

    Bare run: full stream with ``(unsectioned)`` gaps. ``--section`` is a
    focused dump: clip to those spans (gaps only *between* selected ids) and
    skip the CREATURES appendix. ``--sections-only`` still means no
    unsectioned gaps at all.
    """
    focused = bool(section_ids)
    skip_entities = bool(no_entities or pages_only or focused)
    if pages_only:
        return "pages-only", False, skip_entities
    if sections_only:
        return "sections-only", False, skip_entities
    return "document", focused, skip_entities


def _append_unsectioned_gap(
    lines: list[str],
    extract: DocumentExtract,
    warnings: list[str],
    start: int,
    end: int,
) -> None:
    gap = extract.stream[start:end].strip()
    if not gap:
        return
    lines.append("### (unsectioned)")
    lines.append("")
    lines.append(
        _render_span_with_tables(
            gap,
            game=extract.game,
            warnings=warnings,
            label="unsectioned",
            **_table_resolve_kwargs(extract),
        ).rstrip()
    )
    lines.append("")


def render_markdown(
    extract: DocumentExtract,
    *,
    mode: str,
    entity_appendix: str | None,
    clip_to_sections: bool = False,
) -> str:
    warnings = list(extract.warnings)
    lines: list[str] = [
        f"# {extract.file_name} — pdf-as-md extract preview",
        "",
        "> Sink only: parse/resolve via ``backend/src/document_extract.py`` "
        "(same path as ingest ``section_chunking`` + ``resolve_tables_in_span`` / "
        "lookup-table pipeline). Spines citing the section render as a contract "
        "THEN/ELSE panel (not PDF-parsed). **Not** written to Neo4j.",
        "",
        f"- PDF path: `{extract.pdf_path}`",
        f"- Contract: `{extract.contract.get('id')}` v{extract.contract.get('version')} "
        f"({extract.contract.get('status')})",
        f"- Mode: `{mode}`",
        f"- Stream characters: {len(extract.stream)}",
        f"- Sections matched: {len(extract.sections)}",
        "",
    ]

    if mode == "pages-only":
        lines.append("## Full page stream (normalized)")
        lines.append("")
        lines.append(_emit_body(extract.stream))
    elif mode == "sections-only":
        lines.append("## Contract sections")
        lines.append("")
        for item in extract.sections:
            _append_section_md(lines, item, extract, warnings)
    else:
        lines.append("## Document extract (section headings from contract)")
        lines.append("")
        sections = extract.sections
        cursor = (
            sections[0].heading_start if clip_to_sections and sections else 0
        )
        for item in sections:
            if item.heading_start > cursor:
                _append_unsectioned_gap(
                    lines, extract, warnings, cursor, item.heading_start
                )
            _append_section_md(lines, item, extract, warnings)
            cursor = max(cursor, item.content_end)
        if not clip_to_sections and cursor < len(extract.stream):
            _append_unsectioned_gap(
                lines, extract, warnings, cursor, len(extract.stream)
            )

    if entity_appendix:
        lines.append(entity_appendix)

    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_entity_appendix(
    *,
    game: str,
    file_name: str,
    pdf_path: str | None,
    contract: dict[str, Any],
) -> tuple[str | None, list[str]]:
    from src.entity_passage_materialization import (
        compile_stop_before_patterns,
        load_entity_passage_config,
        slice_entity_spans,
    )
    from src.section_chunking import normalize_stream_text
    from src.table_pipeline import load_pdf_text_by_page, resolve_pdf_path

    ep_cfg = load_entity_passage_config(contract)
    if ep_cfg.get("enabled") is False:
        return None, []
    warnings: list[str] = []
    stop_patterns = compile_stop_before_patterns(ep_cfg)
    index_source = contract.get("index_source") or {}
    rows: list[dict[str, Any]] = []
    for item in index_source.get("creatures_index") or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        row: dict[str, Any] = {
            "title": title,
            "page": item.get("page"),
            "entry_kind": item.get("entry_kind") or "creature",
            "column": "CREATURES",
        }
        if item.get("text_end_hint"):
            row["text_end_hint"] = item["text_end_hint"]
        rows.append(row)
    if not rows:
        return None, []

    resolved = resolve_pdf_path(file_name, pdf_path=pdf_path)
    page_texts = {
        p: normalize_stream_text(t) for p, t in load_pdf_text_by_page(resolved).items()
    }
    by_page: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        page = row.get("page")
        if page is None:
            warnings.append(f"entity: no page for {row['title']!r}")
            continue
        by_page.setdefault(int(page), []).append(row)

    lines: list[str] = [
        "## Appendix: CREATURES entity passages",
        "",
        "> Same slicer as runtime `entity_passage_materialization`.",
        "",
    ]
    for page in sorted(by_page):
        spans = slice_entity_spans(
            page_texts.get(page, ""),
            by_page[page],
            stop_patterns=stop_patterns,
        )
        found = {s["title"] for s in spans}
        for entry in by_page[page]:
            if entry["title"] not in found:
                warnings.append(
                    f"entity: start not found for {entry['title']!r} on p.{page}"
                )
        for span in spans:
            title = _md_escape_heading(span["title"])
            lines.append(f"### {title}")
            lines.append("")
            lines.append(
                f"<!-- CREATURES · p.{span.get('page')} · {len(span['text'])} chars -->"
            )
            lines.append("")
            lines.append(_emit_body(span["text"]))
            lines.append("")
    return "\n".join(lines), warnings


def default_output_path(file_name: str) -> Path:
    stem = Path(file_name).stem
    return Path(__file__).resolve().parent / "out" / f"{stem}.as.md"


def _normalize_section_ids(raw: list[str] | None) -> list[str]:
    """Flatten ``--section`` values; allow comma-separated lists in one arg."""
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        for part in str(item).split(","):
            sid = part.strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            out.append(sid)
    return out


def filter_extract_sections_by_id(
    extract: DocumentExtract, section_ids: list[str]
) -> tuple[list[str], list[str]]:
    """Keep only ResolvedSections whose contract id is requested.

    Returns (unknown_ids, unmatched_ids) where unknown are not in the contract
    and unmatched are in the contract but did not resolve in the PDF stream.
    """
    contract_ids = {
        str(s.get("id"))
        for s in (extract.contract.get("sections") or [])
        if s.get("id")
    }
    wanted = set(section_ids)
    unknown = sorted(wanted - contract_ids)
    if unknown:
        return unknown, []

    matched = {
        str(item.section.get("id") or "")
        for item in extract.sections
        if item.section.get("id")
    }
    unmatched = sorted(wanted - matched)
    extract.sections = [
        item
        for item in extract.sections
        if str(item.section.get("id") or "") in wanted
    ]
    return [], unmatched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render shared document_extract (ingest parse path) to Markdown. "
            "Does not write Neo4j."
        )
    )
    parser.add_argument("--game", default="mork-borg")
    parser.add_argument("--file-name", default="mork-borg.pdf")
    parser.add_argument("--pdf", default=None)
    parser.add_argument(
        "--section",
        action="append",
        default=None,
        metavar="ID",
        help=(
            "Contract section id to include (repeatable; comma-separated OK). "
            "Focused dump: clip to those spans (unsectioned gaps only between "
            "selected ids) and skip the CREATURES appendix. Default: all "
            "matched sections. Not an ingest section_phase gate."
        ),
    )
    parser.add_argument("--pages-only", action="store_true")
    parser.add_argument("--sections-only", action="store_true")
    parser.add_argument("--no-entities", action="store_true")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args(argv)

    if args.pages_only and args.sections_only:
        print("Choose at most one of --pages-only / --sections-only", file=sys.stderr)
        return 2

    section_ids = _normalize_section_ids(args.section)

    try:
        extract = load_document_extract(
            args.file_name,
            game=args.game,
            pdf_path=args.pdf,
            phase=None,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if section_ids:
        unknown, unmatched = filter_extract_sections_by_id(extract, section_ids)
        if unknown:
            known = sorted(
                str(s.get("id"))
                for s in (extract.contract.get("sections") or [])
                if s.get("id")
            )
            print(
                f"Unknown section id(s): {', '.join(unknown)}. "
                f"Contract ids include: {', '.join(known[:20])}"
                + ("…" if len(known) > 20 else ""),
                file=sys.stderr,
            )
            return 1
        if unmatched:
            print(
                "Section id(s) in contract but not matched in PDF stream: "
                + ", ".join(unmatched),
                file=sys.stderr,
            )
            return 1

    mode, clip_to_sections, skip_entities = render_options(
        section_ids=section_ids,
        pages_only=args.pages_only,
        sections_only=args.sections_only,
        no_entities=args.no_entities,
    )
    entity_appendix = None
    if not skip_entities:
        entity_appendix, ent_warn = render_entity_appendix(
            game=args.game,
            file_name=args.file_name,
            pdf_path=args.pdf,
            contract=extract.contract,
        )
        extract.warnings.extend(ent_warn)

    md = render_markdown(
        extract,
        mode=mode,
        entity_appendix=entity_appendix,
        clip_to_sections=clip_to_sections,
    )
    out = Path(args.output) if args.output else default_output_path(args.file_name)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(
        f"Wrote {out} ({len(md)} chars, {len(extract.sections)} sections matched, "
        f"{len(extract.warnings)} warnings)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
