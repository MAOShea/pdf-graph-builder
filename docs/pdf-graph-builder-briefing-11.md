# Briefing 11: Finish entity-passage boundaries (chunking quality gate)

**For pdf-graph-builder agents.** Follow-up to [briefing-10](./pdf-graph-builder-briefing-10.md) / handoff-6. Neighbor-creature bleed is fixed; **passage end boundaries are not.** This briefing closes the **passage/chunk boundary quality** gate in AI-DM-Assistant [DESIGN.md §4.5](../../DESIGN.md#45-mechanism-coverage-phases-per-system) (per-phase step 3) for CREATURES — required before that repo treats the fiction gate as done and widens to combat (coverage phase 2).

**Prerequisites:**

1. Handoff-6 green: 12 CREATURES `RulePassage` with `source_format: entity-passage`, `MAPS_TO_PASSAGE` / `DOCUMENTED_BY`.
2. Module: `backend/src/entity_passage_materialization.py` (or successor).
3. ADA already prefers entity passages over page `Chunk` — no ADA change required for this fix.

---

## Problem (observed after handoff-6)

ADA Goblin CONTEXT (entity-scoped path) looks like:

```text
Seth, Goblin
HP 6 Morale 7 Ropy skin -d2 Knife/shortbow d4
Special: Quick, attacks and defence are DR14.
All goblins carry a curse. …
Then, only the dark of Sarkash will hide you.
Head 7s
Captured 150s
Dead 20s
```

**Good:** Bent / Scum / Poisoned knife are gone (next-creature cut works).  
**Bad:** `Head 7s` / `Captured 150s` / `Dead 20s` are **not** Goblin body text — they are trailing bounty/loot lines on the same page **before** the next creature heading. The LLM then invents “headshots” and “150s rewards” for Goblins.

**Root cause:** End delimiter = “next creature heading” only. That is necessary but **not sufficient**. Trailing non-stat blocks between creatures must not stay inside the prior entity’s passage.

**Out of scope for “fixes”:** ADA prompt patches, regex trim in the chat app, or deleting those lines only for Goblin by hard-coded exception without generalizing the boundary rules. This is **chunking / span logic** in pdf-graph-builder.

---

## Goal

Each CREATURES entity `RulePassage.text` must be a **focused creature block**:

| Include | Exclude |
|---|---|
| Name / HP / Morale / armor / weapons / Special | The **next** creature’s block |
| Curse / lore paragraphs that belong to that creature | Trailing **bounty / silver / loot** lines (`Head …s`, `Captured …s`, `Dead …s`, etc.) |
| | Unrelated page chrome / other creatures |

Same quality bar applies when you later add THE_WORLD entity passages: place block must not swallow the next place or a following unrelated table.

---

## Required approach

**Design direction (required):** put end markers in `passage-sections.json` → `entity_passage.end_detection.stop_before` (same spirit as `sections[].end_anchor` and table `pdf_extract.stop_before`). Python only compiles/matches. Do **not** leave bounty vocabulary hardcoded in the materializer.

Suggested end markers (combine; first match wins after start):

1. **Next creature heading** — e.g. `Bent, Scum`, next `IndexEntry` title on page.
2. **`entity_passage.stop_before`** — whole-line regexes for trailing loot / bounty tallies (`Head …s`, `Captured …s`, `Dead …s`, reversed `200s Captured`, …). Exclusive cut.
3. Optional per-row override: `text_end_hint` on a `creatures_index` entry when shared patterns fail.

Operator PDF pass can amend the JSON; re-run materialization **idempotently** (overwrite passage `text` for existing ids).

**Do not** leave acceptance as “has_scoped = true” alone — that already passed while bounty lines remained.

---

## Acceptance criteria

```cypher
// Goblin body must not include bounty trail
MATCH (e:IndexEntry {title:'Goblin'})-[:MAPS_TO_PASSAGE]->(p:RulePassage)
WHERE coalesce(p.source_format, '') = 'entity-passage'
   OR p.id CONTAINS 'entity-passage'
RETURN p.id AS id,
       p.text CONTAINS 'Head 7s' AS has_head,
       p.text CONTAINS 'Captured 150s' AS has_captured,
       p.text CONTAINS 'Dead 20s' AS has_dead,
       p.text CONTAINS 'Bent' OR p.text CONTAINS 'Scum' AS has_neighbor,
       p.text CONTAINS 'Ropy skin' AS has_body,
       p.text CONTAINS 'curse' AS has_curse;
// expect: has_head/has_captured/has_dead/has_neighbor = false
//         has_body/has_curse = true

// Spot-check another dense-page creature if present
MATCH (e:IndexEntry {column:'CREATURES'})-[:MAPS_TO_PASSAGE]->(p:RulePassage)
WHERE coalesce(p.source_format, '') = 'entity-passage'
WITH e.title AS title, p.text AS text
WHERE text CONTAINS 'Head ' AND text =~ '(?s).*Head \\d+s.*'
RETURN title, substring(text, 0, 60) AS preview;
// expect 0 rows (no CREATURES entity-passage still embedding Head Ns lines)
```

**ADA smoke (operator):** Re-ask “What is a Goblin in Mörk Borg?” — CONTEXT entity-scoped block must end at Sarkash / curse close, **without** Head/Captured/Dead lines. Suggestions inventing “150s rewards” / “headshots” from those lines should disappear (LLM may still be imperfect; CONTEXT must be clean).

**Pass:** Cypher green + Goblin CONTEXT clean.  
**Fail:** Only neighbor-creature exclusion without bounty-trail exclusion.

---

## Out of scope

- THE_WORLD entity passages (nice follow-up; same boundary discipline when added)
- Raising RULES `section_phase` / coverage phase 2 combat sections (ADA coverage ladder — after this gate)
- Embeddings on entity passages
- ADA retrieval order (already prefers `MAPS_TO_PASSAGE`)

---

## Operator checklist (AI-DM-Assistant)

- [ ] Sync: `.\scripts\sync-outbox-briefings.ps1`
- [ ] Paste into pgb session
- [ ] After handoff: re-smoke Goblin CONTEXT (inspector panel)
- [ ] Only then treat DESIGN §4.5 fiction-gate step 3 as closable for CREATURES

---

## Checklist for pgb agent

- [ ] Identify why end cut stops only at next creature heading
- [ ] Add deterministic end-before-bounty (and/or contract `text_end_hint`) — general rule, not Goblin-only hack
- [ ] Re-materialize entity passages; overwrite text
- [ ] Acceptance Cypher green (no Head/Captured/Dead in Goblin; no neighbor bleed)
- [ ] Handoff: before/after Goblin `substring(text)` + rule description for ADA
