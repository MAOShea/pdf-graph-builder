# Roadmap (pdf-graph-builder / Mörk Borg ingest)

Operational backlog for scaffold-diff ingest and lookup-table materialization. Not a release schedule.

---

## Done (recent)

- **Section-driven chunking** — `backend/src/section_chunking.py`, wired into scaffold-diff extract; contract `games/mork-borg/passage-sections.json` (see Briefing 6)
- **Contract-owned passage boundaries** — RULES + THE WORLD `sections[]` anchors, `text_filters`, `subheading_regex` / `passage_split`, `page_range`, `content_source`; CREATURES `entity_passage.stop_before` (v0.5.5). Python matches only (Briefings 6, 10–11). Prefer amending JSON after a PDF pass over hardcoding cuts in code.
- **Shared extract + pdf-as-md** — `document_extract.py` + `tools/pdf-as-md` (Markdown sink, no Neo4j) for contract/PDF comparison
- **AgonyEndTable** — hand-authored label→die chooser (p.17); ADA handoff-8 for `USES` / retrieval wiring
- **Ingest coverage reporter** — `backend/check_coverage.py` / `.\check-coverage.ps1`
- **Section ingest gates** — `backend/check_section_gates.py` / `.\check-section-gates.ps1` (Chunks, index hops, splits, spines)
- Unified lookup-table pipeline (`run_lookup_table_pipeline`)
- Complete `--cleanup` on full PDF re-ingest (chunks + document)

---

## Waiting on operator

### PDF pass — review `passage-sections.json` (v0.5.5)

**Milestone:** Briefings 6–11 code paths are in place (section anchors incl. THE WORLD, `text_filters`, index/fiction, entity passages, contract-owned `stop_before`). **Next quality step is yours**, not further agent hardcoding.

1. Open Bare Bones PDF alongside [`games/mork-borg/passage-sections.json`](../games/mork-borg/passage-sections.json) and/or [`tools/pdf-as-md` output](../tools/pdf-as-md).
2. Check RULES + THE WORLD `sections[]` `start_anchor` / `end_anchor` (incl. two-line titles, Western Kingdom pp.15–16, Kergüs / Ambivalence split).
3. Check CREATURES blocks vs `entity_passage.stop_before` (and add `text_end_hint` on a `creatures_index` row if one creature still bleeds).
4. Spot-check `entry_kind` on index rows; confirm footers are stripped (`text_filters`).
5. Use the field guide: [`games/mork-borg/README.md`](../games/mork-borg/README.md). When happy, bump `verified_note` / set `status: verified`, then re-ingest (or `--entity-passages-only` / section materialize for a targeted refresh).

Until that pass lands, treat boundary regexes as a first-stab draft.

**Helper:** [`tools/pdf-as-md`](../tools/pdf-as-md) dumps the same runtime PDF read path to Markdown (no Neo4j) so you can compare extract text to the original PDF while editing the contract.

---

## Planned

### Ingest operational model (one pipeline)

Terminal ingest and web UI must use the **same** `/extract` scaffold-diff path — not a parallel `materialize-*` CLI workflow.

**Do:**

- Run **`backend\start.ps1`**, then **`.\ingest-morkborg.ps1`** for normal ingest (CLI replaces the web UI only). Ollama Stage 2 is **off** unless **`-ScaffoldDiffLlm`**.
- **Restart the backend** after code changes, then run a full ingest so hooks (section chunking, rulebook catalog, tables) load from current `main.py`.
- Run **`.\check-section-gates.ps1`** after ingest to verify contracted section/index/spine shape, then **`.\check-coverage.ps1`** for manifest tables.

**Don't** (for routine ops):

- Chain **`materialize-*`** scripts (`materialize-passage-sections.ps1`, `materialize-rulebook-index.ps1`, etc.) as required ingest steps — they bypass `/extract` and exist only as dev/recovery shortcuts.

**Follow-ups:**

- Document or demote `materialize-*` scripts explicitly as **dev-only / recovery** (not operator workflow).

**Done (ops):** `section_phase` is on `POST /extract` + `ingest_pdf.py` / `.\ingest-morkborg.ps1 -SectionPhase` (CLI default **2** so THE WORLD sections land; backend omits → still 1).

---

## References

- [ingest-manifest-sync.md](./ingest-manifest-sync.md) — SoT split; no copies
- [AGENTS.md](../AGENTS.md) — table delivery workflow
