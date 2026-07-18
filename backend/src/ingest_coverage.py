"""Manifest-driven ingest coverage report (Neo4j vs ingest contract)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from neo4j import Session

from src.bundle_materialization import build_character_creation_wiring, load_bundles_schema
from src.hand_authored_tables import hand_authored_specs, skip_pdf_extract
from src.ingest_manifest import column_names, load_ingest_manifest
from src.pdf_table_parser import page_span

_MATERIALIZABLE_PDF_STATUSES = frozenset({"verified", "partial"})


@dataclass
class TableCheck:
    name: str
    phase: int | None
    expected_rows: int | None
    actual_rows: int
    ok: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class BundleCheck:
    bundles_expected: int
    bundles_found: int
    selects_expected: int
    selects_found: int
    contains_expected: int
    contains_found: int
    applies_during_expected: int
    applies_during_found: int
    uses_expected: int
    uses_found: int
    ok: bool
    missing_bundles: list[str] = field(default_factory=list)


@dataclass
class Phase1Check:
    dr_table_rows: int
    dr_applies_to: str | None
    rule_passage_count: int
    ability_test_count: int
    ok: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class CoverageReport:
    game: str
    document: str
    seeds_total: int
    seeds_ingest_confirmed: int
    seeds_research_only: int
    seeds_operator_verified: int
    tables_expected: int
    tables_ok: int
    table_checks: list[TableCheck]
    bundles: BundleCheck | None
    flags: dict[str, int]
    phase1: Phase1Check
    chunks: dict[str, Any]
    ok: bool
    summary_lines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def expected_materialized_specs(manifest: dict[str, Any], *, game: str) -> list[dict[str, Any]]:
    """Tables the unified pipeline should materialize (manifest contract)."""
    hand_names = {s["name"] for s in hand_authored_specs(game) if s.get("name")}
    seen: set[str] = set()
    specs: list[dict[str, Any]] = []

    for spec in manifest.get("lookup_tables") or []:
        name = spec.get("name")
        if not name or name in seen:
            continue
        pdf_status = (spec.get("pdf_extract") or {}).get("status")
        if name in hand_names:
            seen.add(name)
            specs.append(spec)
            continue
        if skip_pdf_extract(spec):
            continue
        if pdf_status not in _MATERIALIZABLE_PDF_STATUSES:
            continue
        if not page_span(spec):
            continue
        seen.add(name)
        specs.append(spec)

    return sorted(specs, key=lambda s: (s.get("phase") or 99, s.get("name") or ""))


def expected_row_count(spec: dict[str, Any]) -> int | None:
    if skip_pdf_extract(spec):
        return None
    pdf = spec.get("pdf_extract") or {}
    min_rows = pdf.get("min_rows")
    max_rows = pdf.get("max_rows")
    if min_rows is not None and max_rows is not None and min_rows == max_rows:
        return int(min_rows)
    if min_rows is not None:
        return int(min_rows)
    index = pdf.get("index") or {}
    values = index.get("values")
    if isinstance(values, list) and values:
        return len(values)
    acceptance = spec.get("acceptance_rows") or []
    if acceptance:
        return len(acceptance)
    return None


def _normalize_cell(value: Any) -> str:
    return str(value).strip().lower()


def _acceptance_issues(spec: dict[str, Any], rows_by_index: dict[str, dict[str, Any]]) -> list[str]:
    cols = column_names(spec)
    if not cols:
        return []
    index_col = cols[0]
    issues: list[str] = []
    for expected in spec.get("acceptance_rows") or []:
        exp_cells = expected.get("cells") or {}
        key = str(exp_cells.get(index_col))
        if key not in rows_by_index:
            issues.append(f"acceptance row {key} missing")
            continue
        got = rows_by_index[key]
        for col, exp_val in exp_cells.items():
            if col == index_col:
                continue
            if _normalize_cell(got.get(col)) != _normalize_cell(exp_val):
                issues.append(f"acceptance row {key} column {col!r} mismatch")
    return issues


def _fetch_table_rows(session: Session, name: str) -> tuple[int, dict[str, dict[str, Any]]]:
    record = session.run(
        """
        MATCH (t:IngestNode {name: $name})
        OPTIONAL MATCH (t)-[:HAS_ENTRY]->(r:TableEntry)
        RETURN count(r) AS row_count,
               collect(r.cells) AS cells_json
        """,
        {"name": name},
    ).single()
    if not record or record["row_count"] == 0:
        exists = session.run(
            "MATCH (t:IngestNode {name: $name}) RETURN count(t) AS c", {"name": name}
        ).single()["c"]
        if not exists:
            return 0, {}
        return 0, {}

    rows_by_index: dict[str, dict[str, Any]] = {}
    cols = None
    for raw in record["cells_json"] or []:
        if raw is None:
            continue
        cells = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(cells, dict):
            continue
        if cols is None:
            cols = list(cells.keys())
        index_key = str(cells.get(cols[0], "")) if cols else "0"
        rows_by_index[index_key] = cells
    return int(record["row_count"]), rows_by_index


def _check_tables(
    session: Session,
    specs: list[dict[str, Any]],
    *,
    validate_acceptance: bool,
    phase: int | None,
) -> list[TableCheck]:
    checks: list[TableCheck] = []
    for spec in specs:
        if phase is not None and spec.get("phase") != phase:
            continue
        name = spec["name"]
        expected = expected_row_count(spec)
        actual, rows_by_index = _fetch_table_rows(session, name)
        issues: list[str] = []
        if actual == 0:
            issues.append("not materialized or zero rows")
        elif expected is not None and actual < expected:
            issues.append(f"row count {actual} < expected {expected}")
        if validate_acceptance and rows_by_index:
            issues.extend(_acceptance_issues(spec, rows_by_index))
        ok = not issues
        checks.append(
            TableCheck(
                name=name,
                phase=spec.get("phase"),
                expected_rows=expected,
                actual_rows=actual,
                ok=ok,
                issues=issues,
            )
        )
    return checks


def _check_seeds(session: Session) -> dict[str, int]:
    rows = session.run(
        """
        MATCH (n:SeedNode)
        WHERE n.tier IS NOT NULL OR n.seed_id IS NOT NULL
        RETURN coalesce(n.coverage, 'research-only') AS coverage, count(*) AS c
        """
    )
    totals = {"total": 0, "ingest-confirmed": 0, "research-only": 0, "operator-verified": 0}
    for row in rows:
        cov = row["coverage"]
        count = int(row["c"])
        totals["total"] += count
        if cov in totals:
            totals[cov] += count
        else:
            totals[cov] = count
    return totals


def _check_flags(session: Session) -> dict[str, int]:
    return {
        "FlaggedConcept": session.run(
            "MATCH (n:FlaggedConcept) RETURN count(n) AS c"
        ).single()["c"],
        "FlaggedRelationship": session.run(
            "MATCH (n:FlaggedRelationship) RETURN count(n) AS c"
        ).single()["c"],
        "OVERRIDES_SEED": session.run(
            "MATCH ()-[r:OVERRIDES_SEED]->() RETURN count(r) AS c"
        ).single()["c"],
        "POSSIBLE_OVERRIDES_SEED": session.run(
            "MATCH ()-[r:POSSIBLE_OVERRIDES_SEED]->() RETURN count(r) AS c"
        ).single()["c"],
        "NEW_NODE": session.run(
            "MATCH (f:FlaggedConcept {signal: 'NEW_NODE'}) RETURN count(f) AS c"
        ).single()["c"],
    }


def _check_bundles(session: Session, manifest: dict[str, Any], game: str) -> BundleCheck | None:
    bundles_data = load_bundles_schema(game)
    if not bundles_data:
        return None
    plan = build_character_creation_wiring(manifest, bundles_data)
    if not plan:
        return None

    expected_ids = [b["id"] for b in plan.bundles if b.get("id")]
    found_ids = [
        r["id"]
        for r in session.run(
            """
            MATCH (b:OptionalClass:IngestNode)
            RETURN DISTINCT coalesce(b.id, b.name) AS id ORDER BY id
            """
        )
    ]
    missing = sorted(set(expected_ids) - set(found_ids))

    selects_found = session.run(
        "MATCH (:TableEntry)-[:SELECTS]->(:IngestNode) RETURN count(*) AS c"
    ).single()["c"]
    contains_found = session.run(
        "MATCH (:IngestNode)-[:CONTAINS]->(:IngestNode) RETURN count(*) AS c"
    ).single()["c"]
    applies_found = session.run(
        "MATCH (:IngestNode)-[:APPLIES_DURING]->() RETURN count(*) AS c"
    ).single()["c"]
    uses_found = session.run(
        "MATCH (:IngestNode)-[:USES]->(:IngestNode) RETURN count(*) AS c"
    ).single()["c"]

    ok = (
        len(found_ids) >= len(expected_ids)
        and not missing
        and selects_found >= len(plan.selects)
        and contains_found >= len(plan.contains)
        and applies_found >= len(plan.applies_during_links)
        and uses_found >= len(plan.uses)
    )
    return BundleCheck(
        bundles_expected=len(expected_ids),
        bundles_found=len(found_ids),
        selects_expected=len(plan.selects),
        selects_found=int(selects_found),
        contains_expected=len(plan.contains),
        contains_found=int(contains_found),
        applies_during_expected=len(plan.applies_during_links),
        applies_during_found=int(applies_found),
        uses_expected=len(plan.uses),
        uses_found=int(uses_found),
        ok=ok,
        missing_bundles=missing,
    )


def _check_phase1(session: Session) -> Phase1Check:
    dr = session.run(
        """
        MATCH (t:DRTable:IngestNode)
        OPTIONAL MATCH (t)-[:HAS_ENTRY]->(r:TableEntry)
        WITH t, count(r) AS rows
        OPTIONAL MATCH (t)-[:APPLIES_TO]->(dr)
        RETURN rows, dr.name AS applies_to
        ORDER BY rows DESC
        LIMIT 1
        """
    ).single()
    dr_rows = int(dr["rows"]) if dr else 0
    dr_applies = dr["applies_to"] if dr else None

    rule_passages = session.run("MATCH (n:RulePassage) RETURN count(n) AS c").single()["c"]
    ability_tests = session.run(
        "MATCH (n:AbilityTest) RETURN count(n) AS c"
    ).single()["c"]

    issues: list[str] = []
    if dr_rows < 7:
        issues.append(f"DRTable has {dr_rows} rows (expected >=7)")
    if not dr_applies:
        issues.append("DRTable missing APPLIES_TO")
    if int(rule_passages) == 0:
        issues.append("no RulePassage nodes (Phase 1 LLM extract)")

    return Phase1Check(
        dr_table_rows=dr_rows,
        dr_applies_to=dr_applies,
        rule_passage_count=int(rule_passages),
        ability_test_count=int(ability_tests),
        ok=dr_rows >= 7 and bool(dr_applies),
        issues=issues,
    )


def _check_chunks(session: Session, document: str) -> dict[str, Any]:
    row = session.run(
        """
        MATCH (c:Chunk)-[:PART_OF|FIRST_CHUNK]->(:Document {fileName: $fn})
        RETURN count(c) AS n, min(c.page_number) AS min_p, max(c.page_number) AS max_p
        """,
        {"fn": document},
    ).single()
    if not row:
        return {"count": 0, "min_page": None, "max_page": None}
    return {
        "count": int(row["n"]),
        "min_page": row["min_p"],
        "max_page": row["max_p"],
    }


def _build_summary(report: CoverageReport) -> list[str]:
    lines = [
        f"Seeds:     {report.seeds_ingest_confirmed}/{report.seeds_total} ingest-confirmed"
        f" ({report.seeds_research_only} research-only)",
        f"Tables:    {report.tables_ok}/{report.tables_expected} OK",
    ]
    if report.bundles:
        b = report.bundles
        lines.append(
            f"Bundles:   {b.bundles_found}/{b.bundles_expected} "
            f"(SELECTS {b.selects_found}/{b.selects_expected}, "
            f"CONTAINS {b.contains_found}/{b.contains_expected})"
        )
    flag_total = sum(report.flags.values())
    lines.append(f"Flags:     {flag_total} open ({report.flags})")
    p1 = report.phase1
    lines.append(
        f"Phase 1:   DRTable {p1.dr_table_rows} rows"
        f"{f' -> {p1.dr_applies_to}' if p1.dr_applies_to else ''}, "
        f"RulePassage {p1.rule_passage_count}, AbilityTest {p1.ability_test_count}"
    )
    ch = report.chunks
    lines.append(
        f"Chunks:    {ch['count']} "
        f"(pages {ch.get('min_page')}-{ch.get('max_page')})"
    )
    return lines


def run_coverage_report(
    session: Session,
    *,
    game: str = "mork-borg",
    document: str = "mork-borg.pdf",
    validate_acceptance: bool = False,
    phase: int | None = None,
    include_bundles: bool = True,
) -> CoverageReport:
    manifest = load_ingest_manifest(game)
    manifest["game"] = game
    specs = expected_materialized_specs(manifest, game=game)

    table_checks = _check_tables(
        session, specs, validate_acceptance=validate_acceptance, phase=phase
    )
    seeds = _check_seeds(session)
    flags = _check_flags(session)
    bundles = _check_bundles(session, manifest, game) if include_bundles else None
    phase1 = _check_phase1(session)
    chunks = _check_chunks(session, document)

    tables_ok = sum(1 for t in table_checks if t.ok)
    ok = (
        tables_ok == len(table_checks)
        and (bundles.ok if bundles else True)
        and phase1.ok
    )

    report = CoverageReport(
        game=game,
        document=document,
        seeds_total=seeds["total"],
        seeds_ingest_confirmed=seeds.get("ingest-confirmed", 0),
        seeds_research_only=seeds.get("research-only", 0),
        seeds_operator_verified=seeds.get("operator-verified", 0),
        tables_expected=len(table_checks),
        tables_ok=tables_ok,
        table_checks=table_checks,
        bundles=bundles,
        flags=flags,
        phase1=phase1,
        chunks=chunks,
        ok=ok,
    )
    report.summary_lines = _build_summary(report)
    return report


def format_report_text(report: CoverageReport, *, verbose: bool = False) -> str:
    lines = ["=== Ingest coverage ===", ""]
    lines.extend(report.summary_lines)
    if not verbose:
        failed = [t for t in report.table_checks if not t.ok]
        if failed:
            lines.append("")
            lines.append("Missing / failed tables:")
            for t in failed:
                detail = "; ".join(t.issues) if t.issues else "failed"
                exp = f" (expected >={t.expected_rows})" if t.expected_rows else ""
                lines.append(f"  - {t.name}: {t.actual_rows} rows{exp} — {detail}")
        if report.bundles and not report.bundles.ok:
            lines.append("")
            lines.append("Bundle issues:")
            if report.bundles.missing_bundles:
                lines.append(f"  missing: {', '.join(report.bundles.missing_bundles)}")
        if report.phase1.issues:
            lines.append("")
            lines.append("Phase 1 notes:")
            for issue in report.phase1.issues:
                lines.append(f"  - {issue}")
        lines.append("")
        lines.append("PASS" if report.ok else "FAIL")
        return "\n".join(lines)

    lines.append("")
    lines.append("--- Tables ---")
    for t in report.table_checks:
        status = "OK" if t.ok else "FAIL"
        exp = f"/>={t.expected_rows}" if t.expected_rows else ""
        lines.append(f"  [{status}] phase={t.phase} {t.name}: {t.actual_rows}{exp} rows")
        for issue in t.issues:
            lines.append(f"         {issue}")
    lines.append("")
    lines.append("PASS" if report.ok else "FAIL")
    return "\n".join(lines)
