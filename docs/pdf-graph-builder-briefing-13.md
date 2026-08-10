# Briefing 13: THE WORLD declared sections via full `/extract` (required)

**For pdf-graph-builder agents.** ADA retrieval **requires** declared `passage-section` Chunks for place/lore questions. Page-anchored full-page Chunks are a **last resort only** — not an acceptable steady state for THE WORLD.

**Ops correction ([handoff-10](../inbox/ai-dm-assistant-handoff-10.md)):** land Tier-5 section Chunks with the **operator ingest path** — full `POST /extract` (`scaffold-diff`) via `.\ingest-morkborg.ps1` — with **`section_phase` high enough** to include THE WORLD `sections[]`. Do **not** treat `.\materialize-passage-sections.ps1` (or other `materialize-*` CLIs) as the normal fix; those are **dev / recovery only** and bypass `/extract`.

**Contract synced:** ADA / pgb `passage-sections.json` **v0.5.5** — THE WORLD `sections[]` includes `galgenbeck`, `sarkash`, `grift`, …

**Symptom (operator DB `morkborg`, 2026-08-07):** only **4** `Chunk` nodes with `source_format: passage-section` — all RULES phase-1 (`abilities`, `tests-and-dr`, `carrying-capacity`, `hit-points-and-broken`). **Zero** WORLD section Chunks. Default extract still uses **`section_phase=1`**, which explains the gap.

This is an **ingest / `section_phase` gap**, not an ADA synonym issue. No ADA reset/bootstrap required (Tier 5).

---

## Required operator path

1. Confirm pgb `games/mork-borg/passage-sections.json` is v0.5.5 with WORLD `sections[]`.
2. Run **full ingest**: `.\ingest-morkborg.ps1` → `POST /extract` (`scaffold-diff`).
3. On that ingest, set **`section_phase` high enough** that THE WORLD ids are included (not stuck at phase 1).
4. Do **not** chain `materialize-passage-sections.ps1` as a required step (recovery/debug only).

---

## Acceptance (after that ingest)

```cypher
MATCH (c:Chunk)
WHERE c.source_format = 'passage-section'
RETURN c.section_id AS sid, c.section_title AS st
ORDER BY sid
```

Must include WORLD ids from the contract, including:

| `section_id` | Smoke |
|---|---|
| `galgenbeck` | “Where is Galgenbeck?” → CONTEXT **declared section**, not only page-anchored |
| `sarkash` / `grift` / … | Present (spot-check 2+) |

Shape (handoff-8):

```text
(:Chunk {
  id: "{file}#section:{section_id}",
  section_id, section_title,
  text,   // body AFTER start heading
  page_number_start / page_number_end,
  source_format: "passage-section"
})-[:PART_OF]->(:Document)

(:Chunk)-[:DOCUMENTED_BY]->(:RulePassage { section_id, … })
```

Optional: `(IndexEntry)-[:MAPS_TO_SECTION]->(Chunk)` (ADA also matches `section_title` / `section_id` ≈ entry title).

---

## Likely cause

| Cause | Notes |
|---|---|
| Default **`section_phase=1`** | Only RULES phase-1 sections land — matches the 4 Chunks in Neo4j |
| WORLD declared in contract but phase gate skips them | Raise phase on full `/extract` |

Do **not** “fix” by teaching ADA to prefer page Chunks.

---

## Acceptance checklist

- [ ] `passage-section` count ≫ 4 and includes `galgenbeck`
- [ ] Spot-check: `galgenbeck` body is place prose (Tveland / Josilfa), not an unrelated page dump
- [ ] Handoff to ADA `docs/inbox/` with Cypher counts + any `MAPS_TO_SECTION` notes

**ADA already wired:** `ContextRetriever._add_sections_from_catalog` before page-anchored fallback. Once Chunks exist from full `/extract`, Galgenbeck smoke should show declared section prose without further ADA changes.
