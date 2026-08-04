"""Entity-scoped RulePassage materialization for catalog fiction (Briefings 10–11).

Splits dense bestiary pages so Goblin prose is not the whole page Chunk.
End cuts (bounty/loot tallies, etc.) come from passage-sections.json
``entity_passage.end_detection`` — not hardcoded layout vocabulary in this module.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.index_materialization import (
    _document_exists,
    _entity_id,
    slug_title,
)
from src.ingest_manifest import load_passage_sections
from src.section_chunking import normalize_stream_text
from src.shared.common_fn import execute_graph_query
from src.table_pipeline import load_pdf_text_by_page, resolve_pdf_path

logger = logging.getLogger(__name__)

# Fallback column scope if contract omits entity_passage.columns
_DEFAULT_ENTITY_PASSAGE_COLUMNS = frozenset({"CREATURES"})


def entity_passage_id(file_name: str, column: str, title: str) -> str:
    return f"{file_name}#entity-passage:{column}:{slug_title(title)}"


def _title_body_regex(title: str) -> str:
    """Allow optional parentheticals between words (e.g. Undead (weak) necromancer)."""
    words = [w for w in re.split(r"\s+", title.strip()) if w]
    if not words:
        return r"(?!)"
    if len(words) == 1:
        return re.escape(words[0])
    joiner = r"(?:\s+(?:\([^)]*\)\s*)?)+"
    return joiner.join(re.escape(w) for w in words)


def find_title_start(page_text: str, title: str) -> int | None:
    """Return char offset of the line that introduces this index title, or None."""
    body = _title_body_regex(title)
    # Prefer "Name, Title" heading lines; fall back to any whole-line title hit.
    patterns = [
        re.compile(rf"(?im)^(?P<line>[^\n]{{0,60}},\s*{body}\s*)$"),
        re.compile(rf"(?im)^(?P<line>[^\n]*\b{body}\b[^\n]*)$"),
    ]
    for pat in patterns:
        m = pat.search(page_text)
        if m:
            return m.start("line")
    return None


def load_entity_passage_config(contract: dict[str, Any] | None = None, *, game: str = "mork-borg") -> dict[str, Any]:
    """Return entity_passage block from passage-sections.json (empty dict if absent)."""
    if contract is None:
        contract = load_passage_sections(game)
    block = contract.get("entity_passage")
    return block if isinstance(block, dict) else {}


def compile_stop_before_patterns(entity_passage: dict[str, Any]) -> list[re.Pattern[str]]:
    """Compile exclusive end patterns from entity_passage.end_detection.stop_before."""
    end = entity_passage.get("end_detection") or {}
    if not isinstance(end, dict):
        return []
    flags_s = str(end.get("stop_before_flags") or "im")
    flags = 0
    if "i" in flags_s:
        flags |= re.IGNORECASE
    if "m" in flags_s:
        flags |= re.MULTILINE
    compiled: list[re.Pattern[str]] = []
    for item in end.get("stop_before") or []:
        if isinstance(item, str):
            pattern = item
        elif isinstance(item, dict):
            pattern = str(item.get("pattern") or "").strip()
            if item.get("type") not in (None, "line_regex", "regex"):
                logger.warning("entity_passages: unknown stop_before type %r — treating as regex", item.get("type"))
        else:
            continue
        if not pattern:
            continue
        compiled.append(re.compile(pattern, flags))
    return compiled


def find_stop_before_start(span_text: str, patterns: list[re.Pattern[str]]) -> int | None:
    """Offset of the earliest stop_before match within a creature span (exclusive cut)."""
    best: int | None = None
    for pat in patterns:
        m = pat.search(span_text)
        if m is None:
            continue
        if best is None or m.start() < best:
            best = m.start()
    return best


def find_text_end_hint(span_text: str, hint: str | None) -> int | None:
    """Optional per-entry exclusive end: literal substring, else regex."""
    if not hint:
        return None
    hint = hint.strip()
    if not hint:
        return None
    at = span_text.find(hint)
    if at >= 0:
        return at
    try:
        m = re.search(hint, span_text, flags=re.IGNORECASE | re.MULTILINE)
    except re.error:
        return None
    return m.start() if m else None


def trim_span_end(
    page_text: str,
    start: int,
    end: int,
    *,
    stop_patterns: list[re.Pattern[str]] | None = None,
    text_end_hint: str | None = None,
) -> int:
    """Tighten end using contract stop_before and optional per-entry text_end_hint."""
    span = page_text[start:end]
    cuts: list[int] = []
    hint_at = find_text_end_hint(span, text_end_hint)
    if hint_at is not None:
        cuts.append(hint_at)
    stop_at = find_stop_before_start(span, stop_patterns or [])
    if stop_at is not None:
        cuts.append(stop_at)
    if not cuts:
        return end
    return start + min(cuts)


def slice_entity_spans(
    page_text: str,
    entries: list[dict[str, Any]],
    *,
    stop_patterns: list[re.Pattern[str]] | None = None,
) -> list[dict[str, Any]]:
    """
    For entries sharing one page, find start offsets and slice so neighbors and
    contract stop_before / text_end_hint cuts do not bleed into the prior block.
    """
    located: list[tuple[int, dict[str, Any]]] = []
    for entry in entries:
        title = str(entry.get("title") or "").strip()
        if not title:
            continue
        start = find_title_start(page_text, title)
        if start is None:
            continue
        located.append((start, entry))

    located.sort(key=lambda item: item[0])
    deduped: list[tuple[int, dict[str, Any]]] = []
    seen_starts: set[int] = set()
    for start, entry in located:
        if start in seen_starts:
            continue
        seen_starts.add(start)
        deduped.append((start, entry))

    spans: list[dict[str, Any]] = []
    for i, (start, entry) in enumerate(deduped):
        end = deduped[i + 1][0] if i + 1 < len(deduped) else len(page_text)
        end = trim_span_end(
            page_text,
            start,
            end,
            stop_patterns=stop_patterns,
            text_end_hint=entry.get("text_end_hint"),
        )
        text = page_text[start:end].strip()
        if not text:
            continue
        spans.append(
            {
                "title": entry["title"],
                "column": entry["column"],
                "entry_kind": entry.get("entry_kind"),
                "page": entry.get("page"),
                "text": text,
                "char_start": start,
                "char_end": end,
            }
        )
    return spans


def _load_creatures_from_contract(game: str) -> list[dict[str, Any]]:
    contract = load_passage_sections(game)
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
        hint = item.get("text_end_hint")
        if hint:
            row["text_end_hint"] = hint
        rows.append(row)
    return rows


def materialize_entity_passages(
    graph,
    file_name: str,
    *,
    game: str = "mork-borg",
    columns: frozenset[str] | None = None,
    pdf_path: str | None = None,
) -> dict[str, Any]:
    """
    For each CREATURES IndexEntry: slice entity span from PDF page → MERGE RulePassage.
    Links: (entity)-[:DOCUMENTED_BY]->(passage), (entry)-[:MAPS_TO_PASSAGE]->(passage).
    """
    stats: dict[str, Any] = {
        "passages_created": 0,
        "links_documented_by": 0,
        "links_maps_to_passage": 0,
        "by_title": {},
        "warnings": [],
    }

    contract = load_passage_sections(game)
    ep_cfg = load_entity_passage_config(contract)
    if ep_cfg.get("enabled") is False:
        stats["warnings"].append("entity_passage.enabled is false — skipped")
        return stats

    scope = columns
    if scope is None:
        cfg_cols = ep_cfg.get("columns") or list(_DEFAULT_ENTITY_PASSAGE_COLUMNS)
        scope = frozenset(str(c) for c in cfg_cols)

    stop_patterns = compile_stop_before_patterns(ep_cfg)
    if not stop_patterns:
        stats["warnings"].append(
            "entity_passage.end_detection.stop_before empty — only next-title cuts apply"
        )

    if not _document_exists(graph, file_name):
        stats["warnings"].append(f"Document {file_name!r} not found — skipped entity passages")
        return stats

    try:
        resolved = resolve_pdf_path(file_name, pdf_path=pdf_path)
        page_texts = {
            p: normalize_stream_text(t) for p, t in load_pdf_text_by_page(resolved).items()
        }
    except FileNotFoundError as exc:
        stats["warnings"].append(str(exc))
        return stats

    contract_rows = _load_creatures_from_contract(game)
    if "CREATURES" not in scope:
        contract_rows = []

    by_page: dict[int, list[dict[str, Any]]] = {}
    for row in contract_rows:
        page = row.get("page")
        if page is None:
            stats["warnings"].append(f"no page for creature {row['title']!r}")
            continue
        by_page.setdefault(int(page), []).append(row)

    all_spans: list[dict[str, Any]] = []
    for page, entries in sorted(by_page.items()):
        page_text = page_texts.get(page, "")
        if not page_text:
            stats["warnings"].append(f"empty PDF text for page {page}")
            continue
        spans = slice_entity_spans(page_text, entries, stop_patterns=stop_patterns)
        found = {s["title"] for s in spans}
        for entry in entries:
            if entry["title"] not in found:
                msg = f"start anchor not found for creature {entry['title']!r} on p.{page}"
                stats["warnings"].append(msg)
                logger.warning("entity_passages: %s", msg)
        all_spans.extend(spans)

    for span in all_spans:
        title = span["title"]
        column = span["column"]
        entry_kind = span.get("entry_kind") or "creature"
        page = span.get("page")
        text = span["text"]
        passage_id = entity_passage_id(file_name, column, title)
        entity_id = _entity_id(file_name, entry_kind, title)
        entry_id = f"{file_name}#index:{column}:{slug_title(title)}"

        execute_graph_query(
            graph,
            """
            MERGE (p:RulePassage {id: $passage_id})
            SET p.text = $text,
                p.fileName = $file_name,
                p.page_number = $page,
                p.index_title = $title,
                p.column = $column,
                p.entry_kind = $entry_kind,
                p.entity_id = $entity_id,
                p.source_format = 'entity-passage',
                p.tier = 5
            """,
            {
                "passage_id": passage_id,
                "text": text,
                "file_name": file_name,
                "page": page,
                "title": title,
                "column": column,
                "entry_kind": entry_kind,
                "entity_id": entity_id,
            },
        )
        stats["passages_created"] += 1
        stats["by_title"][title] = {"page": page, "chars": len(text)}

        entity_rows = execute_graph_query(
            graph,
            """
            MATCH (p:RulePassage {id: $passage_id})
            MATCH (entity:IngestNode {id: $entity_id})
            MERGE (entity)-[:DOCUMENTED_BY]->(p)
            RETURN entity.id AS id
            """,
            {"passage_id": passage_id, "entity_id": entity_id},
        )
        if entity_rows:
            stats["links_documented_by"] += 1
        else:
            stats["warnings"].append(f"no fiction IngestNode for {title!r} ({entity_id})")

        entry_rows = execute_graph_query(
            graph,
            """
            MATCH (p:RulePassage {id: $passage_id})
            MATCH (e:IndexEntry {id: $entry_id})
            MERGE (e)-[:MAPS_TO_PASSAGE]->(p)
            RETURN e.id AS id
            """,
            {"passage_id": passage_id, "entry_id": entry_id},
        )
        if entry_rows:
            stats["links_maps_to_passage"] += 1
        else:
            stats["warnings"].append(f"no IndexEntry for {title!r} ({entry_id})")

    logger.info(
        "entity_passages: created=%s documented_by=%s maps_to_passage=%s stop_patterns=%s warnings=%s",
        stats["passages_created"],
        stats["links_documented_by"],
        stats["links_maps_to_passage"],
        len(stop_patterns),
        len(stats["warnings"]),
    )
    return stats
