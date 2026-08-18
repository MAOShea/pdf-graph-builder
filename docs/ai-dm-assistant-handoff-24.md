# AI-DM-Assistant Handoff 24: Coverage 2c complete (Briefing 24 + follow-ups)

**From:** pdf-graph-builder  
**Date:** 2026-08-16  
**Context:** [Briefing 24](./pdf-graph-builder-briefing-24.md) / slice **2c** (`reaction-morale`, Bare Bones p.32). Supersedes piecemeal [handoff-21](./ai-dm-assistant-handoff-21.md) / [22](./ai-dm-assistant-handoff-22.md) / [23](./ai-dm-assistant-handoff-23.md) as the single ADA inbox item for 2c.

**Verdict:** **2c ingest green** on operator DB `morkborg`. Catalog P2, `ReactionTable`, and Morale `If` spines landed. **Ball is with ADA** — promote contracts; run standing smokes **M1 / M2** (ADA-only; pgb cannot execute chat smokes).

---

## Briefing 24 gates

| Gate | Result |
|---|---|
| **P1** section Chunk focused (Reaction → before Getting Better) | **Green** — `section_id=reaction-morale`, p.32, `source_format=passage-section`, 441 chars |
| **P2** Reaction **and** Morale `MAPS_TO_SECTION` → same Chunk | **Green** |
| **P3** (briefing: no table) | **Reopened by operator** — `ReactionTable` (5 bands) shipped; no flee/surrender d6 table |
| **P4** no fiction-seed fan-out from section | **Green** |
| **P5** no invented Reaction / MoraleCheck SeedNodes | **Green** — `FOR` Morale spines reuse existing `SeedNode:Morale` |

**Operator extras beyond briefing text:** structured `ReactionTable` + three Morale altitude-D spines (boolean procedure).

---

## Contracts to promote

| File | Version | Change |
|---|---|---|
| `passage-sections.json` | **0.5.12** | `index_titles`: Reaction + Morale; `contains_lookup_tables`: `ReactionTable` |
| `ingest-manifest.json` | **0.3.6** | `ReactionTable` (`range_list` 2-3…11-12, stop before Morale) |
| `operational-spines.json` | **0.4.0** | `if:morale-trigger`, `if:morale-demoralized`, `if:morale-flee-or-surrender` |

ADA: `sync-passage-sections-from-pgb.ps1`; reconcile ingest-manifest / operational-spines per your SoT policy.

---

## Ops (what pgb ran)

| Step | Path |
|---|---|
| Catalog P2 | `index_titles` edit + `link_index_entries_to_sections` / section rematerialize |
| ReactionTable | `.\ingest-tables.ps1 -Tables ReactionTable` |
| Morale spines | `.\materialize-operational-spines.ps1` |
| Full `.\ingest-morkborg.ps1` / Ollama | **Not required** for these gates |

---

## Acceptance Cypher (pasted)

### P1 — Section

```cypher
MATCH (c:Chunk {section_id: 'reaction-morale'})-[:PART_OF]->(:Document {fileName: 'mork-borg.pdf'})
RETURN c.source_format AS source_format,
       c.page_number_start AS p_start,
       size(c.text) AS chars,
       substring(c.text, 0, 100) AS head,
       substring(c.text, size(c.text)-80, 80) AS tail
```

| source_format | p_start | chars | head / tail |
|---|---|---|---|
| passage-section | **32** | **441** | When meeting… / …flees or (4–6) surrenders. |

### P2 — Catalog

```cypher
MATCH (e:IndexEntry)-[:MAPS_TO_SECTION]->(c:Chunk {section_id: 'reaction-morale'})
RETURN e.title AS title
ORDER BY e.title
```

| title |
|---|
| **Morale** |
| **Reaction** |

### ReactionTable

```cypher
MATCH (t:ReactionTable)-[:HAS_ENTRY]->(r:TableEntry)
RETURN t.id AS table, count(r) AS entry_count
```

| table | entry_count |
|---|---|
| ReactionTable | **5** |

Rows: 2-3 Kill! · 4-6 Angered · 7-8 Indifferent · 9-10 Almost friendly · 11-12 Helpful.

### Morale If spines

```cypher
MATCH (i:If:IngestNode)
WHERE i.id STARTS WITH 'if:morale-'
OPTIONAL MATCH (i)-[:FOR]->(proc)
OPTIONAL MATCH (i)-[:`IF`]->(b:BoolExpression)
OPTIONAL MATCH (i)-[:DOCUMENTED_BY]->(p:RulePassage)
RETURN i.id AS if_id, b.combinator AS combinator,
       [l IN labels(proc) WHERE l <> 'SeedNode'][0] AS for_label,
       p.section_id AS evidence
ORDER BY i.id
```

| if_id | combinator | for | evidence |
|---|---|---|---|
| `if:morale-demoralized` | LEAF | Morale | reaction-morale |
| `if:morale-flee-or-surrender` | AND | Morale | reaction-morale |
| `if:morale-trigger` | OR | Morale | reaction-morale |

```cypher
MATCH (c:Compare {id: 'compare:2d6-gt-morale'})-[:COMPARED_TO]->(seed)
RETURN c.op AS op, c.left AS left, c.threshold AS threshold,
       [l IN labels(seed) WHERE l <> 'SeedNode'][0] AS compared_to
```

| op | left | threshold | compared_to |
|---|---|---|---|
| **>** | **2d6** | **null** (runtime sheet) | **Morale** |

---

## Standing smokes (ADA only)

pgb does **not** run chat smokes. After promote:

| Id | Question intent | Expect in CONTEXT |
|---|---|---|
| **M1** | Uncertain reaction, rolled **7** on 2d6 | Declared `reaction-morale` and/or `ReactionTable` → **7–8 Indifferent** (not basilisk / powers) |
| **M2** | Leader dead; Morale **7**, rolled **9** on 2d6 | **Morale → MAPS_TO_SECTION** + prefer `if:morale-*` (greater-than → demoralized); **not** creature `HAS_MORALE` sheet as the procedure |

Listed in ADA `deltas.json` → `phase_2_slices.2c.standing_smokes`.

---

## Remaining WIP

- Optional `passage_split` on `^\s*Morale\s*$` (not blocking).
- ADA may add dedicated `MoraleCheck` SeedNode later; retarget spine `for_procedure` if sheet `Morale` must stay procedure-free.
- Slice **2d** (`getting-better-or-worse`) — next coverage slice, not this handoff.

---

## Promote

```powershell
# From pdf-graph-builder root:
Copy-Item -Force .\docs\ai-dm-assistant-handoff-24.md D:\GitHub\AI-DM-Assistant\docs\inbox\

# ADA:
# .\scripts\sync-passage-sections-from-pgb.ps1
# pull ingest-manifest + operational-spines per sync policy
# run M1 / M2
```
