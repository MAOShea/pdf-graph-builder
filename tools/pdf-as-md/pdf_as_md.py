#!/usr/bin/env python3
"""Markdown sink for the shared document extract path (no Neo4j).

Parsing lives in ``backend/src/document_extract.py`` (same path ingest uses).
This tool only renders that model to ``.as.md`` for PDF comparison.
"""

from __future__ import annotations

import argparse
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


def _md_escape_heading(text: str) -> str:
    return text.replace("\n", " ").strip()


def _emit_body(text: str) -> str:
    return text.strip() + ("\n" if text.strip() else "")


def _render_table_block(block: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    title = block.get("title")
    if title:
        lines.append(f"### {title}")
        lines.append("")
    columns = block.get("columns") or []
    rows = block.get("rows") or []
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


def _render_span_with_tables(
    span_text: str,
    *,
    game: str,
    warnings: list[str],
    label: str,
    names_filter: list[str] | None = None,
) -> str:
    hits, tw = resolve_tables_in_span(span_text, game=game, names_filter=names_filter)
    for w in tw:
        warnings.append(f"{label}: {w}")
    if not hits:
        return _emit_body(span_text)

    parts: list[str] = []
    cursor = 0
    for hit in hits:
        before = span_text[cursor : hit.start].strip()
        if before:
            parts.append(before)
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
                }
            )
        )
        parts.append("")
        cursor = max(cursor, hit.end)
    after = span_text[cursor:].strip()
    if after:
        parts.append(after)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


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
    phase = section.get("phase", "?")
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
    meta = f"`{sid}` · phase {phase}"
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
        if item.matched_heading:
            lines.append(item.matched_heading)
            lines.append("")
        rendered, err = _render_content_source_md(extract.game, content_source)
        if err:
            warnings.append(f"section {sid!r}: {err}")
            lines.append(f"> **content_source error:** {err}")
            lines.append("")
            lines.append(
                _emit_body(extract.stream[item.heading_start : item.content_end])
            )
        else:
            assert rendered is not None
            lines.append(rendered.rstrip())
            lines.append("")
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
        ).rstrip()
        if sentinel.strip() and head_md.endswith(sentinel.strip()):
            head_md = head_md[: -len(sentinel.strip())].rstrip()
        if head_md.strip():
            lines.append(head_md)
            lines.append("")

        passage_table_filters = _passage_table_filters(extract.game, sid, len(parts))
        for i, part in enumerate(parts):
            first = part.splitlines()[0] if part.splitlines() else f"passage {i}"
            lines.append(
                f"> `{sid}#p{i}` · PDF: {_md_escape_heading(first)} via passage_split"
            )
            lines.append("")
            p_filter = passage_table_filters[i] if passage_table_filters else names_filter
            lines.append(
                _render_span_with_tables(
                    part,
                    game=extract.game,
                    warnings=warnings,
                    label=f"section {sid!r}#p{i}",
                    names_filter=p_filter,
                ).rstrip()
            )
            lines.append("")
        return

    pdf_span = extract.stream[item.heading_start : item.content_end]
    lines.append(
        _render_span_with_tables(
            pdf_span,
            game=extract.game,
            warnings=warnings,
            label=f"section {sid!r}",
            names_filter=names_filter,
        ).rstrip()
    )
    lines.append("")


def render_markdown(
    extract: DocumentExtract,
    *,
    mode: str,
    entity_appendix: str | None,
) -> str:
    warnings = list(extract.warnings)
    lines: list[str] = [
        f"# {extract.file_name} — pdf-as-md extract preview",
        "",
        "> Sink only: parse/resolve via ``backend/src/document_extract.py`` "
        "(same path as ingest ``section_chunking`` + ``resolve_tables_in_span`` / "
        "lookup-table pipeline). **Not** written to Neo4j.",
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
        cursor = 0
        for item in extract.sections:
            if item.heading_start > cursor:
                gap = extract.stream[cursor : item.heading_start].strip()
                if gap:
                    lines.append("### (unsectioned)")
                    lines.append("")
                    lines.append(
                        _render_span_with_tables(
                            gap,
                            game=extract.game,
                            warnings=warnings,
                            label="unsectioned",
                        ).rstrip()
                    )
                    lines.append("")
            _append_section_md(lines, item, extract, warnings)
            cursor = max(cursor, item.content_end)
        if cursor < len(extract.stream):
            gap = extract.stream[cursor:].strip()
            if gap:
                lines.append("### (unsectioned)")
                lines.append("")
                lines.append(
                    _render_span_with_tables(
                        gap,
                        game=extract.game,
                        warnings=warnings,
                        label="unsectioned",
                    ).rstrip()
                )
                lines.append("")

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
    parser.add_argument("--phase", type=int, default=None)
    parser.add_argument("--pages-only", action="store_true")
    parser.add_argument("--sections-only", action="store_true")
    parser.add_argument("--no-entities", action="store_true")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args(argv)

    if args.pages_only and args.sections_only:
        print("Choose at most one of --pages-only / --sections-only", file=sys.stderr)
        return 2

    try:
        extract = load_document_extract(
            args.file_name,
            game=args.game,
            pdf_path=args.pdf,
            phase=args.phase,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    entity_appendix = None
    if not args.no_entities and not args.pages_only:
        entity_appendix, ent_warn = render_entity_appendix(
            game=args.game,
            file_name=args.file_name,
            pdf_path=args.pdf,
            contract=extract.contract,
        )
        extract.warnings.extend(ent_warn)

    if args.pages_only:
        mode = "pages-only"
    elif args.sections_only:
        mode = "sections-only"
    else:
        mode = "document"

    md = render_markdown(extract, mode=mode, entity_appendix=entity_appendix)
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
