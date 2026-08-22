"""Contract-driven ingest gates for passage sections, index hops, and spines.

This is ingest acceptance (did ``/extract`` write the contracted graph shape?),
not ADA chat smokes. Drive ids and index titles from
``passage-sections.json`` / ``operational-spines.json``. Fail closed.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from neo4j import Session

from src.index_materialization import (
    index_titles_for_section,
    maps_to_seed_labels,
    uses_table_names,
)
from src.ingest_manifest import load_passage_sections
from src.spine_materialization import load_operational_spines


def _load_spines(game: str) -> dict[str, Any]:
    load_operational_spines.cache_clear()
    return load_operational_spines(game)


def _load_sections(game: str) -> dict[str, Any]:
    load_passage_sections.cache_clear()
    return load_passage_sections(game)


@dataclass
class GateCheck:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class SectionGatesReport:
    game: str
    document: str
    phase: int
    column: str
    contract_version: str
    spines_version: str
    checks: list[GateCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ok"] = self.ok
        return payload


def unescape_heading_fragment(fragment: str) -> str:
    """Turn a heading_regex alternative into a plaintext needle."""
    s = fragment
    s = s.replace(r"\s*", " ")
    s = s.replace(r"\s+", " ")
    s = s.replace(r"\s", " ")
    s = s.replace(r"\(", "(").replace(r"\)", ")")
    s = s.replace(r"\?", "?").replace(r"\.", ".")
    s = s.replace(r"\+", "+")
    return " ".join(s.split())


def _first_alternation_inner(pattern: str) -> str | None:
    """Inner text of the first capturing group that contains ``|`` (escaped parens ok)."""
    i = 0
    n = len(pattern)
    while i < n:
        ch = pattern[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "(":
            if i + 1 < n and pattern[i + 1] == "?":
                i += 1
                continue
            depth = 1
            i += 1
            start = i
            while i < n and depth:
                if pattern[i] == "\\":
                    i += 2
                    continue
                if pattern[i] == "(":
                    depth += 1
                elif pattern[i] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            inner = pattern[start:i]
            if "|" in inner:
                return inner
        i += 1
    return None


def split_heading_needles(pattern: str) -> list[str]:
    """Plaintext heading needles from a ``passage_split`` heading_regex pattern."""
    if not pattern:
        return []
    inner = _first_alternation_inner(pattern)
    if inner:
        parts = []
        buf = []
        depth = 0
        j = 0
        while j < len(inner):
            if inner[j] == "\\":
                buf.append(inner[j : j + 2])
                j += 2
                continue
            if inner[j] == "(":
                depth += 1
                buf.append(inner[j])
                j += 1
                continue
            if inner[j] == ")":
                depth -= 1
                buf.append(inner[j])
                j += 1
                continue
            if inner[j] == "|" and depth == 0:
                needle = unescape_heading_fragment("".join(buf))
                if needle:
                    parts.append(needle)
                buf = []
                j += 1
                continue
            buf.append(inner[j])
            j += 1
        needle = unescape_heading_fragment("".join(buf))
        if needle:
            parts.append(needle)
        return parts
    stripped = re.sub(r"^\^\\s\*", "", pattern)
    stripped = re.sub(r"\\s\*\$\s*$", "", stripped)
    stripped = stripped.strip("^$")
    needle = unescape_heading_fragment(stripped)
    return [needle] if needle else []


def section_column(section: dict[str, Any]) -> str:
    return str(section.get("column") or "RULES")


def gated_sections(
    contract: dict[str, Any],
    *,
    phase: int,
    column: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for section in contract.get("sections") or []:
        sid = section.get("id")
        if not sid:
            continue
        if int(section.get("phase") or 99) > phase:
            continue
        if column.lower() != "all" and section_column(section) != column:
            continue
        out.append(section)
    return out


def spine_procedures(spine: dict[str, Any]) -> list[str]:
    multi = spine.get("for_procedures")
    if isinstance(multi, list) and multi:
        return [str(p) for p in multi if str(p).strip()]
    one = spine.get("for_procedure")
    return [str(one)] if one else []


def _chunk_for_section(session: Session, document: str, section_id: str) -> dict[str, Any] | None:
    row = session.run(
        """
        MATCH (c:Chunk {section_id: $sid})-[:PART_OF]->(:Document {fileName: $fn})
        WHERE coalesce(c.source_format, '') = 'passage-section'
        RETURN c.id AS id, size(coalesce(c.text, '')) AS chars
        ORDER BY c.id
        LIMIT 1
        """,
        {"sid": section_id, "fn": document},
    ).single()
    return dict(row) if row else None


def _passage_texts(session: Session, document: str, section_id: str) -> list[str]:
    rows = session.run(
        """
        MATCH (p:RulePassage {section_id: $sid})
        WHERE p.fileName = $fn OR p.id STARTS WITH $prefix
        RETURN coalesce(p.text, '') AS text
        ORDER BY p.passage_index, p.id
        """,
        {"sid": section_id, "fn": document, "prefix": f"{document}#"},
    )
    return [str(r["text"]) for r in rows]


def _orphan_section_ids(session: Session, document: str, known_ids: set[str]) -> list[str]:
    rows = session.run(
        """
        MATCH (c:Chunk)-[:PART_OF]->(:Document {fileName: $fn})
        WHERE coalesce(c.source_format, '') = 'passage-section'
          AND c.section_id IS NOT NULL
        RETURN DISTINCT c.section_id AS sid
        ORDER BY sid
        """,
        {"fn": document},
    )
    leftovers = []
    for row in rows:
        sid = str(row["sid"])
        if sid not in known_ids:
            leftovers.append(sid)
    return leftovers


def _index_map(
    session: Session,
    document: str,
    title: str,
    column: str,
) -> list[dict[str, Any]]:
    rows = session.run(
        """
        MATCH (e:IndexEntry {column: $column, title: $title})
        WHERE e.source = $fn OR e.id STARTS WITH $prefix
        OPTIONAL MATCH (e)-[:MAPS_TO_SECTION]->(c:Chunk)
        RETURN e.id AS entry_id, c.section_id AS section_id
        """,
        {
            "column": column,
            "title": title,
            "fn": document,
            "prefix": f"{document}#index:{column}:",
        },
    )
    return [dict(r) for r in rows]


_INDEX_ARRAYS = (
    ("rules_index", "RULES"),
    ("world_index", "THE_WORLD"),
    ("creatures_index", "CREATURES"),
)


def _seed_map(
    session: Session,
    document: str,
    title: str,
    column: str,
) -> list[str]:
    row = session.run(
        """
        MATCH (e:IndexEntry {column: $column, title: $title})
        WHERE e.source = $fn OR e.id STARTS WITH $prefix
        MATCH (e)-[:MAPS_TO_SEED]->(s:SeedNode)
        UNWIND [lbl IN labels(s) WHERE lbl <> 'SeedNode'] AS label
        RETURN collect(DISTINCT label) AS seed_labels
        """,
        {
            "column": column,
            "title": title,
            "fn": document,
            "prefix": f"{document}#index:{column}:",
        },
    ).single()
    if not row:
        return []
    return [str(x) for x in (row.get("seed_labels") or []) if x]


def _table_uses_map(
    session: Session,
    document: str,
    title: str,
    column: str,
) -> list[str]:
    row = session.run(
        """
        MATCH (e:IndexEntry {column: $column, title: $title})
        WHERE e.source = $fn OR e.id STARTS WITH $prefix
        MATCH (e)-[:USES]->(t:IngestNode)
        RETURN collect(DISTINCT coalesce(t.name, t.id)) AS tables
        """,
        {
            "column": column,
            "title": title,
            "fn": document,
            "prefix": f"{document}#index:{column}:",
        },
    ).single()
    if not row:
        return []
    return [str(x) for x in (row.get("tables") or []) if x]


def _spine_graph(session: Session, if_id: str) -> dict[str, Any]:
    row = session.run(
        """
        OPTIONAL MATCH (i:IngestNode:If {id: $if_id})
        OPTIONAL MATCH (i)-[:DOCUMENTED_BY]->(p:RulePassage)
        OPTIONAL MATCH (i)-[:FOR]->(proc:SeedNode)
        RETURN i.id AS if_id,
               collect(DISTINCT p.section_id) AS evidence_sections,
               collect(DISTINCT labels(proc)) AS proc_label_sets
        """,
        {"if_id": if_id},
    ).single()
    return dict(row) if row else {"if_id": None, "evidence_sections": [], "proc_label_sets": []}


def _append_place_relation_gates(
    session: Session,
    report: SectionGatesReport,
    *,
    game: str,
    document: str,
) -> None:
    from src.place_relation_materialization import load_place_relations

    load_place_relations.cache_clear()
    contract = load_place_relations(game)
    prefix = f"{document}#index:"
    for row in contract.get("part_of") or []:
        child = str(row.get("child_title") or "")
        parent = str(row.get("parent_title") or "")
        name = f"place-part-of:{child}->{parent}"
        rec = session.run(
            """
            MATCH (ce:IndexEntry {entry_kind: 'place'})-[:DENOTES]->(c)
            MATCH (pe:IndexEntry {entry_kind: 'place'})-[:DENOTES]->(p)
            WHERE (ce.source = $document OR ce.id STARTS WITH $prefix)
              AND (pe.source = $document OR pe.id STARTS WITH $prefix)
              AND toLower(ce.title) = toLower($child)
              AND toLower(pe.title) = toLower($parent)
            OPTIONAL MATCH (c)-[r:PART_OF]->(p)
            RETURN r IS NOT NULL AS ok
            """,
            {
                "document": document,
                "prefix": prefix,
                "child": child,
                "parent": parent,
            },
        ).single()
        ok = bool(rec and rec.get("ok"))
        report.checks.append(
            GateCheck(
                name=name,
                ok=ok,
                detail="PART_OF" if ok else "missing Place PART_OF Place",
            )
        )
    for row in contract.get("occurs_in_place") or []:
        faction = str(row.get("faction_title") or "")
        place = str(row.get("place_title") or "")
        name = f"faction-occurs-in:{faction}->{place}"
        rec = session.run(
            """
            MATCH (fe:IndexEntry {entry_kind: 'faction'})-[:DENOTES]->(f)
            MATCH (pe:IndexEntry {entry_kind: 'place'})-[:DENOTES]->(p)
            WHERE (fe.source = $document OR fe.id STARTS WITH $prefix)
              AND (pe.source = $document OR pe.id STARTS WITH $prefix)
              AND toLower(fe.title) = toLower($faction)
              AND toLower(pe.title) = toLower($place)
            OPTIONAL MATCH (f)-[r:OCCURS_IN]->(p)
            RETURN r IS NOT NULL AS ok
            """,
            {
                "document": document,
                "prefix": prefix,
                "faction": faction,
                "place": place,
            },
        ).single()
        ok = bool(rec and rec.get("ok"))
        report.checks.append(
            GateCheck(
                name=name,
                ok=ok,
                detail="OCCURS_IN Place" if ok else "missing Faction OCCURS_IN Place",
            )
        )


def run_section_gates(
    session: Session,
    *,
    game: str = "mork-borg",
    document: str = "mork-borg.pdf",
    phase: int = 2,
    column: str = "RULES",
) -> SectionGatesReport:
    contract = _load_sections(game)
    spines_contract = _load_spines(game)
    sections = gated_sections(contract, phase=phase, column=column)
    known_ids = {str(s["id"]) for s in (contract.get("sections") or []) if s.get("id")}

    report = SectionGatesReport(
        game=game,
        document=document,
        phase=phase,
        column=column,
        contract_version=str(contract.get("version") or ""),
        spines_version=str(spines_contract.get("version") or ""),
    )

    leftovers = _orphan_section_ids(session, document, known_ids)
    if leftovers:
        report.checks.append(
            GateCheck(
                name="orphans",
                ok=False,
                detail=(
                    "passage-section Chunk section_id not in contract: "
                    + ", ".join(leftovers)
                ),
            )
        )
    else:
        report.checks.append(
            GateCheck(
                name="orphans",
                ok=True,
                detail="no leftover passage-section ids",
            )
        )

    _append_place_relation_gates(
        session, report, game=game, document=document
    )

    for section in sections:
        sid = str(section["id"])
        chunk = _chunk_for_section(session, document, sid)
        if not chunk:
            report.checks.append(
                GateCheck(
                    name=f"chunk:{sid}",
                    ok=False,
                    detail="no passage-section Chunk",
                )
            )
            continue
        chars = int(chunk.get("chars") or 0)
        if chars <= 0:
            report.checks.append(
                GateCheck(
                    name=f"chunk:{sid}",
                    ok=False,
                    detail="passage-section Chunk has empty text",
                )
            )
        else:
            report.checks.append(
                GateCheck(
                    name=f"chunk:{sid}",
                    ok=True,
                    detail=f"chars={chars}",
                )
            )

        if not section.get("extract_rule_passages", True):
            continue

        texts = _passage_texts(session, document, sid)
        if not texts:
            report.checks.append(
                GateCheck(
                    name=f"passages:{sid}",
                    ok=False,
                    detail="no RulePassage for section",
                )
            )
        else:
            report.checks.append(
                GateCheck(
                    name=f"passages:{sid}",
                    ok=True,
                    detail=f"n={len(texts)}",
                )
            )

        split = section.get("passage_split") or {}
        if section.get("passage_granularity") == "subheading_regex" and split.get("pattern"):
            needles = split_heading_needles(str(split["pattern"]))
            blob = "\n".join(texts).lower()
            missing = [n for n in needles if n.lower() not in blob]
            if missing:
                report.checks.append(
                    GateCheck(
                        name=f"split:{sid}",
                        ok=False,
                        detail="RulePassage text missing split heads: "
                        + ", ".join(missing),
                    )
                )
            else:
                report.checks.append(
                    GateCheck(
                        name=f"split:{sid}",
                        ok=True,
                        detail="needles=" + ", ".join(needles),
                    )
                )

        idx_column = section_column(section)
        for title in index_titles_for_section(section):
            rows = _index_map(session, document, title, idx_column)
            if not rows:
                report.checks.append(
                    GateCheck(
                        name=f"index:{sid}:{title}",
                        ok=False,
                        detail=f"no {idx_column} IndexEntry title={title!r}",
                    )
                )
                continue
            mapped = [r.get("section_id") for r in rows if r.get("section_id")]
            if not mapped:
                report.checks.append(
                    GateCheck(
                        name=f"index:{sid}:{title}",
                        ok=False,
                        detail=f"IndexEntry {title!r} has no MAPS_TO_SECTION",
                    )
                )
                continue
            wrong = [m for m in mapped if m != sid]
            if wrong:
                report.checks.append(
                    GateCheck(
                        name=f"index:{sid}:{title}",
                        ok=False,
                        detail=(
                            f"IndexEntry {title!r} MAPS_TO_SECTION "
                            f"{wrong[0]!r}, expected {sid!r}"
                        ),
                    )
                )
            else:
                report.checks.append(
                    GateCheck(
                        name=f"index:{sid}:{title}",
                        ok=True,
                        detail=f"MAPS_TO_SECTION {sid}",
                    )
                )

    index_source = contract.get("index_source") or {}
    for array_key, idx_col in _INDEX_ARRAYS:
        if column.lower() != "all" and idx_col != column:
            continue
        for item in index_source.get(array_key) or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            contracted = maps_to_seed_labels(item)
            contracted_tables = uses_table_names(item)
            if not contracted and not contracted_tables:
                continue
            entries = _index_map(session, document, title, idx_col)
            if contracted:
                check_name = f"maps_to_seed:{idx_col}:{title}"
                if not entries:
                    report.checks.append(
                        GateCheck(
                            name=check_name,
                            ok=False,
                            detail=f"no {idx_col} IndexEntry title={title!r}",
                        )
                    )
                else:
                    present = set(_seed_map(session, document, title, idx_col))
                    missing = [lab for lab in contracted if lab not in present]
                    if missing:
                        report.checks.append(
                            GateCheck(
                                name=check_name,
                                ok=False,
                                detail=(
                                    f"IndexEntry {title!r} missing MAPS_TO_SEED "
                                    + ", ".join(missing)
                                ),
                            )
                        )
                    else:
                        report.checks.append(
                            GateCheck(
                                name=check_name,
                                ok=True,
                                detail="MAPS_TO_SEED " + ", ".join(contracted),
                            )
                        )
            if contracted_tables:
                table_check = f"uses_tables:{idx_col}:{title}"
                if not entries:
                    report.checks.append(
                        GateCheck(
                            name=table_check,
                            ok=False,
                            detail=f"no {idx_col} IndexEntry title={title!r}",
                        )
                    )
                else:
                    present_tables = set(
                        _table_uses_map(session, document, title, idx_col)
                    )
                    missing_tables = [
                        name
                        for name in contracted_tables
                        if name not in present_tables
                    ]
                    if missing_tables:
                        report.checks.append(
                            GateCheck(
                                name=table_check,
                                ok=False,
                                detail=(
                                    f"IndexEntry {title!r} missing USES "
                                    + ", ".join(missing_tables)
                                ),
                            )
                        )
                    else:
                        report.checks.append(
                            GateCheck(
                                name=table_check,
                                ok=True,
                                detail="USES " + ", ".join(contracted_tables),
                            )
                        )

    for spine in spines_contract.get("spines") or []:
        if_id = str(spine.get("id") or "")
        ev = spine.get("evidence") or {}
        expected_sid = ev.get("section_id")
        if not if_id or not expected_sid:
            continue
        graph = _spine_graph(session, if_id)
        if not graph.get("if_id"):
            report.checks.append(
                GateCheck(
                    name=f"spine:{if_id}",
                    ok=False,
                    detail="If node missing",
                )
            )
            continue
        evidence_sids = [s for s in (graph.get("evidence_sections") or []) if s]
        if expected_sid not in evidence_sids:
            actual = ",".join(str(s) for s in evidence_sids) or "(none)"
            report.checks.append(
                GateCheck(
                    name=f"spine:{if_id}",
                    ok=False,
                    detail=(
                        f"DOCUMENTED_BY section_id={actual}, "
                        f"expected {expected_sid}"
                    ),
                )
            )
            continue
        missing_procs: list[str] = []
        label_sets = graph.get("proc_label_sets") or []
        flat_labels = set()
        for labset in label_sets:
            if labset:
                flat_labels.update(labset)
        for proc in spine_procedures(spine):
            if proc not in flat_labels:
                missing_procs.append(proc)
        if missing_procs:
            report.checks.append(
                GateCheck(
                    name=f"spine:{if_id}",
                    ok=False,
                    detail="FOR missing " + ", ".join(missing_procs),
                )
            )
        else:
            report.checks.append(
                GateCheck(
                    name=f"spine:{if_id}",
                    ok=True,
                    detail=f"DOCUMENTED_BY {expected_sid}",
                )
            )

    return report


def format_report_text(report: SectionGatesReport, *, verbose: bool = False) -> str:
    lines = [
        "=== Section ingest gates ===",
        "",
        f"game={report.game} document={report.document} "
        f"phase<={report.phase} column={report.column}",
        f"passage-sections {report.contract_version}, "
        f"operational-spines {report.spines_version}",
        "",
    ]
    failed = [c for c in report.checks if not c.ok]
    passed = [c for c in report.checks if c.ok]
    lines.append(f"checks: {len(passed)}/{len(report.checks)} OK")
    if failed:
        lines.append("")
        lines.append("Failures:")
        for check in failed:
            lines.append(f"  - {check.name}: {check.detail}")
    if verbose:
        lines.append("")
        lines.append("--- All checks ---")
        for check in report.checks:
            status = "OK" if check.ok else "FAIL"
            lines.append(f"  [{status}] {check.name}: {check.detail}")
    lines.append("")
    lines.append("PASS" if report.ok else "FAIL")
    return "\n".join(lines)
