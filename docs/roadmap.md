# Roadmap (pdf-graph-builder / Mörk Borg ingest)

Operational backlog for scaffold-diff ingest and lookup-table materialization. Not a release schedule.

---

## Done (recent)

- **Section-driven chunking** — `backend/src/section_chunking.py`, wired into scaffold-diff extract; contract `games/mork-borg/passage-sections.json` (see Briefing 6)
- **Ingest coverage reporter** — `backend/check_coverage.py` / `.\check-coverage.ps1`
- Unified lookup-table pipeline (`run_lookup_table_pipeline`)
- Complete `--cleanup` on full PDF re-ingest (chunks + document)

---

## Planned

_(none)_

---

## References

- [ingest-manifest-sync.md](./ingest-manifest-sync.md) — manifest as Tier-5 contract
- [pdf-graph-builder-briefing-4.md](./pdf-graph-builder-briefing-4.md) — Phase 1 verification queries
- [AGENTS.md](../AGENTS.md) — table delivery workflow
