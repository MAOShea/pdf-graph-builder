"""Generic leaf typing: IngestNode INSTANCE_OF one SeedNode (+ optional DENOTES).

Used by fiction catalog faces and by lookup-table ``row_typing`` config.
Identity is stable ``{file}#entity:{kind}:{slug(name)}`` so multiple faces
(index entries or table rows) can DENOTES the same instance.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Callable

from src.shared.common_fn import execute_graph_query

logger = logging.getLogger(__name__)

_DIE = re.compile(r"(?P<die>(?:\d+)?d\d+)\b", re.IGNORECASE)
_AMMO_PREFIX = re.compile(
    r"^(?:(?:\d+\s+)?(?:bolts|arrows)|(?:bolts|arrows)\s+\d+)\s+",
    re.IGNORECASE,
)
_TIER = re.compile(r"tier\s+(\d+)", re.IGNORECASE)


def slug_title(title: str) -> str:
    """Lowercase slug for stable ids — strip diacritics/punct, hyphenate."""
    text = unicodedata.normalize("NFKD", title or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "untitled"


def normalize_name_key(name: str) -> str:
    """Identity key across tables: lowercase, no diacritics, collapsed space."""
    s = unicodedata.normalize("NFKD", (name or "").strip())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def entity_id(file_name: str, entity_kind: str, display_name: str) -> str:
    key = normalize_name_key(display_name) or display_name
    return f"{file_name}#entity:{entity_kind}:{slug_title(key)}"


def attach_typed_instance(
    graph,
    *,
    file_name: str,
    entity_kind: str,
    display_name: str,
    seed_label: str,
    denotes_from_id: str | None = None,
    extra_props: dict[str, Any] | None = None,
) -> str:
    """MERGE typed IngestNode; leaf INSTANCE_OF; optional face-[:DENOTES]->entity."""
    node_id = entity_id(file_name, entity_kind, display_name)
    props: dict[str, Any] = {
        "id": node_id,
        "name": display_name,
        "tier": 5,
        "source": file_name,
        "normalized_name": normalize_name_key(display_name),
        "entity_kind": entity_kind,
    }
    if extra_props:
        for k, v in extra_props.items():
            if v is not None:
                props[k] = v

    execute_graph_query(
        graph,
        """
        MERGE (entity:IngestNode {id: $entity_id})
        ON CREATE SET entity += $props
        ON MATCH SET
          entity.damage = coalesce(entity.damage, $props.damage),
          entity.armor_tier = coalesce(entity.armor_tier, $props.armor_tier),
          entity.normalized_name = coalesce(entity.normalized_name, $props.normalized_name),
          entity.entity_kind = coalesce(entity.entity_kind, $props.entity_kind)
        WITH entity
        OPTIONAL MATCH (entity)-[old:INSTANCE_OF]->(:SeedNode)
        DELETE old
        WITH entity
        MATCH (seed:SeedNode)
        WHERE $seed_label IN labels(seed) OR seed.name = $seed_label
        WITH entity, seed
        LIMIT 1
        MERGE (entity)-[:INSTANCE_OF]->(seed)
        """,
        {
            "entity_id": node_id,
            "props": props,
            "seed_label": seed_label,
        },
    )

    if denotes_from_id:
        execute_graph_query(
            graph,
            """
            MATCH (entity:IngestNode {id: $entity_id})
            MATCH (face:IngestNode {id: $face_id})
            MERGE (face)-[:DENOTES]->(entity)
            """,
            {"entity_id": node_id, "face_id": denotes_from_id},
        )

    return node_id


# --- row_typing name / prop strategies (manifest-selected) -----------------

def _cell(cells: dict[str, Any], column: str) -> str:
    return str(cells.get(column) or "").strip()


def _strategy_plain(cells: dict[str, Any], column: str, _cfg: dict) -> Any:
    text = _cell(cells, column)
    return text or None


def _strategy_text_before_die(cells: dict[str, Any], column: str, _cfg: dict) -> Any:
    text = _cell(cells, column)
    if not text:
        return None
    m = _DIE.search(text)
    if not m:
        return None
    before = text[: m.start()].strip(" ,;")
    before = _AMMO_PREFIX.sub("", before).strip()
    # PDF sometimes yields "10 Zweihänder d10" (count without bolts/arrows word)
    before = re.sub(r"^\d+\s+", "", before).strip()
    before = before.split(",")[0].strip()
    return before or None


def _strategy_text_before_paren(cells: dict[str, Any], column: str, _cfg: dict) -> Any:
    text = _cell(cells, column)
    if not text:
        return None
    head = re.split(r"\s*\(", text, maxsplit=1)[0].strip()
    return head or None


def _strategy_first_die(cells: dict[str, Any], column: str, _cfg: dict) -> Any:
    text = _cell(cells, column)
    if not text:
        return None
    m = _DIE.search(text)
    if not m:
        return None
    return m.group("die").lower().replace(" ", "")


def _strategy_tier_in_text(cells: dict[str, Any], column: str, _cfg: dict) -> Any:
    text = _cell(cells, column)
    if not text:
        return None
    m = _TIER.search(text)
    return int(m.group(1)) if m else None


_STRATEGIES: dict[str, Callable[[dict[str, Any], str, dict], Any]] = {
    "plain": _strategy_plain,
    "text_before_die": _strategy_text_before_die,
    "text_before_paren": _strategy_text_before_paren,
    "first_die": _strategy_first_die,
    "tier_in_text": _strategy_tier_in_text,
}


def resolve_field(cells: dict[str, Any], field_cfg: dict[str, Any] | None) -> Any:
    """Resolve a ``row_typing`` name/props field config against a row's cells."""
    if not field_cfg or not isinstance(field_cfg, dict):
        return None
    column = str(field_cfg.get("column") or "").strip()
    strategy = str(field_cfg.get("strategy") or "plain").strip()
    if not column:
        return None
    fn = _STRATEGIES.get(strategy)
    if fn is None:
        logger.warning("typed_instance: unknown strategy %r — skipped", strategy)
        return None
    return fn(cells, column, field_cfg)


def _cell_matches_rule(cells: dict[str, Any], rule: dict[str, Any]) -> bool:
    """One ``match_when`` / include rule against a row's cells."""
    column = str(rule.get("column") or "").strip()
    if not column:
        return False
    raw = cells.get(column)
    text = "" if raw is None else str(raw).strip()

    if "in" in rule:
        allowed = rule.get("in") or []
        if not isinstance(allowed, list):
            return False
        # Face indices may be int in JSON or string from PDF parse.
        norm_allowed = {str(x).strip() for x in allowed}
        if text in norm_allowed:
            return True
        try:
            if str(int(float(text))) in {str(int(float(str(x)))) for x in allowed}:
                return True
        except (TypeError, ValueError):
            pass
        return False

    contains = rule.get("contains")
    if contains is not None:
        return str(contains).lower() in text.lower()

    pattern = rule.get("regex")
    if pattern is not None:
        try:
            return re.search(str(pattern), text, re.IGNORECASE) is not None
        except re.error:
            logger.warning("typed_instance: bad match_when regex %r", pattern)
            return False

    return False


def skip_row(cells: dict[str, Any], row_typing: dict[str, Any]) -> bool:
    """True when this row should not become a typed instance.

    - ``skip_when``: any matching rule → skip (e.g. empty damage = ammo).
    - ``match_when``: if present, skip unless **any** rule matches (selective
      faces on a heterogeneous table — DESIGN §4.7 starting d12 beasts).
    """
    for rule in row_typing.get("skip_when") or []:
        if not isinstance(rule, dict):
            continue
        column = str(rule.get("column") or "").strip()
        if not column:
            continue
        raw = cells.get(column)
        empty = raw is None or (isinstance(raw, str) and not raw.strip())
        if rule.get("empty") and empty:
            return True

    match_when = row_typing.get("match_when")
    if match_when:
        rules = [r for r in match_when if isinstance(r, dict)]
        if not rules:
            return True
        if not any(_cell_matches_rule(cells, r) for r in rules):
            return True
    return False


def apply_row_typing(
    graph,
    *,
    file_name: str,
    cells: dict[str, Any],
    row_id: str,
    row_typing: dict[str, Any],
    scaffold_seed_ok: Callable[[str], bool] | None = None,
) -> str | None:
    """If ``row_typing`` applies, attach leaf instance and DENOTES from the row.

    Returns entity id, or None when skipped / misconfigured.
    """
    if not row_typing:
        return None
    seed_label = str(row_typing.get("instance_of") or "").strip()
    entity_kind = str(row_typing.get("entity_kind") or "").strip()
    if not seed_label or not entity_kind:
        logger.warning(
            "typed_instance: row_typing needs instance_of + entity_kind (row %s)",
            row_id,
        )
        return None
    if scaffold_seed_ok is not None and not scaffold_seed_ok(seed_label):
        logger.warning(
            "typed_instance: SeedNode %r missing — skip typing for %s",
            seed_label,
            row_id,
        )
        return None
    if skip_row(cells, row_typing):
        return None

    name_cfg = row_typing.get("name")
    if not isinstance(name_cfg, dict):
        name_cfg = {
            "column": str(row_typing.get("name_column") or "").strip(),
            "strategy": str(row_typing.get("name_strategy") or "plain"),
        }
    display_name = resolve_field(cells, name_cfg)
    if not display_name or not isinstance(display_name, str):
        logger.warning(
            "typed_instance: could not resolve name for %s cells=%r",
            row_id,
            cells,
        )
        return None

    extra: dict[str, Any] = {}
    for prop_name, prop_cfg in (row_typing.get("props") or {}).items():
        if not isinstance(prop_cfg, dict):
            continue
        val = resolve_field(cells, prop_cfg)
        if val is not None:
            extra[str(prop_name)] = val

    entity_id = attach_typed_instance(
        graph,
        file_name=file_name,
        entity_kind=entity_kind,
        display_name=display_name,
        seed_label=seed_label,
        denotes_from_id=row_id,
        extra_props=extra or None,
    )
    sheet_from = row_typing.get("sheet_from")
    if entity_id and isinstance(sheet_from, dict):
        _apply_sheet_from(
            graph, entity_id=entity_id, cells=cells, sheet_from=sheet_from
        )
    return entity_id


def _apply_sheet_from(
    graph,
    *,
    entity_id: str,
    cells: dict[str, Any],
    sheet_from: dict[str, Any],
) -> None:
    """Optional compact sheet parse from a cell (starting beasts — DESIGN §4.7)."""
    from src.creature_sheet_materialization import (
        attach_combatant_sheet_slots,
        parse_paren_hp_attack,
    )

    column = str(sheet_from.get("column") or "").strip()
    strategy = str(sheet_from.get("strategy") or "").strip()
    if not column or not strategy:
        return
    text = _cell(cells, column)
    if not text:
        return
    parsed = None
    if strategy == "paren_hp_attack":
        parsed = parse_paren_hp_attack(text)
    else:
        logger.warning("typed_instance: unknown sheet_from strategy %r", strategy)
        return
    if not parsed:
        return
    n = attach_combatant_sheet_slots(graph, entity_id, parsed)
    if n:
        logger.debug(
            "typed_instance: attached %s sheet slot(s) on %s", n, entity_id
        )
