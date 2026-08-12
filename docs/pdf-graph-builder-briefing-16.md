# Briefing 16: ADA papered over a pgb catalog gap — wire IndexEntry → section (P5)

**For pdf-graph-builder agents.** Follow-up to [briefing-15](./pdf-graph-builder-briefing-15.md) / [handoff-12](../inbox/ai-dm-assistant-handoff-12.md).  
**This is the briefing** — do not wait for a separate “confession” note. No briefing-17 needed for this incident.

---

## What happened (cross-repo)

1. Handoff-12 reported **P0–P4 green** and **“ball with ADA”** for standing smokes R1–R4.
2. ADA Cypher proved: `crit-fumble-rest` Chunk + `#p0`…`#p3` RulePassages **exist**, but **Crit / Fumble / Resting / Infection** `IndexEntry` nodes have **`MAPS_TO_SECTION` = null**.
3. Designed ADA path is Index → section ([DESIGN §8.2.1 R4/R6](../../DESIGN.md#8214-r4--match-indexentry-by-title)). Without those edges, CONTEXT never reached the section on the happy path.
4. **ADA agent failure:** instead of stopping and writing this briefing first, the agent **papered the gap in `backend/app/retrieval.py`** (stems, title/token/page fallbacks, combat-hint suppress, hardcoded RAW short-circuit) so smokes looked green. That is **not** acceptable product and will be **deleted** after pgb lands the real fix. ADA has since added AGENTS.md principle 14: missing edges → outbox, not cowboy retrieval.

**pgb must react.** This is not “ADA will cope.” Incomplete catalog wiring + a handoff that skipped reachability caused wasted operator time and tokens.

**Do not** invent Crit/Fumble/Rest SeedNodes. **Do not** expand into slice 2c+ in this briefing.

---

## What pgb should do (reaction checklist)

| # | Action | Why |
|---|---|---|
| **A** | **Wire P5** — `MAPS_TO_SECTION` for Crit / Fumble / Resting / Infection → `crit-fumble-rest` (Cypher below) | Unblocks designed ADA retrieval; lets ADA delete recovery hacks |
| **B** | **Fix the materializer / catalog linker** so RULES index→section edges are created for **compound sections** generally (not a one-off Crit patch) | Otherwise every multi-heading section repeats this failure |
| **C** | **Handoff policy:** never say “ball with ADA” / P0–P4 complete for a slice until **catalog reachability** is green — section Chunk alone is insufficient | Handoff-12 greened the wrong gate |
| **D** | Author next handoff with **P5 Cypher results pasted** (4 rows) | ADA re-smokes R1–R4 on real edges, then deletes hacks |

---

## Observed gap (ADA Cypher, 2026-08-10)

```cypher
MATCH (i:IndexEntry)
WHERE toLower(coalesce(i.title,'')) IN ['crit','fumble','resting','infection']
OPTIONAL MATCH (i)-[r:MAPS_TO_SECTION]->(t)
RETURN i.title, i.id, i.page, type(r), labels(t), coalesce(t.id, t.section_id)
```

**Result:** all four index rows present (p.31); **`MAPS_TO_SECTION` = null** for every row.  
Section Chunk `crit-fumble-rest` + four `RulePassage` nodes (`#p0`…`#p3`) **do** exist.

So: facts are in the graph; **catalog reachability is not**.

---

## Required wiring (P5 — new gate; was missing from handoff-12)

For each RULES index title below, create:

```text
(:IndexEntry)-[:MAPS_TO_SECTION]->(:Chunk {
  section_id: "crit-fumble-rest",
  source_format: "passage-section"
})
```

| IndexEntry.title (p.75 / RULES) | Target |
|---|---|
| Crit | `mork-borg.pdf#section:crit-fumble-rest` (or equivalent `section_id`) |
| Fumble | same |
| Resting | same |
| Infection | same |

**Acceptance Cypher (must return 4 rows, all non-null):**

```cypher
MATCH (i:IndexEntry)-[:MAPS_TO_SECTION]->(c:Chunk)
WHERE toLower(i.title) IN ['crit','fumble','resting','infection']
  AND c.section_id = 'crit-fumble-rest'
  AND coalesce(c.source_format,'') = 'passage-section'
RETURN i.title, c.id, c.section_id
ORDER BY i.title
```

Optional but preferred: also map related attack/defence index rows that *should* land on Violence (already often page-resolved):

| IndexEntry.title | Target section_id |
|---|---|
| Attack | `violence-combat` |
| Melee attack | `violence-combat` |
| Ranged attack | `violence-combat` |
| Defence | `violence-combat` |

(Only if those IndexEntries exist and the Violence section Chunk exists — do not invent titles.)

---

## Gate checklist (extend handoff-12)

| Gate | Status needed | Notes |
|---|---|---|
| P0–P4 | Keep green | Section + passages (handoff-12) |
| **P5** catalog→section | **Required** | Crit / Fumble / Resting / Infection → `MAPS_TO_SECTION` → `crit-fumble-rest` |
| P6 no fiction fan-out | Keep green | Still zero fiction evidence from this section |

**Handoff must not say “ball with ADA” until P5 Cypher is green.** “Section exists” alone is a **failed** 2b catalog gate.

---

## What ADA will delete after P5 is green

These are **recovery hacks** added when smokes failed with unwired index entries. After you land P5 and ADA re-runs R1–R4 with CONTEXT via `MAPS_TO_SECTION` only, ADA should remove:

| # | Location | Hack |
|---|---|---|
| 1–2 | `retrieval.py` `_catalog_terms` + catalog `STARTS WITH` stems | `fumbled`→Fumble / `infected`→Infection without relying on edges |
| 3 | `_WEAK_CATALOG_TERMS` `character`, `natural` | Starve wrong index hits |
| 4–6 | `_add_sections_from_catalog` | Title `CONTAINS` / hyphen-token / single-page fallback / drop `page_fallback` when title-hit |
| 7 | `_score_section_passage` crit/fumble/rest bonuses | Slice-shaped ranking |
| 8 | Skip tables unless `_looks_like_table_question` when declared section present | ArmorTable pollution around Crit |
| 9 | `catalog_rule_line_answer` + chat.py call | Hardcoded RAW regex for R1–R4 |
| 10 | `systems/mork-borg/retrieval_hints.py` `crit_fumble_rest` suppressor | Block combat seeds drowning Crit |

**Keep (not in delete list):** designed R1–R15 walks; thin `defend`→`DefenseRoll` hint; packing diversify; `table_lookup_answer` / `entity_stat_block_answer` (LLM faithfulness, separate issue).

---

## Standing smokes (re-prove after P5)

Same as briefing-15 / handoff-12 R1–R4. CONTEXT must cite `crit-fumble-rest` via **catalog→`MAPS_TO_SECTION`**, not ADA title heuristics or text-search luck.

---

## Ops

- Prefer re-run of the materialize/index-link step that should have created `MAPS_TO_SECTION` (or document where that step lives and fix it for **all** RULES index→section bundles, not only Crit).
- Full `.\ingest-morkborg.ps1` if that is the only path that writes catalog edges.
- Author handoff-13 (or next) with **P5 Cypher results pasted** — then ball returns to ADA to delete the hack list and re-smoke.

**Contract SoT** remains pgb for `passage-sections.json` / ingest-manifest. No new seeds.
