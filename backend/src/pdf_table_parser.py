"""Extract lookup tables from PDF chunk text using ingest-manifest pdf_extract signatures."""

import json
import logging
import re
from typing import Any

from langchain_core.documents import Document

from src.ingest_manifest import column_names, load_ingest_manifest, lookup_table_specs, spec_by_name

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f]+")
_MAX_LABEL_LEN = 2000


def _skip_pdf_extract(spec: dict[str, Any]) -> bool:
    return bool((spec.get("hand_authored") or {}).get("skip_pdf_extract"))


def _clean_label(raw: str) -> str:
    return " ".join(_CONTROL_CHAR_RE.sub(" ", raw).split())


def _normalize_range_key(key: str) -> str:
    return key.replace("\u2013", "-").strip()


def _index_keys(index_type: str, index_cfg: dict) -> list[str]:
    if index_cfg.get("values"):
        return [_normalize_range_key(str(v)) for v in index_cfg["values"]]
    if index_type == "dr_set":
        return [str(v) for v in index_cfg.get("values") or []]
    if index_type == "d12":
        return [str(i) for i in range(1, 13)]
    if index_type == "d10":
        return [str(i) for i in range(1, 11)]
    if index_type == "d8":
        return [str(i) for i in range(1, 9)]
    if index_type == "d6":
        return [str(i) for i in range(1, 7)]
    if index_type == "d20":
        return [str(i) for i in range(1, 21)]
    if index_type == "d100":
        return [str(i) for i in range(1, 101)]
    if index_type == "d100_pairs":
        return [f"{i}-{i + 1}" for i in range(1, 99, 2)] + ["99-00"]
    return []


def _key_boundary_pattern(key: str, *, dotted: bool = False) -> re.Pattern:
    key = _normalize_range_key(key)
    if "-" in key:
        parts = key.split("-", 1)
        key_expr = rf"{re.escape(parts[0])}[\-–]{re.escape(parts[1])}"
    else:
        key_expr = re.escape(key)
    suffix = r"(?:[\s\t]+|\.)" if dotted else r"(?:[\s\t]+)"
    return re.compile(rf"(?:^|[\s\t]){key_expr}{suffix}", re.IGNORECASE)


def _parse_rows_sequential(
    body: str, keys: list[str], index_type: str, *, dotted: bool = False
) -> list[list[Any]]:
    """Parse rows in key order so digits inside prose are not mistaken for row indices."""
    if not keys:
        return []

    rows: list[list[Any]] = []
    search_from = 0
    for i, key in enumerate(keys):
        match = _key_boundary_pattern(key, dotted=dotted).search(body, search_from)
        if not match:
            break
        start = match.end()
        if i + 1 < len(keys):
            next_match = _key_boundary_pattern(keys[i + 1], dotted=dotted).search(body, start)
            end = next_match.start() if next_match else len(body)
        else:
            end = len(body)
        label = _clean_label(body[start:end])
        if not label or len(label) > _MAX_LABEL_LEN:
            continue
        rows.append([_parse_index_value(key, index_type), label])
        search_from = end
    return rows


def _page_span(spec: dict[str, Any]) -> list[int]:
    pages = spec.get("pages")
    if not pages or pages == "TBD":
        return []
    if isinstance(pages, int):
        return [pages]
    text = str(pages)
    if "-" in text:
        start, end = text.split("-", 1)
        return list(range(int(start.strip()), int(end.strip()) + 1))
    try:
        return [int(text.strip())]
    except ValueError:
        return []


def _find_header(text: str, patterns: list[str]) -> re.Match | None:
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match
    return None


def _slice_body(text: str, start: int, stop_before: list[str]) -> str:
    body = text[start:]
    if not stop_before:
        return body
    earliest = len(body)
    for pat in stop_before:
        match = re.search(pat, body, re.IGNORECASE | re.DOTALL)
        if match:
            earliest = min(earliest, match.start())
    return body[:earliest]


def page_span(spec: dict[str, Any]) -> list[int]:
    """Public alias for manifest page span (single page or inclusive range)."""
    return _page_span(spec)


def _parse_index_value(raw: str, index_type: str) -> Any:
    raw = raw.strip()
    if index_type == "dr_set":
        try:
            return int(raw)
        except ValueError:
            return raw
    if index_type in ("d12", "d10", "d8", "d6", "d20", "d100"):
        try:
            return int(raw)
        except ValueError:
            return raw
    if index_type in ("d100_pairs", "range_list"):
        return _normalize_range_key(raw)
    if index_type == "d66":
        if "–" in raw or "-" in raw:
            return raw.replace("–", "-").strip()
        try:
            return int(raw)
        except ValueError:
            return raw
    return raw


def extract_table_from_text(
    text: str,
    spec: dict[str, Any],
    *,
    page_number: int | None = None,
    allow_multi_page: bool = False,
) -> dict | None:
    """Parse one lookup table from chunk text per manifest pdf_extract block."""
    if not text:
        return None

    pdf_extract = spec.get("pdf_extract") or {}
    if pdf_extract.get("status") == "todo" or _skip_pdf_extract(spec):
        return None

    if len(_page_span(spec)) >= 2 and not allow_multi_page:
        return None

    prefer_page = pdf_extract.get("prefer_page")
    if prefer_page is not None and page_number is not None and page_number != prefer_page:
        return None

    header_patterns = pdf_extract.get("header_patterns") or []
    if not header_patterns:
        return None

    header = _find_header(text, header_patterns)
    if not header:
        return None

    body = _slice_body(text, header.end(), pdf_extract.get("stop_before") or [])
    index_cfg = pdf_extract.get("index") or {}
    index_type = index_cfg.get("type") or ""
    keys = _index_keys(index_type, index_cfg)
    if not keys:
        return None

    cols = column_names(spec)
    if len(cols) < 2:
        return None

    rows = _parse_rows_sequential(
        body,
        keys,
        index_type,
        dotted=bool(pdf_extract.get("dotted_index")),
    )

    min_rows = pdf_extract.get("min_rows") or 1
    if len(rows) < min_rows:
        return None

    max_rows = pdf_extract.get("max_rows")
    if max_rows is not None and len(rows) > max_rows:
        rows = rows[:max_rows]

    return {
        "manifest_name": spec["name"],
        "title": spec["name"],
        "columns": cols,
        "rows": rows,
    }


def extract_all_tables_from_text(
    text: str,
    *,
    page_number: int | None = None,
    game: str = "mork-borg",
) -> list[dict]:
    tables: list[dict] = []
    for spec in lookup_table_specs(game):
        table = extract_table_from_text(text, spec, page_number=page_number)
        if table:
            tables.append(table)
    return tables


def _is_pdf_chunk(meta: dict) -> bool:
    if meta.get("source_format") == "structured-json":
        return False
    return meta.get("page_number") is not None or meta.get("block_type") is None


def _parse_tables_from_metadata(meta: dict) -> list[dict]:
    raw = meta.get("table_json")
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return [raw]
    return []


def _attach_table_to_chunk(meta: dict, chunk_doc: Document, tables: list[dict]) -> None:
    if len(tables) == 1:
        meta["table_json"] = json.dumps(tables[0])
        meta["block_title"] = tables[0].get("title", tables[0].get("manifest_name"))
    else:
        meta["table_json"] = json.dumps(tables)
        meta["block_title"] = ", ".join(t.get("manifest_name", "?") for t in tables)
    meta["block_type"] = "table"
    meta["source_format"] = meta.get("source_format") or "pdf"
    chunk_doc.metadata = meta


def enrich_pdf_chunks_with_tables(
    chunk_list: list[dict],
    *,
    game: str = "mork-borg",
    force: bool = False,
) -> dict[str, int]:
    """Scan PDF chunks; attach extracted table_json (one object or array) per chunk."""
    stats = {"chunks_scanned": 0, "tables_found": 0}
    manifest = load_ingest_manifest(game)

    sorted_items = sorted(
        chunk_list,
        key=lambda item: (item.get("chunk_doc") or Document(page_content="")).metadata.get(
            "page_number", 9999
        )
        or 9999,
    )

    page_to_item: dict[int, dict] = {}
    chunks_by_page: dict[int, str] = {}
    for item in sorted_items:
        chunk_doc: Document = item.get("chunk_doc")
        if chunk_doc is None:
            continue
        page = (chunk_doc.metadata or {}).get("page_number")
        if page is not None:
            page_to_item[page] = item
            chunks_by_page[page] = chunk_doc.page_content or ""

    materialized_on_chunk: set[str] = set()

    for item in sorted_items:
        chunk_doc: Document = item.get("chunk_doc")
        if chunk_doc is None:
            continue

        meta = chunk_doc.metadata or {}
        if not force and (meta.get("table_json") or not _is_pdf_chunk(meta)):
            continue
        if not _is_pdf_chunk(meta):
            continue

        stats["chunks_scanned"] += 1
        page = meta.get("page_number")
        tables = extract_all_tables_from_text(
            chunk_doc.page_content,
            page_number=page,
            game=game,
        )
        for table in tables:
            materialized_on_chunk.add(table.get("manifest_name", ""))
        if not tables:
            if force:
                meta.pop("table_json", None)
                meta.pop("block_type", None)
                meta.pop("block_title", None)
                chunk_doc.metadata = meta
            continue

        _attach_table_to_chunk(meta, chunk_doc, tables)
        stats["tables_found"] += len(tables)
        logging.info(
            "pdf table parser: found %s table(s) on page %s: %s",
            len(tables),
            page,
            [t.get("manifest_name") for t in tables],
        )

    for spec in manifest.get("lookup_tables") or []:
        name = spec.get("name")
        if not name or name in materialized_on_chunk or _skip_pdf_extract(spec):
            continue
        pdf_status = (spec.get("pdf_extract") or {}).get("status")
        if pdf_status in ("todo", "hand-authored"):
            continue
        span = _page_span(spec)
        if len(span) < 2:
            continue
        merged_text = " ".join(chunks_by_page.get(p, "") for p in span)
        table = extract_table_from_text(
            merged_text, spec, page_number=span[0], allow_multi_page=True
        )
        if not table:
            continue
        anchor = page_to_item.get(span[0])
        if not anchor:
            continue
        anchor_doc: Document = anchor.get("chunk_doc")
        if anchor_doc is None:
            continue
        anchor_meta = anchor_doc.metadata or {}
        existing = _parse_tables_from_metadata(anchor_meta)
        if any(t.get("manifest_name") == name for t in existing):
            prior = next(t for t in existing if t.get("manifest_name") == name)
            if len(prior.get("rows") or []) >= len(table.get("rows") or []):
                continue
            existing = [t for t in existing if t.get("manifest_name") != name]
        _attach_table_to_chunk(anchor_meta, anchor_doc, existing + [table])
        materialized_on_chunk.add(name)
        stats["tables_found"] += 1
        logging.info(
            "pdf table parser: multi-page %s from pages %s (%s rows)",
            name,
            span,
            len(table.get("rows") or []),
        )

    return stats


def persist_chunk_table_metadata(graph, chunk_list: list[dict]) -> int:
    """Write table_json / block_type back onto :Chunk nodes (layer C evidence)."""
    updated = 0
    for item in chunk_list:
        chunk_id = item.get("chunk_id")
        chunk_doc: Document = item.get("chunk_doc")
        if not chunk_id or chunk_doc is None:
            continue

        meta = chunk_doc.metadata or {}
        table_json = meta.get("table_json")
        if not table_json:
            continue

        try:
            graph.query(
                """
                MATCH (c:Chunk {id: $chunk_id})
                SET c.table_json = $table_json,
                    c.block_type = $block_type,
                    c.block_title = $block_title,
                    c.source_format = coalesce(c.source_format, $source_format)
                """,
                {
                    "chunk_id": chunk_id,
                    "table_json": table_json,
                    "block_type": meta.get("block_type", "table"),
                    "block_title": meta.get("block_title"),
                    "source_format": meta.get("source_format", "pdf"),
                },
            )
            updated += 1
        except Exception as e:
            logging.error("pdf table parser: failed to persist chunk %s: %s", chunk_id, e)

    return updated


def tables_from_chunk_metadata(meta: dict) -> list[dict]:
    """Return table dict(s) from chunk metadata table_json."""
    return _parse_tables_from_metadata(meta)
