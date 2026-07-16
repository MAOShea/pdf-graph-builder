"""Unified lookup-table pipeline: PDF on disk → Neo4j (manifest-driven).

Single orchestrator for service and CLI. Page text is always read from the PDF file,
never from Neo4j chunk storage.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fitz import open as fitz_open
from langchain_core.documents import Document

from src.bundle_materialization import materialize_character_creation_bundles
from src.hand_authored_tables import materialize_hand_authored_tables, skip_pdf_extract
from src.ingest_manifest import _project_root, load_ingest_manifest
from src.make_relationships import create_relation_between_chunks
from src.pdf_table_parser import (
    _attach_table_to_chunk,
    extract_table_from_text,
    page_span,
    persist_chunk_table_metadata,
)
from src.table_materialization import materialize_lookup_table

logger = logging.getLogger(__name__)


def resolve_pdf_path(
    file_name: str,
    *,
    pdf_path: str | Path | None = None,
    merged_file_path: str | Path | None = None,
) -> Path:
    """Locate the PDF file on disk (never Neo4j)."""
    candidates: list[Path] = []
    if pdf_path is not None:
        candidates.append(Path(pdf_path))
    if merged_file_path is not None:
        candidates.append(Path(merged_file_path))
    root = _project_root()
    candidates.extend(
        [
            root / file_name,
            root / "backend" / "merged_files" / file_name,
            Path(__file__).resolve().parents[1] / "merged_files" / file_name,
        ]
    )
    for path in candidates:
        if path.is_file():
            return path.resolve()
    tried = ", ".join(str(p) for p in candidates)
    raise FileNotFoundError(
        f"PDF not found for {file_name!r}. Pass pdf_path= or place the file at repo root. Tried: {tried}"
    )


def load_pdf_text_by_page(pdf_path: Path) -> dict[int, str]:
    doc = fitz_open(pdf_path)
    by_page = {i + 1: doc[i].get_text() for i in range(len(doc))}
    doc.close()
    return by_page


def _span_overlaps_range(span: list[int], start: int | None, end: int | None) -> bool:
    if not span:
        return False
    lo = min(span)
    hi = max(span)
    if start is not None and hi < start:
        return False
    if end is not None and lo > end:
        return False
    return True


def _pdf_extractable_specs(
    manifest: dict[str, Any],
    *,
    table_names: list[str] | None = None,
    start_page: int | None = None,
    end_page: int | None = None,
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for spec in manifest.get("lookup_tables") or []:
        name = spec.get("name")
        if not name:
            continue
        if table_names and name not in table_names:
            continue
        if skip_pdf_extract(spec):
            continue
        pdf_status = (spec.get("pdf_extract") or {}).get("status")
        if pdf_status in ("todo", "hand-authored"):
            continue
        span = page_span(spec)
        if not span:
            continue
        if not _span_overlaps_range(span, start_page, end_page):
            continue
        specs.append(spec)
    return specs


def run_lookup_table_pipeline(
    graph,
    file_name: str,
    scaffold_map: dict,
    *,
    pdf_path: str | Path | None = None,
    merged_file_path: str | Path | None = None,
    game: str = "mork-borg",
    table_names: list[str] | None = None,
    start_page: int | None = None,
    end_page: int | None = None,
    hand_authored: bool = True,
    bundles: bool = True,
) -> dict[str, Any]:
    """Parse manifest lookup tables from PDF and materialize into Neo4j."""
    stats: dict[str, Any] = {
        "pdf_path": None,
        "pdf_tables_parsed": 0,
        "pdf_tables_materialized": 0,
        "pdf_tables_failed": 0,
        "chunks_persisted": 0,
        "hand_authored": {},
        "bundles": {},
        "failures": [],
    }

    if not scaffold_map:
        logger.warning("lookup table pipeline: empty scaffold_map — skipping")
        return stats

    resolved = resolve_pdf_path(
        file_name, pdf_path=pdf_path, merged_file_path=merged_file_path
    )
    stats["pdf_path"] = str(resolved)
    by_page = load_pdf_text_by_page(resolved)
    manifest = load_ingest_manifest(game)

    chunk_items: list[dict] = []
    materialized: set[str] = set()

    for spec in _pdf_extractable_specs(
        manifest,
        table_names=table_names,
        start_page=start_page,
        end_page=end_page,
    ):
        name = spec["name"]
        if name in materialized:
            continue
        span = page_span(spec)
        merged_text = " ".join(by_page.get(p, "") for p in span)
        table = extract_table_from_text(
            merged_text,
            spec,
            page_number=span[0],
            allow_multi_page=len(span) > 1,
        )
        if not table:
            stats["pdf_tables_failed"] += 1
            stats["failures"].append(f"{name}: parse failed (pages {span})")
            logger.warning("lookup table pipeline: parse failed for %s pages %s", name, span)
            continue

        stats["pdf_tables_parsed"] += 1
        chunk_doc = Document(
            page_content=merged_text,
            metadata={"page_number": span[0], "source_format": "pdf"},
        )
        meta = chunk_doc.metadata
        _attach_table_to_chunk(meta, chunk_doc, [table])
        chunk_doc.metadata = meta

        chunk_list = create_relation_between_chunks(graph, file_name, [chunk_doc])
        if not chunk_list:
            stats["pdf_tables_failed"] += 1
            stats["failures"].append(f"{name}: no Document node for {file_name}")
            continue

        chunk_id = chunk_list[0]["chunk_id"]
        chunk_items.append(
            {"chunk_id": chunk_id, "chunk_doc": chunk_doc, **chunk_list[0]}
        )

        if materialize_lookup_table(
            graph, chunk_id, table, spec, chunk_doc, file_name, scaffold_map
        ):
            materialized.add(name)
            stats["pdf_tables_materialized"] += 1
            logger.info(
                "lookup table pipeline: %s materialized (%s rows, pages %s)",
                name,
                len(table.get("rows") or []),
                span,
            )
        else:
            stats["pdf_tables_failed"] += 1
            stats["failures"].append(f"{name}: materialize_lookup_table returned false")

    stats["chunks_persisted"] = persist_chunk_table_metadata(graph, chunk_items)

    if hand_authored:
        ha_stats = materialize_hand_authored_tables(
            graph,
            file_name,
            scaffold_map,
            game=game,
            table_name=table_names[0] if table_names and len(table_names) == 1 else None,
        )
        stats["hand_authored"] = ha_stats

    if bundles:
        stats["bundles"] = materialize_character_creation_bundles(
            graph, file_name, scaffold_map, game=game
        )

    return stats
