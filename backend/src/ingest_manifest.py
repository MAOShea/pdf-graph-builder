"""Load Tier-5 ingest manifest (lookup table contracts + pdf_extract signatures)."""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_GAME = "mork-borg"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def manifest_path(game: str = DEFAULT_GAME) -> Path:
    return _project_root() / "games" / game / "ingest-manifest.json"


@lru_cache(maxsize=4)
def load_ingest_manifest(game: str = DEFAULT_GAME) -> dict[str, Any]:
    path = manifest_path(game)
    if not path.is_file():
        logging.warning("ingest manifest not found: %s", path)
        return {"lookup_tables": []}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def lookup_table_specs(
    game: str = DEFAULT_GAME,
    *,
    extract_status: tuple[str, ...] | None = ("verified", "partial"),
) -> list[dict[str, Any]]:
    from src.hand_authored_tables import skip_pdf_extract

    manifest = load_ingest_manifest(game)
    specs = manifest.get("lookup_tables") or []
    if extract_status is None:
        return specs
    result = []
    for s in specs:
        pdf_status = (s.get("pdf_extract") or {}).get("status")
        if pdf_status in extract_status and not skip_pdf_extract(s):
            result.append(s)
    return result


def spec_by_name(manifest: dict[str, Any], name: str) -> dict[str, Any] | None:
    for spec in manifest.get("lookup_tables") or []:
        if spec.get("name") == name:
            return spec
    return None


def column_names(spec: dict[str, Any]) -> list[str]:
    return [c["name"] for c in spec.get("columns") or []]


def passage_sections_path(game: str = DEFAULT_GAME) -> Path:
    manifest = load_ingest_manifest(game)
    rel = (manifest.get("passage_sections") or {}).get("file", "passage-sections.json")
    return _project_root() / "games" / game / rel


@lru_cache(maxsize=4)
def load_passage_sections(game: str = DEFAULT_GAME) -> dict[str, Any]:
    path = passage_sections_path(game)
    if not path.is_file():
        logging.warning("passage sections contract not found: %s", path)
        return {"sections": []}
    with path.open(encoding="utf-8") as f:
        return json.load(f)
