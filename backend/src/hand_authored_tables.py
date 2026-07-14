"""Hand-authored table overrides (exceptions to PDF extraction)."""

import json
import logging
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from src.document_sources.structured_json import load_structured_json_documents
from src.ingest_manifest import _project_root, column_names, load_ingest_manifest, spec_by_name
from src.make_relationships import create_relation_between_chunks
from src.table_materialization import materialize_lookup_table


def _hand_authored_cfg(spec: dict[str, Any]) -> dict[str, Any]:
    return spec.get("hand_authored") or {}


def skip_pdf_extract(spec: dict[str, Any]) -> bool:
    return bool(_hand_authored_cfg(spec).get("skip_pdf_extract"))


def resolve_hand_authored_path(spec: dict[str, Any]) -> Path | None:
    cfg = _hand_authored_cfg(spec)
    rel = cfg.get("file")
    if not rel:
        return None
    path = Path(rel)
    if not path.is_absolute():
        path = _project_root() / path
    return path if path.is_file() else None


def table_from_document(doc: Document, spec: dict[str, Any]) -> dict:
    raw = doc.metadata.get("table_json")
    if isinstance(raw, str):
        table = json.loads(raw)
    elif isinstance(raw, dict):
        table = raw
    else:
        raise ValueError("Document has no table_json metadata")
    table["manifest_name"] = spec["name"]
    table["columns"] = column_names(spec)
    return table


def load_hand_authored_table(spec: dict[str, Any]) -> dict | None:
    path = resolve_hand_authored_path(spec)
    if not path:
        logging.warning("hand-authored file missing for %s", spec.get("name"))
        return None
    docs = load_structured_json_documents(path)
    for doc in docs:
        if doc.metadata.get("block_type") == "table" and doc.metadata.get("table_json"):
            return table_from_document(doc, spec)
    return None


def hand_authored_specs(game: str = "mork-borg") -> list[dict[str, Any]]:
    manifest = load_ingest_manifest(game)
    return [s for s in manifest.get("lookup_tables") or [] if _hand_authored_cfg(s).get("file")]


def _spec_for_json_path(path: Path, game: str) -> dict[str, Any]:
    manifest = load_ingest_manifest(game)
    with path.open(encoding="utf-8") as f:
        envelope = json.load(f)
    table_name = envelope.get("manifest_table")
    if table_name:
        spec = spec_by_name(manifest, table_name)
        if spec:
            return spec
    for spec in manifest.get("lookup_tables") or []:
        ha = _hand_authored_cfg(spec)
        if ha.get("file") and Path(ha["file"]).name == path.name:
            return spec
    raise ValueError(
        f"No manifest lookup_tables entry for {path.name}. "
        "Set manifest_table in JSON or hand_authored.file in ingest-manifest.json"
    )


def materialize_hand_authored_tables(
    graph,
    file_name: str,
    scaffold_map: dict,
    *,
    game: str = "mork-borg",
    table_name: str | None = None,
) -> dict[str, int]:
    """Load manifest hand-authored files and materialize (skip PDF for those tables)."""
    stats = {"tables_loaded": 0, "tables_materialized": 0}
    for spec in hand_authored_specs(game):
        if table_name and spec.get("name") != table_name:
            continue
        path = resolve_hand_authored_path(spec)
        if not path:
            continue
        docs = load_structured_json_documents(path)
        for doc in docs:
            if doc.metadata.get("block_type") != "table":
                continue
            table = table_from_document(doc, spec)
            stats["tables_loaded"] += 1
            doc.metadata["source_format"] = "hand-authored"
            doc.metadata["override_pdf"] = True
            doc.metadata["hand_authored_file"] = path.name
            chunk_list = create_relation_between_chunks(graph, file_name, [doc])
            if not chunk_list:
                continue
            chunk_id = chunk_list[0]["chunk_id"]
            if materialize_lookup_table(
                graph, chunk_id, table, spec, doc, file_name, scaffold_map
            ):
                stats["tables_materialized"] += 1
    return stats


def ingest_hand_authored_file(
    graph,
    json_path: str | Path,
    file_name: str = "mork-borg.pdf",
    *,
    game: str = "mork-borg",
    scaffold_map: dict | None = None,
) -> dict[str, int]:
    """CLI entry: ingest one hand-authored JSON table file."""
    from src.graphDB_dataAccess import graphDBdataAccess

    path = Path(json_path)
    spec = _spec_for_json_path(path, game)
    if scaffold_map is None:
        scaffold_map = graphDBdataAccess(graph).fetch_scaffold_node_map()

    docs = load_structured_json_documents(path)
    table_doc = next(
        (d for d in docs if d.metadata.get("block_type") == "table" and d.metadata.get("table_json")),
        None,
    )
    if not table_doc:
        raise ValueError(f"No table block in {path}")

    table = table_from_document(table_doc, spec)
    table_doc.metadata["source_format"] = "hand-authored"
    table_doc.metadata["override_pdf"] = True
    table_doc.metadata["hand_authored_file"] = path.name

    chunk_list = create_relation_between_chunks(graph, file_name, [table_doc])
    if not chunk_list:
        raise RuntimeError("Failed to create chunk node — is Document present in Neo4j?")

    chunk_id = chunk_list[0]["chunk_id"]
    ok = materialize_lookup_table(
        graph, chunk_id, table, spec, table_doc, file_name, scaffold_map
    )
    return {"tables_loaded": 1, "tables_materialized": 1 if ok else 0}
