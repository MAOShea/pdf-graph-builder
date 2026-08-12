# AI-DM-Assistant Handoff 15: D1 spines live on full ingest — ADA select hop

**From:** pdf-graph-builder  
**Date:** 2026-08-11  
**Context:** [Briefing 17](./pdf-graph-builder-briefing-17.md) / [handoff-14](./ai-dm-assistant-handoff-14.md). Full `.\ingest-morkborg.ps1` (`section_phase=2`) completed after D0.4 reset+bootstrap.

**Verdict:** **D1 green on a Completed Document.** Three Violence DR12 `If` spines (with `BoolExpression` LEAF + `Compare.threshold=12`) survived cleanup+full extract. **Ball is with ADA** — implement select hop and smoke **C1–C3**. Do not paper missing spines in `retrieval.py`.

---

## Ingest status (operator DB `morkborg`)

| Field | Value |
|---|---|
| Document | `mork-borg.pdf` **Completed** |
| Chunks | 71 / 71 processed |
| Tokens | ~214 662 |
| `section_phase` | **2** (sections + operational spines in `/extract`) |

Handoff-14 used recovery materialize only. **This handoff supersedes that ops note** — product-path ingest has now run.

---

## What pgb shipped (unchanged contract)

| Item | Path / detail |
|---|---|
| Spine contract | `games/mork-borg/operational-spines.json` v0.1.0 |
| Manifest pointer | `ingest-manifest.json` → `operational_spines` |
| Materializer | `backend/src/spine_materialization.py` (deterministic; closed vocab) |
| Extract hook | scaffold-diff when `section_phase >= 2` |
| Recovery CLI | `.\materialize-operational-spines.ps1` |

**Stable ids:** `if:melee-hit-default`, `if:ranged-hit-default`, `if:defence-default`  
(+ `bool:*`, `compare:*-dr12`, `outcome:*` children).

**Scope reminder:** only **D1** (Violence defaults). Crit/fumble/rest = **D2**; creature DR = **D3**. Not “all BoolExpressions in the book.”

---

## Acceptance Cypher (pasted 2026-08-11 post-ingest)

### Spines + BoolExpression + Compare→12

```cypher
MATCH (i:If:IngestNode)-[:FOR]->(proc)
MATCH (i)-[:`IF`]->(b:BoolExpression)-[:HAS_ATOM]->(c:Compare)
OPTIONAL MATCH (c)-[:COMPARED_TO]->(dr)
OPTIONAL MATCH (i)-[:THEN]->(t)
OPTIONAL MATCH (i)-[:ELSE]->(e)
RETURN coalesce(proc.name, labels(proc)[0]) AS procedure,
       b.combinator AS combinator,
       c.threshold AS threshold,
       dr.name AS compared_to,
       count(DISTINCT t) AS then_n,
       count(DISTINCT e) AS else_n,
       i.id AS if_id
ORDER BY procedure
```

| procedure | combinator | threshold | compared_to | then | else | if_id |
|---|---|---|---|---|---|---|
| DefenseRoll | LEAF | **12** | DR | 1 | 1 | `if:defence-default` |
| MeleeAttack | LEAF | **12** | DR | 1 | 1 | `if:melee-hit-default` |
| RangedAttack | LEAF | **12** | DR | 1 | 1 | `if:ranged-hit-default` |

Filter **`i:IngestNode`** — scaffold also has abstract `SeedNode:If` shape edges.

### Evidence → violence-combat passages

```cypher
MATCH (i:If:IngestNode)-[:FOR]->(proc)
MATCH (i)-[:DOCUMENTED_BY]->(p:RulePassage)
WHERE p.section_id = 'violence-combat'
RETURN coalesce(proc.name, labels(proc)[0]) AS procedure, collect(p.id) AS ids
ORDER BY procedure
```

| procedure | passage |
|---|---|
| MeleeAttack | `…#violence-combat#p1` (Test Strength) |
| RangedAttack | `…#violence-combat#p2` (Test Presence) |
| DefenseRoll | `…#violence-combat#p3` (Test Agility) |

---

## Graph shape (for retrieval)

```text
(:If:IngestNode)-[:FOR]->(:MeleeAttack|:RangedAttack|:DefenseRoll)
(:If)-[:IF]->(:BoolExpression {combinator:'LEAF'})-[:HAS_ATOM]->(:Compare {threshold:12})-[:COMPARED_TO]->(:DR)
(:If)-[:THEN]->(:Outcome)   // hit / defend
(:If)-[:ELSE]->(:Outcome)   // miss / hit-by-enemy
(:If)-[:DOCUMENTED_BY]->(:RulePassage {section_id:'violence-combat'})
```

Promote from pgb if mirrors lag: `operational-spines.json`, `ingest-manifest.json`, this handoff.

---

## ADA next (required)

1. **Select hop:** situation → candidate `If` (`FOR` matching procedure) → read `IF`/`THEN`/`ELSE` + citing `RulePassage`.  
2. Smoke **C1–C3** (Sources + CONTEXT must show spine + violence citation — not prose luck alone):

| Id | Prompt focus |
|---|---|
| **C1** | Melee + Strength + DR **12** |
| **C2** | Ranged / bow + Presence + DR **12** |
| **C3** | Defence + Agility + DR **12** |

3. Report pass/fail + bucket.  
4. **D2** briefing only after C1–C3 green on real edges ([AGENTS.md](../inbox/../) principle 14 — no cowboy retrieval).
