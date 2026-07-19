"""Section-driven chunking from passage-sections.json heading anchors (Briefing 6)."""

from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.documents import Document

from src.ingest_manifest import load_ingest_manifest, load_passage_sections
from src.shared.common_fn import execute_graph_query
from src.table_pipeline import load_pdf_text_by_page, resolve_pdf_path

logger = logging.getLogger(__name__)


def _regex_flags(anchor_matching: dict[str, Any]) -> int:
    flags = re.MULTILINE
    if anchor_matching.get("case_insensitive", True):
        flags |= re.IGNORECASE
    return flags


def normalize_stream_text(text: str, *, normalize_whitespace: bool = True) -> str:
    if not normalize_whitespace:
        return text
    lines = [re.sub(r"\s+", " ", line.strip()) for line in text.splitlines()]
    return "\n".join(lines)


def build_page_indexed_stream(
    page_texts: dict[int, str],
) -> tuple[str, list[dict[str, int]]]:
    """Concatenate pages in order; return stream and [{page_number, start, end}, ...]."""
    parts: list[str] = []
    spans: list[dict[str, int]] = []
    offset = 0
    for page_number in sorted(page_texts.keys()):
        if parts:
            parts.append("\n")
            offset += 1
        start = offset
        text = page_texts[page_number]
        parts.append(text)
        offset += len(text)
        spans.append({"page_number": page_number, "start": start, "end": offset})
    return "".join(parts), spans


def page_at_offset(spans: list[dict[str, int]], char_offset: int) -> int | None:
    for span in spans:
        if span["start"] <= char_offset < span["end"]:
            return span["page_number"]
    if spans and char_offset >= spans[-1]["end"]:
        return spans[-1]["page_number"]
    return spans[0]["page_number"] if spans else None


def page_range_for_span(
    spans: list[dict[str, int]], start: int, end: int
) -> tuple[int | None, int | None]:
    start_page = page_at_offset(spans, start)
    end_page = page_at_offset(spans, max(start, end - 1))
    return start_page, end_page


def _anchor_pattern(anchor: dict[str, Any]) -> str:
    if anchor.get("type") != "heading_regex":
        raise ValueError(f"unsupported anchor type: {anchor.get('type')}")
    return str(anchor["pattern"])


def resolve_section_span(
    stream: str,
    section: dict[str, Any],
    *,
    anchor_matching: dict[str, Any],
) -> tuple[int, int] | None:
    """Return (content_start, content_end) offsets in stream; end is exclusive."""
    flags = _regex_flags(anchor_matching)
    start_pat = _anchor_pattern(section["start_anchor"])
    start_m = re.search(start_pat, stream, flags=flags)
    if not start_m:
        return None

    content_start = start_m.end()
    end_pat = _anchor_pattern(section["end_anchor"])
    end_m = re.search(end_pat, stream[content_start:], flags=flags)
    if not end_m:
        return content_start, len(stream)
    return content_start, content_start + end_m.start()


def split_passages(text: str, granularity: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if granularity == "section":
        return [text]
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if parts:
        return parts
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return ["\n".join(lines)] if lines else []


def section_chunk_id(file_name: str, section_id: str) -> str:
    return f"{file_name}#section:{section_id}"


def passage_node_id(file_name: str, section_id: str, index: int) -> str:
    return f"{file_name}#section:{section_id}#p{index}"


def _page_texts_from_documents(pages: list[Document] | None) -> dict[int, str] | None:
    if not pages:
        return None
    by_page: dict[int, str] = {}
    for i, doc in enumerate(pages):
        meta = doc.metadata or {}
        page_num = meta.get("page_number")
        if page_num is None and "page" in meta:
            page_num = int(meta["page"]) + 1
        if page_num is None:
            page_num = i + 1
        by_page[int(page_num)] = doc.page_content
    return by_page


def _load_page_texts(
    file_name: str,
    *,
    pages: list[Document] | None = None,
    pdf_path: str | None = None,
) -> dict[int, str]:
    from_docs = _page_texts_from_documents(pages)
    if from_docs:
        return from_docs
    resolved = resolve_pdf_path(file_name, pdf_path=pdf_path)
    return load_pdf_text_by_page(resolved)


def _merge_section_chunk(
    graph,
    file_name: str,
    section: dict[str, Any],
    text: str,
    page_start: int | None,
    page_end: int | None,
    position: int,
) -> str:
    chunk_id = section_chunk_id(file_name, section["id"])
    execute_graph_query(
        graph,
        """
        MATCH (d:Document {fileName: $file_name})
        MERGE (c:Chunk {id: $chunk_id})
        SET c.text = $text,
            c.fileName = $file_name,
            c.section_id = $section_id,
            c.section_title = $section_title,
            c.source_format = 'passage-section',
            c.position = $position,
            c.length = size($text),
            c.tier = 5,
            c.page_number = $page_start,
            c.page_number_start = $page_start,
            c.page_number_end = $page_end
        MERGE (c)-[:PART_OF]->(d)
        """,
        {
            "file_name": file_name,
            "chunk_id": chunk_id,
            "text": text,
            "section_id": section["id"],
            "section_title": section.get("title", section["id"]),
            "position": position,
            "page_start": page_start,
            "page_end": page_end,
        },
    )
    return chunk_id


def _mark_superseded_page_chunks(
    graph,
    file_name: str,
    page_start: int | None,
    page_end: int | None,
) -> int:
    if page_start is None or page_end is None:
        return 0
    rows = execute_graph_query(
        graph,
        """
        MATCH (c:Chunk)-[:PART_OF]->(:Document {fileName: $file_name})
        WHERE c.section_id IS NULL
          AND c.page_number IS NOT NULL
          AND c.page_number >= $page_start
          AND c.page_number <= $page_end
          AND coalesce(c.superseded_by_section, false) = false
        SET c.superseded_by_section = true
        RETURN count(c) AS n
        """,
        {
            "file_name": file_name,
            "page_start": page_start,
            "page_end": page_end,
        },
    )
    return int(rows[0]["n"]) if rows else 0


def _link_passage_to_seeds(
    graph,
    passage_id: str,
    seed_labels: list[str],
) -> int:
    linked = 0
    for label in seed_labels:
        rows = execute_graph_query(
            graph,
            """
            MATCH (p:RulePassage {id: $passage_id})
            MATCH (s:SeedNode)
            WHERE $label IN labels(s)
            MERGE (p)-[:CONFIRMS_SEED]->(s)
            RETURN count(s) AS n
            """,
            {"passage_id": passage_id, "label": label},
        )
        linked += int(rows[0]["n"]) if rows else 0
    return linked


def _merge_rule_passage(
    graph,
    file_name: str,
    section: dict[str, Any],
    index: int,
    text: str,
    page_number: int | None,
    seed_labels: list[str],
) -> tuple[str, int]:
    passage_id = passage_node_id(file_name, section["id"], index)
    execute_graph_query(
        graph,
        """
        MERGE (p:RulePassage {id: $passage_id})
        SET p.text = $text,
            p.fileName = $file_name,
            p.section_id = $section_id,
            p.section_title = $section_title,
            p.passage_index = $index,
            p.page_number = $page_number,
            p.tier = 5
        WITH p
        MATCH (c:Chunk {id: $chunk_id})
        MERGE (c)-[:DOCUMENTED_BY]->(p)
        """,
        {
            "passage_id": passage_id,
            "text": text,
            "file_name": file_name,
            "section_id": section["id"],
            "section_title": section.get("title", section["id"]),
            "index": index,
            "page_number": page_number,
            "chunk_id": section_chunk_id(file_name, section["id"]),
        },
    )
    seed_links = _link_passage_to_seeds(graph, passage_id, seed_labels)
    return passage_id, seed_links


def _wire_section_chunk_chain(graph, file_name: str, chunk_ids: list[str]) -> None:
    if not chunk_ids:
        return
    execute_graph_query(
        graph,
        """
        MATCH (d:Document {fileName: $file_name})
        OPTIONAL MATCH (d)-[old:FIRST_CHUNK]->(:Chunk)
        DELETE old
        WITH d
        MATCH (c:Chunk {id: $first_id})
        MERGE (d)-[:FIRST_CHUNK]->(c)
        """,
        {"file_name": file_name, "first_id": chunk_ids[0]},
    )
    for prev_id, next_id in zip(chunk_ids, chunk_ids[1:]):
        execute_graph_query(
            graph,
            """
            MATCH (prev:Chunk {id: $prev_id})
            MATCH (next:Chunk {id: $next_id})
            MERGE (next)<-[:NEXT_CHUNK]-(prev)
            """,
            {"prev_id": prev_id, "next_id": next_id},
        )


def materialize_passage_sections(
    graph,
    file_name: str,
    *,
    game: str = "mork-borg",
    phase: int = 1,
    pages: list[Document] | None = None,
    pdf_path: str | None = None,
    strict_phase: bool = False,
) -> dict[str, Any]:
    """
    Chunk document text by passage-sections.json heading anchors.
    Idempotent MERGE on stable section/passage ids.
    """
    stats: dict[str, Any] = {
        "sections_expected": 0,
        "sections_matched": 0,
        "chunks_created": 0,
        "passages_created": 0,
        "seed_links_created": 0,
        "page_chunks_superseded": 0,
        "warnings": [],
    }

    manifest = load_ingest_manifest(game)
    if not (manifest.get("passage_sections") or {}).get("file"):
        stats["warnings"].append("manifest has no passage_sections.file — skipped")
        return stats

    contract = load_passage_sections(game)
    anchor_matching = contract.get("anchor_matching") or {}
    all_sections = contract.get("sections") or []
    if strict_phase:
        sections = [s for s in all_sections if s.get("phase") == phase]
    else:
        sections = [s for s in all_sections if (s.get("phase") or 99) <= phase]
    stats["sections_expected"] = len(sections)
    if not sections:
        return stats

    try:
        page_texts = _load_page_texts(file_name, pages=pages, pdf_path=pdf_path)
    except FileNotFoundError as exc:
        stats["warnings"].append(str(exc))
        return stats

    stream, spans = build_page_indexed_stream(page_texts)
    stream = normalize_stream_text(
        stream, normalize_whitespace=anchor_matching.get("normalize_whitespace", True)
    )

    chunk_ids: list[str] = []
    position = 0
    for section in sections:
        section_id = section.get("id", "?")
        span = resolve_section_span(stream, section, anchor_matching=anchor_matching)
        if span is None:
            hint = section.get("operator_page_hint", "?")
            msg = f"start anchor not found for section {section_id!r} (operator_page_hint={hint})"
            logger.warning("section_chunking: %s", msg)
            stats["warnings"].append(msg)
            continue

        content_start, content_end = span
        section_text = stream[content_start:content_end].strip()
        if not section_text:
            msg = f"empty section text for {section_id!r}"
            logger.warning("section_chunking: %s", msg)
            stats["warnings"].append(msg)
            continue

        if content_end >= len(stream):
            hint = section.get("operator_page_hint", "?")
            msg = (
                f"end anchor not found for section {section_id!r} "
                f"(extended to EOF; operator_page_hint={hint})"
            )
            logger.warning("section_chunking: %s", msg)
            stats["warnings"].append(msg)

        page_start, page_end = page_range_for_span(spans, content_start, content_end)
        position += 1
        chunk_id = _merge_section_chunk(
            graph,
            file_name,
            section,
            section_text,
            page_start,
            page_end,
            position,
        )
        chunk_ids.append(chunk_id)
        stats["sections_matched"] += 1
        stats["chunks_created"] += 1
        stats["page_chunks_superseded"] += _mark_superseded_page_chunks(
            graph, file_name, page_start, page_end
        )

        if section.get("extract_rule_passages", True):
            granularity = section.get("passage_granularity", "paragraph")
            seed_labels = section.get("links_to_seed_labels") or []
            for i, para in enumerate(split_passages(section_text, granularity)):
                para_offset = content_start + section_text.find(para)
                page_num = page_at_offset(spans, para_offset)
                _, seed_links = _merge_rule_passage(
                    graph,
                    file_name,
                    section,
                    i,
                    para,
                    page_num,
                    seed_labels,
                )
                stats["passages_created"] += 1
                stats["seed_links_created"] += seed_links

    _wire_section_chunk_chain(graph, file_name, chunk_ids)
    logger.info(
        "section_chunking: matched=%s passages=%s superseded=%s warnings=%s",
        stats["sections_matched"],
        stats["passages_created"],
        stats["page_chunks_superseded"],
        len(stats["warnings"]),
    )
    return stats


def section_chunks_for_llm(
    graph,
    file_name: str,
    *,
    game: str = "mork-borg",
    phase: int = 1,
) -> list[dict[str, Any]]:
    """Return section chunk entries in LLM processing shape."""
    contract = load_passage_sections(game)
    section_ids = {
        s["id"]
        for s in contract.get("sections") or []
        if (s.get("phase") or 99) <= phase and s.get("id")
    }
    if not section_ids:
        return []

    rows = execute_graph_query(
        graph,
        """
        MATCH (c:Chunk)-[:PART_OF]->(:Document {fileName: $file_name})
        WHERE c.section_id IN $section_ids
        RETURN c.id AS chunk_id, c.text AS text, c.section_id AS section_id,
               c.section_title AS section_title, c.page_number AS page_number,
               c.position AS position
        ORDER BY c.page_number_start, c.position
        """,
        {"file_name": file_name, "section_ids": list(section_ids)},
    )
    result = []
    for row in rows:
        meta = {
            "section_id": row.get("section_id"),
            "section_title": row.get("section_title"),
            "page_number": row.get("page_number"),
            "source_format": "passage-section",
        }
        result.append(
            {
                "chunk_id": row["chunk_id"],
                "chunk_doc": Document(page_content=row["text"] or "", metadata=meta),
            }
        )
    return result


def filter_chunks_for_llm(graph, file_name: str, chunk_list: list[dict]) -> list[dict]:
    """Drop token/page chunks superseded by section chunks."""
    if not chunk_list:
        return chunk_list
    rows = execute_graph_query(
        graph,
        """
        MATCH (c:Chunk)-[:PART_OF]->(:Document {fileName: $file_name})
        WHERE c.id IN $chunk_ids
        RETURN c.id AS id, coalesce(c.superseded_by_section, false) AS superseded
        """,
        {"file_name": file_name, "chunk_ids": [c["chunk_id"] for c in chunk_list]},
    )
    superseded = {r["id"] for r in rows if r.get("superseded")}
    return [c for c in chunk_list if c["chunk_id"] not in superseded]
