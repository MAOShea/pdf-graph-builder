"""
Load hand-authored structured JSON rulebook sections into LangChain Documents.

Each leaf block becomes one atomic chunk (no token splitting). See docs/structured-ingest-schema.md.
"""
import json
import logging
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

SOURCE_FORMAT = "structured-json"
SCHEMA_VERSION = "1"


class StructuredJsonError(Exception):
    pass


def _render_table(block: dict) -> str:
    title = block.get("title", "")
    columns = block.get("columns") or []
    rows = block.get("rows") or []
    lines: list[str] = []
    if title:
        lines.append(f"## {title}")
    if columns:
        lines.append("| " + " | ".join(str(c) for c in columns) + " |")
        lines.append("| " + " | ".join("---" for _ in columns) + " |")
        for row in rows:
            cells = list(row) if isinstance(row, (list, tuple)) else [row]
            while len(cells) < len(columns):
                cells.append("")
            lines.append("| " + " | ".join(str(c) for c in cells[: len(columns)]) + " |")
    return "\n".join(lines)


def _render_text_block(block: dict, heading_path: list[str]) -> str:
    parts: list[str] = []
    if heading_path:
        parts.append(" > ".join(heading_path))
    title = block.get("title")
    if title and title not in heading_path:
        parts.append(f"## {title}")
    text = (block.get("text") or "").strip()
    if text:
        parts.append(text)
    return "\n\n".join(parts)


def _flatten_blocks(
    blocks: list,
    envelope: dict,
    heading_path: list[str] | None = None,
    source_path: str = "",
) -> list[Document]:
    heading_path = list(heading_path or [])
    section_id = envelope.get("section_id", "")
    file_title = envelope.get("title", "")
    documents: list[Document] = []

    for block in blocks:
        if not isinstance(block, dict):
            raise StructuredJsonError(f"Each block must be an object, got {type(block).__name__}")

        block_type = block.get("type")
        if not block_type:
            if "columns" in block and "rows" in block:
                block_type = "table"
            elif "blocks" in block:
                block_type = "section"
            elif "text" in block:
                block_type = "text"
            else:
                raise StructuredJsonError(f"Block missing type and could not infer: {block.keys()}")

        if block_type == "section":
            title = block.get("title", "")
            child_path = heading_path + ([title] if title else [])
            child_blocks = block.get("blocks") or []
            if not child_blocks:
                logging.warning("Empty section block skipped: %s", title or "(untitled)")
                continue
            documents.extend(
                _flatten_blocks(child_blocks, envelope, child_path, source_path)
            )
            continue

        if block_type == "text":
            content = _render_text_block(block, heading_path)
            if not content.strip():
                continue
            meta = {
                "source_format": SOURCE_FORMAT,
                "schema_version": SCHEMA_VERSION,
                "section_id": section_id,
                "file_title": file_title,
                "block_type": "text",
                "block_title": block.get("title") or (heading_path[-1] if heading_path else ""),
                "heading_path": heading_path,
                "source": source_path,
            }
            documents.append(Document(page_content=content, metadata=meta))

        elif block_type == "table":
            columns = block.get("columns") or []
            rows = block.get("rows") or []
            if not columns or not rows:
                raise StructuredJsonError("Table block requires non-empty columns and rows")
            content = _render_table(block)
            table_json = json.dumps({"title": block.get("title"), "columns": columns, "rows": rows}, ensure_ascii=False)
            meta = {
                "source_format": SOURCE_FORMAT,
                "schema_version": SCHEMA_VERSION,
                "section_id": section_id,
                "file_title": file_title,
                "block_type": "table",
                "block_title": block.get("title", ""),
                "heading_path": heading_path,
                "table_json": table_json,
                "source": source_path,
            }
            documents.append(Document(page_content=content, metadata=meta))

        else:
            raise StructuredJsonError(f"Unknown block type: {block_type}")

    return documents


def _normalize_envelope(data: Any, file_path: str) -> dict:
    if isinstance(data, str):
        return {"title": Path(file_path).stem, "blocks": [{"type": "text", "text": data}]}
    if not isinstance(data, dict):
        raise StructuredJsonError("JSON root must be an object or string")

    if "blocks" in data:
        return data

    if "text" in data:
        return {
            "source": data.get("source"),
            "section_id": data.get("section_id") or Path(file_path).stem,
            "title": data.get("title") or Path(file_path).stem,
            "blocks": [{"type": "text", "title": data.get("title"), "text": data["text"]}],
        }

    if "columns" in data and "rows" in data:
        return {
            "source": data.get("source"),
            "section_id": data.get("section_id") or Path(file_path).stem,
            "title": data.get("title") or Path(file_path).stem,
            "blocks": [data],
        }

    raise StructuredJsonError(
        "JSON must have a 'blocks' array, or be a {text} / {title,text} / table object"
    )


def load_structured_json_documents(file_path: str | Path) -> list[Document]:
    path = Path(file_path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    envelope = _normalize_envelope(data, str(path))
    blocks = envelope.get("blocks") or []
    if not blocks:
        raise StructuredJsonError(f"No blocks in structured JSON: {path}")

    documents = _flatten_blocks(blocks, envelope, source_path=str(path))
    if not documents:
        raise StructuredJsonError(f"No content blocks produced from: {path}")

    for i, doc in enumerate(documents):
        doc.metadata["block_index"] = i

    logging.info(
        "Structured JSON %s: %d atomic block(s) from section_id=%s",
        path.name,
        len(documents),
        envelope.get("section_id", ""),
    )
    return documents


def is_structured_json_file(file_path: str | Path) -> bool:
    path = Path(file_path)
    if path.suffix.lower() != ".json":
        return False
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, str):
            return True
        if not isinstance(data, dict):
            return False
        if "blocks" in data or "text" in data or ("columns" in data and "rows" in data):
            return True
        if data.get("source_format") == SOURCE_FORMAT:
            return True
    except (json.JSONDecodeError, OSError):
        return False
    return False
