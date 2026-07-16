# Roadmap (pdf-graph-builder / Mörk Borg ingest)

Operational backlog for scaffold-diff ingest and lookup-table materialization. Not a release schedule.

---

## Planned

### Ingest coverage reporter (`check_coverage.py`)

Single CLI summary of how complete an ingest is — replacing ad-hoc spot checks (`check_gaps.py`, `verify_phase1.py`, `verify_phase2.py`, manual Cypher).

**Checklist sources:**

| Dimension | Source of truth |
|---|---|
| Lookup tables materialized | `games/<game>/ingest-manifest.json` → `lookup_tables[]` (`pdf_extract.status` in `verified` / `partial`; row counts vs `min_rows` / `acceptance_rows`) |
| Optional-class bundles | Manifest `character_creation` + `games/<game>/hand-authored-overrides/optional-classes.json` (`SELECTS`, `CONTAINS`, `APPLIES_DURING`) |
| Scaffold seed coverage | Live Neo4j `:SeedNode` count and `coverage` (`research-only` vs `ingest-confirmed`) |
| Review queue | `FlaggedConcept`, `FlaggedRelationship`, `OVERRIDES_SEED` / `POSSIBLE_OVERRIDES_SEED` counts |
| Phase 1 prose extract | Briefing 4 criteria (`RulePassage`, `AbilityTest`, `DRTable` wiring) — optional hard-coded phase block |

**Example output (target):**

```
Seeds:     48/54 ingest-confirmed
Tables:    47/51 materialized (4 missing: …)
Bundles:   6/6 wired
Flags:     2 open (1 NEW_NODE, 1 POSSIBLE_OVERRIDES_SEED)
Phase 1:   DRTable OK, RulePassage 0
```

Interim: Bloom perspective `docs/bloom-scaffold-diff-perspective.json` for visual seed coverage; manifest `status` fields for authoring-time contracts only.

---

## Done (recent)

- Unified lookup-table pipeline (`run_lookup_table_pipeline`)
- Complete `--cleanup` on full PDF re-ingest (chunks + document)

---

## References

- [ingest-manifest-sync.md](./ingest-manifest-sync.md) — manifest as Tier-5 contract
- [pdf-graph-builder-briefing-4.md](./pdf-graph-builder-briefing-4.md) — Phase 1 verification queries
- [AGENTS.md](../AGENTS.md) — table delivery workflow
