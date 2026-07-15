"""Phase 2 bundle wiring: selector rows → OptionalClass bundles → nested tables."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.ingest_manifest import _project_root, load_ingest_manifest, spec_by_name
from src.table_materialization import _find_seed_id, _row_index_key

logger = logging.getLogger(__name__)


@dataclass
class BundleWiringPlan:
    bundles: list[dict[str, Any]] = field(default_factory=list)
    selector_table: str = ""
    applies_during: str = "CharacterCreation"
    character_creation_uses_selector: bool = True
    selects: list[tuple[str, str]] = field(default_factory=list)
    contains: list[tuple[str, str]] = field(default_factory=list)
    uses: list[tuple[str, str]] = field(default_factory=list)
    applies_during_links: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def bundles_schema_path(game: str = "mork-borg") -> Path:
    return _project_root() / "games" / game / "tables" / "optional-classes.json"


def load_bundles_schema(game: str = "mork-borg") -> dict[str, Any] | None:
    path = bundles_schema_path(game)
    if not path.is_file():
        logger.warning("bundle materialization: schema not found: %s", path)
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _selector_row_id(table_name: str, cells: dict[str, Any], col_defs: list[dict]) -> str:
    return f"{table_name}:row:{_row_index_key(cells, col_defs)}"


def build_character_creation_wiring(
    manifest: dict[str, Any],
    bundles_data: dict[str, Any],
) -> BundleWiringPlan | None:
    """Build idempotent wiring plan from manifest + optional-classes.json."""
    cc = manifest.get("character_creation")
    if not cc:
        return None

    plan = BundleWiringPlan(
        selector_table=cc.get("selector_table", "OptionalClassesTable"),
        applies_during=cc.get("applies_during", "CharacterCreation"),
    )

    selector_spec = spec_by_name(manifest, plan.selector_table)
    if not selector_spec:
        plan.warnings.append(f"selector table spec missing: {plan.selector_table}")
        return plan

    col_defs = selector_spec.get("columns") or []
    for acceptance in selector_spec.get("acceptance_rows") or []:
        bundle_id = acceptance.get("selects_bundle")
        cells = acceptance.get("cells") or {}
        if not bundle_id or not cells:
            continue
        row_id = _selector_row_id(plan.selector_table, cells, col_defs)
        plan.selects.append((row_id, bundle_id))

    parent_by_table: dict[str, str] = {}
    for spec in manifest.get("lookup_tables") or []:
        parent = spec.get("parent_bundle")
        if parent:
            parent_by_table[spec["name"]] = parent

    json_contains: dict[str, set[str]] = {}
    for bundle in bundles_data.get("bundles") or []:
        bundle_id = bundle.get("id")
        if not bundle_id:
            continue
        plan.bundles.append(bundle)
        plan.applies_during_links.append(bundle_id)
        json_contains[bundle_id] = set(bundle.get("contains_tables") or [])
        for table_name in bundle.get("uses_tables") or []:
            plan.uses.append((bundle_id, table_name))

    for table_name, bundle_id in parent_by_table.items():
        plan.contains.append((bundle_id, table_name))
        expected = json_contains.get(bundle_id)
        if expected is not None and table_name not in expected:
            plan.warnings.append(
                f"manifest parent_bundle {bundle_id} → {table_name} "
                f"not listed in optional-classes.json contains_tables"
            )

    for bundle_id, tables in json_contains.items():
        manifest_tables = {t for t, p in parent_by_table.items() if p == bundle_id}
        if manifest_tables and manifest_tables != tables:
            plan.warnings.append(
                f"optional-classes.json contains_tables for {bundle_id} "
                f"({sorted(tables)}) differs from manifest ({sorted(manifest_tables)})"
            )

    return plan


def _merge_bundle_node(
    graph,
    bundle: dict[str, Any],
    file_name: str,
    instance_of_seed: str,
) -> None:
    bundle_id = bundle["id"]
    labels = ["IngestNode", "OptionalClass", "SelectableBundle", bundle_id]
    label_clause = ":".join(labels)
    props = {
        "id": bundle_id,
        "name": bundle.get("name", bundle_id),
        "tier": 5,
        "source": file_name,
    }
    if bundle.get("pages"):
        props["pages"] = bundle["pages"]

    graph.query(
        f"""
        MERGE (bundle:{label_clause} {{id: $bundle_id}})
        SET bundle += $props
        WITH bundle
        MATCH (seed:SeedNode)
        WHERE toLower(coalesce(seed.seed_id, seed.id, seed.name, '')) = toLower($instance_of_seed)
        MERGE (bundle)-[:INSTANCE_OF]->(seed)
        """,
        {
            "bundle_id": bundle_id,
            "props": props,
            "instance_of_seed": instance_of_seed,
        },
    )


def _ensure_character_creation_uses_selector(
    graph,
    selector_table: str,
    applies_during: str,
) -> bool:
    rows = graph.query(
        f"""
        MATCH (cc:SeedNode)
        WHERE $applies_during IN labels(cc) OR cc.name = $applies_during
        MATCH (t:IngestNode {{id: $selector_table}})
        MERGE (cc)-[:USES]->(t)
        RETURN count(*) AS linked
        """,
        {"selector_table": selector_table, "applies_during": applies_during},
    )
    return bool(rows and rows[0].get("linked"))


def _merge_applies_during(graph, bundle_id: str, applies_during: str) -> bool:
    rows = graph.query(
        """
        MATCH (bundle:IngestNode {id: $bundle_id})
        MATCH (cc:SeedNode)
        WHERE $applies_during IN labels(cc) OR cc.name = $applies_during
        MERGE (bundle)-[:APPLIES_DURING]->(cc)
        RETURN count(*) AS linked
        """,
        {"bundle_id": bundle_id, "applies_during": applies_during},
    )
    return bool(rows and rows[0].get("linked"))


def _merge_selects(graph, row_id: str, bundle_id: str) -> bool:
    rows = graph.query(
        """
        MATCH (row:TableEntry {id: $row_id})
        MATCH (bundle:IngestNode {id: $bundle_id})
        MERGE (row)-[:SELECTS]->(bundle)
        RETURN count(*) AS linked
        """,
        {"row_id": row_id, "bundle_id": bundle_id},
    )
    return bool(rows and rows[0].get("linked"))


def _merge_contains(graph, bundle_id: str, table_name: str) -> bool:
    rows = graph.query(
        """
        MATCH (bundle:IngestNode {id: $bundle_id})
        MATCH (table:IngestNode {id: $table_name})
        MERGE (bundle)-[:CONTAINS]->(table)
        RETURN count(*) AS linked
        """,
        {"bundle_id": bundle_id, "table_name": table_name},
    )
    return bool(rows and rows[0].get("linked"))


def _merge_uses(graph, bundle_id: str, table_name: str) -> bool:
    rows = graph.query(
        """
        MATCH (bundle:IngestNode {id: $bundle_id})
        MATCH (ext:IngestNode {id: $table_name})
        MERGE (bundle)-[:USES]->(ext)
        RETURN count(*) AS linked
        """,
        {"bundle_id": bundle_id, "table_name": table_name},
    )
    return bool(rows and rows[0].get("linked"))


def apply_bundle_wiring_plan(
    graph,
    plan: BundleWiringPlan,
    file_name: str,
    scaffold_map: dict,
    *,
    cc_config: dict[str, Any],
) -> dict[str, int]:
    """Execute wiring plan against Neo4j. Idempotent."""
    stats = {
        "bundles_created": 0,
        "selects_linked": 0,
        "contains_linked": 0,
        "uses_linked": 0,
        "applies_during_linked": 0,
        "warnings": len(plan.warnings),
    }

    mat_cfg = cc_config.get("materialization") or {}
    instance_of_label = mat_cfg.get("bundle_instance_of", "OptionalClass")
    instance_of_seed = _find_seed_id(scaffold_map, instance_of_label, graph)
    if not instance_of_seed:
        plan.warnings.append(f"bundle seed not found: {instance_of_label}")
        stats["warnings"] = len(plan.warnings)
        logger.warning(
            "bundle materialization: %s seed missing — skipping bundle nodes",
            instance_of_label,
        )
    else:
        for bundle in plan.bundles:
            _merge_bundle_node(graph, bundle, file_name, instance_of_seed)
            stats["bundles_created"] += 1

    if plan.character_creation_uses_selector:
        _ensure_character_creation_uses_selector(
            graph, plan.selector_table, plan.applies_during
        )

    for bundle_id in plan.applies_during_links:
        if _merge_applies_during(graph, bundle_id, plan.applies_during):
            stats["applies_during_linked"] += 1

    for row_id, bundle_id in plan.selects:
        if _merge_selects(graph, row_id, bundle_id):
            stats["selects_linked"] += 1
        else:
            plan.warnings.append(f"SELECTS skipped — row or bundle missing: {row_id} → {bundle_id}")

    for bundle_id, table_name in plan.contains:
        if _merge_contains(graph, bundle_id, table_name):
            stats["contains_linked"] += 1
        else:
            plan.warnings.append(
                f"CONTAINS skipped — bundle or table missing: {bundle_id} → {table_name}"
            )

    for bundle_id, table_name in plan.uses:
        if _merge_uses(graph, bundle_id, table_name):
            stats["uses_linked"] += 1
        else:
            plan.warnings.append(
                f"USES skipped — bundle or external table missing: {bundle_id} → {table_name}"
            )

    for warning in plan.warnings:
        logger.warning("bundle materialization: %s", warning)

    stats["warnings"] = len(plan.warnings)
    return stats


def materialize_character_creation_bundles(
    graph,
    file_name: str,
    scaffold_map: dict,
    *,
    game: str = "mork-borg",
) -> dict[str, int]:
    """
    Wire character-creation bundles per manifest character_creation block.
    Call after flat table materialization (pass 1).
    """
    manifest = load_ingest_manifest(game)
    cc = manifest.get("character_creation")
    if not cc:
        logger.info("bundle materialization: no character_creation block — skipping")
        return {"bundles_created": 0, "selects_linked": 0, "contains_linked": 0,
                "uses_linked": 0, "applies_during_linked": 0, "warnings": 0}

    bundles_data = load_bundles_schema(game)
    if not bundles_data:
        return {"bundles_created": 0, "selects_linked": 0, "contains_linked": 0,
                "uses_linked": 0, "applies_during_linked": 0, "warnings": 1}

    plan = build_character_creation_wiring(manifest, bundles_data)
    if plan is None:
        return {"bundles_created": 0, "selects_linked": 0, "contains_linked": 0,
                "uses_linked": 0, "applies_during_linked": 0, "warnings": 0}

    stats = apply_bundle_wiring_plan(graph, plan, file_name, scaffold_map, cc_config=cc)
    logger.info(
        "bundle materialization: bundles=%s selects=%s contains=%s uses=%s applies_during=%s warnings=%s",
        stats["bundles_created"],
        stats["selects_linked"],
        stats["contains_linked"],
        stats["uses_linked"],
        stats["applies_during_linked"],
        stats["warnings"],
    )
    return stats
