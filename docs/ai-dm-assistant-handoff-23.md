# AI-DM-Assistant Handoff 23: Coverage 2c — Morale If spines

**From:** pdf-graph-builder  
**Date:** 2026-08-16  
**Context:** Operator follow-up after [handoff-21](./ai-dm-assistant-handoff-21.md) / [handoff-22](./ai-dm-assistant-handoff-22.md) / [Briefing 24](./pdf-graph-builder-briefing-24.md). Morale procedure boolean rules encoded as altitude-D `If` spines (not prose-only).

**Verdict:** **Morale spines green** — three `If` graphs `FOR` `Morale`, evidence on `reaction-morale`. **Ball is with ADA** — retrieval hop for Morale procedure; smoke **M2** should prefer spines + section (not invent bands / not sheet-only).

---

## Ops

| Action | Done? |
|---|---|
| Contract `operational-spines.json` **v0.4.0** | **Yes** |
| Compare atom: optional `compared_to` (Morale) + null threshold | **Yes** — `spine_materialization.py` |
| `.\materialize-operational-spines.ps1` | **Yes** — warnings=0; D1–D3 intact |
| Full Ollama ingest | **No** — not required |

```powershell
.\materialize-operational-spines.ps1
# or next full .\ingest-morkborg.ps1 (section_phase>=2) re-emits via /extract
```

---

## Spines shipped

| If.id | combinator | Meaning |
|---|---|---|
| `if:morale-trigger` | **OR** | leader killed ∨ half group eliminated ∨ enemy ≤⅓ HP → **roll 2d6 vs Morale** |
| `if:morale-demoralized` | **LEAF** | `Compare` 2d6 **>** `COMPARED_TO` SeedNode:`Morale` (threshold from sheet at runtime) → demoralized / else holds |
| `if:morale-flee-or-surrender` | **AND** | demoralized ∧ d6 ≤ 3 → **flees**; ELSE **surrenders** |

**FOR:** existing `SeedNode:Morale` (sheet slot + procedure hook). Briefing 24 forbade inventing `MoraleCheck` in pgb — ADA may add a dedicated procedure seed later and we retarget `for_procedure`.

---

## Acceptance Cypher (pasted)

```cypher
MATCH (i:If:IngestNode)
WHERE i.id STARTS WITH 'if:morale-'
OPTIONAL MATCH (i)-[:FOR]->(proc)
OPTIONAL MATCH (i)-[:`IF`]->(b:BoolExpression)
OPTIONAL MATCH (b)-[:HAS_ATOM]->(a)
OPTIONAL MATCH (i)-[:THEN]->(t)
OPTIONAL MATCH (i)-[:ELSE]->(e)
OPTIONAL MATCH (i)-[:DOCUMENTED_BY]->(p:RulePassage)
RETURN i.id AS if_id, b.combinator AS combinator,
       collect(DISTINCT coalesce(a.name, a.id)) AS atoms,
       collect(DISTINCT coalesce(t.name, t.id)) AS then_names,
       collect(DISTINCT coalesce(e.name, e.id)) AS else_names,
       [l IN labels(proc) WHERE l <> 'SeedNode'][0] AS for_label,
       p.section_id AS evidence_section
ORDER BY i.id
```

| if_id | combinator | atoms (abbrev) | then | else | for | evidence |
|---|---|---|---|---|---|---|
| if:morale-demoralized | LEAF | compare:2d6-gt-morale | demoralized | morale-holds | Morale | reaction-morale |
| if:morale-flee-or-surrender | AND | demoralized, compare:d6-flee-band | flees | surrenders | Morale | reaction-morale |
| if:morale-trigger | OR | leader is killed, half the group…, 1/3 HP… | roll-2d6-vs-morale | — | Morale | reaction-morale |

```cypher
MATCH (c:Compare {id: 'compare:2d6-gt-morale'})-[:COMPARED_TO]->(seed)
RETURN c.op, c.left, c.threshold, labels(seed)
```

| op | left | threshold | seed |
|---|---|---|---|
| **>** | **2d6** | **null** | SeedNode / **Morale** |

---

## Promote

| File | Version |
|---|---|
| `games/mork-borg/operational-spines.json` | **0.4.0** |

```powershell
Copy-Item -Force .\docs\ai-dm-assistant-handoff-23.md D:\GitHub\AI-DM-Assistant\docs\inbox\
```

## Remaining WIP

- Optional `passage_split` on `Morale` subhead (still deferred).
- ADA: dedicated `MoraleCheck` SeedNode if sheet `Morale` must stay procedure-free.
- Reaction bands remain `ReactionTable` (handoff-22); not spines.
