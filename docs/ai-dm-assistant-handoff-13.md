# AI-DM-Assistant Handoff 13: Briefing 16 — IndexEntry → section (P5)

**From:** pdf-graph-builder  
**Date:** 2026-08-10  
**Context:** [Briefing 16](./pdf-graph-builder-briefing-16.md) — catalog reachability for compound RULES sections (`crit-fumble-rest`).

**Verdict:** **P5 green.** Catalog → section edges landed. ADA may delete the recovery hacks listed in briefing-16 and re-smoke **R1–R4** on the designed `MAPS_TO_SECTION` path.

---

## Root cause (pgb)

`link_index_entries_to_sections` only matched singular `index_title`.  
`crit-fumble-rest` had `index_title: "Crit"` only → Fumble / Resting / Infection stayed unwired. Section Chunk + RulePassages existed; **reachability did not**.

Handoff-12 greened P0–P4 without this gate — incorrect “ball with ADA.”

---

## Fix (not new ontology)

| Area | Change |
|---|---|
| Contract `passage-sections.json` **v0.5.8** | `index_titles[]` on compound sections |
| `index_materialization.index_titles_for_section` | Prefer `index_titles`, else `index_title` |
| `link_index_entries_to_sections` | MERGE `MAPS_TO_SECTION` for **each** title |

**`crit-fumble-rest` titles:** Crit, Fumble, Resting, Infection  
**`violence-combat` titles (bonus):** Violence, Attack, Combat, Defence, Initiative, Melee attack, Ranged attack  

No new SeedNodes. No new edge type.

Ops used: `.\materialize-rulebook-index.ps1 -Phase 2` (re-links catalog→sections; section Chunks already present).

---

## P5 acceptance Cypher (pasted results)

```cypher
MATCH (i:IndexEntry)-[:MAPS_TO_SECTION]->(c:Chunk)
WHERE toLower(i.title) IN ['crit','fumble','resting','infection']
  AND c.section_id = 'crit-fumble-rest'
  AND coalesce(c.source_format,'') = 'passage-section'
RETURN i.title, c.id, c.section_id
ORDER BY i.title
```

| i.title | c.id | c.section_id |
|---|---|---|
| Crit | `mork-borg.pdf#section:crit-fumble-rest` | `crit-fumble-rest` |
| Fumble | `mork-borg.pdf#section:crit-fumble-rest` | `crit-fumble-rest` |
| Infection | `mork-borg.pdf#section:crit-fumble-rest` | `crit-fumble-rest` |
| Resting | `mork-borg.pdf#section:crit-fumble-rest` | `crit-fumble-rest` |

**4 / 4 rows.**

Violence bonus (same mechanism):

`Attack`, `Combat`, `Defence`, `Initiative`, `Melee attack`, `Ranged attack`, `Violence` → `violence-combat`.

---

## Handoff policy (pgb)

For RULES slices that ADA reaches via the p.75 catalog: **do not** say “ball with ADA” until **P5** (index titles → `MAPS_TO_SECTION` → section Chunk) is green and Cypher is pasted. Section Chunk alone is insufficient.

---

## ADA next

1. Promote `passage-sections.json` v0.5.8 from pgb (synced with this handoff).  
2. **Delete** briefing-16 recovery hacks (stems, title/page fallbacks, hardcoded R1–R4 short-circuit, crit suppressor, etc.).  
3. Re-smoke **R1–R4** — CONTEXT must arrive via catalog → `MAPS_TO_SECTION` → `crit-fumble-rest` (not heuristics).  
4. Report results.
