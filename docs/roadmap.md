# Roadmap (pdf-graph-builder / Mörk Borg ingest)

Operational backlog for scaffold-diff ingest and lookup-table materialization. Not a release schedule.

---

## Done (recent)

- **Section-driven chunking** — `backend/src/section_chunking.py`, wired into scaffold-diff extract; contract `games/mork-borg/passage-sections.json` (see Briefing 6)
- **Contract-owned passage boundaries** — RULES `sections[]` anchors + CREATURES `entity_passage.stop_before` in `passage-sections.json` (v0.4.0); Python matches only (Briefings 10–11). Prefer amending JSON after a PDF pass over hardcoding cuts in code.
- **Ingest coverage reporter** — `backend/check_coverage.py` / `.\check-coverage.ps1`
- Unified lookup-table pipeline (`run_lookup_table_pipeline`)
- Complete `--cleanup` on full PDF re-ingest (chunks + document)

---

## Waiting on operator

### PDF pass — review `passage-sections.json` (v0.4.0)

**Milestone:** Briefings 6–11 code paths are in place (section anchors, index/fiction, entity passages, contract-owned `stop_before`). **Next quality step is yours**, not further agent hardcoding.

1. Open Bare Bones PDF alongside [`games/mork-borg/passage-sections.json`](../games/mork-borg/passage-sections.json).
2. Check RULES `sections[]` `start_anchor` / `end_anchor` against real headings.
3. Check CREATURES blocks vs `entity_passage.stop_before` (and add `text_end_hint` on a `creatures_index` row if one creature still bleeds).
4. Spot-check `entry_kind` on index rows.
5. Use the field guide: [`games/mork-borg/README.md`](../games/mork-borg/README.md). When happy, bump `verified_note` / set `status: verified`, then re-ingest (or `--entity-passages-only` / section materialize for a targeted refresh).

Until that pass lands, treat boundary regexes as a first-stab draft.

---

## Planned

### Ingest operational model (one pipeline)

Terminal ingest and web UI must use the **same** `/extract` scaffold-diff path — not a parallel `materialize-*` CLI workflow.

**Do:**

- Run **`backend\start.ps1`**, then **`.\ingest-morkborg.ps1`** for normal ingest (CLI replaces the web UI only).
- **Restart the backend** after code changes, then run a full ingest so hooks (section chunking, rulebook catalog, tables) load from current `main.py`.
- Run **`.\check-coverage.ps1`** after ingest to verify manifest vs Neo4j.

**Don't** (for routine ops):

- Chain **`materialize-*`** scripts (`materialize-passage-sections.ps1`, `materialize-rulebook-index.ps1`, etc.) as required ingest steps — they bypass `/extract` and exist only as dev/recovery shortcuts.

**Follow-ups:**

- Document or demote `materialize-*` scripts explicitly as **dev-only / recovery** (not operator workflow).
- Expose **`section_phase`** on full ingest (`ingest_pdf.py` / `/extract`) so full runs are not stuck at phase 1 by default.

---

## References

- [ingest-manifest-sync.md](./ingest-manifest-sync.md) — manifest as Tier-5 contract
- [pdf-graph-builder-briefing-4.md](./pdf-graph-builder-briefing-4.md) — Phase 1 verification queries
- [AGENTS.md](../AGENTS.md) — table delivery workflow
