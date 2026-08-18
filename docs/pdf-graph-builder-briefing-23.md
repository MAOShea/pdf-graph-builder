# Briefing 23: Execute D4 — creature sheet materialization

**For pdf-graph-builder agents.** This is the **execute** ticket for altitude-D **D4** (creature sheets). It does **not** change the sheet model.

**Lock (do not rewrite):** [briefing-20](./pdf-graph-builder-briefing-20.md) (2026-08-13). Quoted below so this file is the paste target.

**Why a new briefing:** 20 was written before [briefing-21](./pdf-graph-builder-briefing-21.md) (evidence fan-out) and [briefing-22](./pdf-graph-builder-briefing-22.md) (`SUPERSEDES`). D4 was never filled — there is no D4 handoff. Paste **this** file, not 20.

**Now (2026-08-15):**

| Fact | Source |
|---|---|
| D1–D3 spines green | handoff-15 / 16 / 17 |
| `If-[:SUPERSEDES]->If` green (11 edges; Goblin trio) | [handoff-19](../inbox/ai-dm-assistant-handoff-19.md) |
| ADA `spine_answer` retired | ADA-side only — **not** a pgb task |
| Sheet seed grammar already in ADA | `osr-d20-dc` **0.2.0**; MB `deltas` **0.4.0** |

**Prerequisite (operator, ADA first):** reset + bootstrap so the scaffold has `Creature-[:HAS_HIT_POINTS]->HitPoints` (and the other `HAS_*` rows). Then full Tier-5 dress-up **in pgb** (ingest is only there).

**Do not invent** `HAS_STAT`, free-form `HAS_ATTACK` without the locked target labels, or d20 `ArmorClass` for MB reduce-die armor.

---

## Framing (quoted from briefing-20)

| Side | Role |
|---|---|
| **DM prompt** | “What’s a Goblin’s HP / armor / attack?” |
| **Rulebook** | Bestiary lines on entity passages |
| **pgb** | Materialize sheet slots on creature **instances** via closed `HAS_*` edges |
| **ADA** | Hop instance → sheet nodes into CONTEXT (**after** a green handoff — not in this briefing) |

---

## Locked shape (quoted from briefing-20)

For each creature instance `C` with a parseable bestiary line:

```text
(C)-[:HAS_HIT_POINTS]->(:HitPoints:IngestNode {value: <int>})
(C)-[:HAS_MORALE]->(:Morale:IngestNode {value: <int|null>, none: true?})
(C)-[:HAS_ARMOR]->(:Armor:IngestNode {name: <str>, reduce: <die|null>})   // "No armor" → name only / reduce null
(C)-[:HAS_ATTACK]->(:AttackProfile:IngestNode {name: <str>, damage: <die>})  // one+ edges OK
Each sheet node -[:DOCUMENTED_BY]->(entity RulePassage)  // or C DOCUMENTED_BY is enough if already present
```

**Goblin exemplar** (acceptance — unchanged):

| Slot | Expect |
|---|---|
| HP | `value: 6` |
| Morale | `value: 7` |
| Armor | name ≈ `Ropy skin`, reduce ≈ `d2` |
| Attack | name ≈ `Knife/shortbow`, damage ≈ `d4` |

**Skip** fields the prose lacks (do not invent). Multiple `HAS_ATTACK` when the book lists several attacks.

**Ids:** opaque / stable per `(creature_id, slot, ordinal)` — **no** `goblin-hp` required; creature identity stays on the instance node.

---

## Keep (new since briefing-20 — do not regress)

Full re-ingest must **re-emit** D1–D3 spines and `SUPERSEDES` (handoff-19: materializer `link_creature_dr_supersedes()`). Do not drop override → default edges to land sheets.

| Keep | Why |
|---|---|
| D1 Violence + D2 crit/rest + D3 creature DR `If` spines | D4-P0 |
| `(overrideIf)-[:SUPERSEDES]->(defaultIf)` for same `FOR` | S22 / handoff-19 |
| Entity passages / CREATURES catalog | Sheet `DOCUMENTED_BY` |

---

## Out of scope

| Deferred | Why |
|---|---|
| Changing the `HAS_*` lock | Briefing-20 is the lock |
| D3 DR override spines / opaque `If.id` rewrite | Keep briefing-19 / 22 |
| PC sheets / ability scores on PCs | Same edges exist on `PlayerCharacter`; fill later |
| `ArmorClass` / d20 AC math | Wrong model for MB |
| Generic `HAS_STAT` bag | Forbidden — typed edges only |
| Lore-only Special lines as sheet slots | Cite passage; structured Special later if needed |
| ADA retrieve hops / new `*_answer()` short-circuits | After green handoff; ADA owns that |

---

## Ops path

| Where | What |
|---|---|
| **ADA** | Operator: `reset_db` + `bootstrap`. Confirm scaffold `Creature-[:HAS_HIT_POINTS]->HitPoints` (etc.). Paste **this** briefing to pgb. |
| **pgb** | Full product-path ingest (fiction + D1–D3 + `SUPERSEDES` + **this D4 sheet materialize**). |

1. ADA reset + bootstrap (operator — before this session).
2. Hand **this** briefing to pgb (not briefing-20).
3. pgb: sheet materializer over CREATURES entity passages; closed vocab only; re-emit `SUPERSEDES` with D3.
4. Handoff with Cypher pasted (gates below).

---

## Acceptance gates (handoff must paste results)

### D4-P0 — Prior spines intact (quoted from briefing-20)

```cypher
MATCH (i:If:IngestNode)
WHERE i.id IN ['if:melee-hit-default', 'if:crit-attack']
   OR i.id STARTS WITH 'if:d3-'
RETURN count(i) AS n
```

**Expect:** `n >= 5` (D1 + D2 sample + some D3).

### D4-P1 — Goblin sheet slots (quoted from briefing-20)

```cypher
MATCH (c)-[:INSTANCE_OF]->(:Creature)
WHERE toLower(coalesce(c.name, c.title, '')) = 'goblin'
OPTIONAL MATCH (c)-[:HAS_HIT_POINTS]->(hp:HitPoints)
OPTIONAL MATCH (c)-[:HAS_MORALE]->(m:Morale)
OPTIONAL MATCH (c)-[:HAS_ARMOR]->(a:Armor)
OPTIONAL MATCH (c)-[:HAS_ATTACK]->(atk:AttackProfile)
RETURN coalesce(c.name, c.title) AS creature,
       hp.value AS hp,
       m.value AS morale,
       coalesce(a.name, a.title) AS armor,
       a.reduce AS armor_reduce,
       collect(DISTINCT {name: coalesce(atk.name, atk.title), damage: atk.damage}) AS attacks
```

**Expect:** hp=6, morale=7, armor present with reduce d2, ≥1 attack with damage d4.

### D4-P2 — Batch: at least N creatures with HP (quoted from briefing-20)

```cypher
MATCH (c)-[:HAS_HIT_POINTS]->(:HitPoints)
WHERE (c)-[:INSTANCE_OF]->(:Creature) OR c:Creature OR 'Creature' IN labels(c)
RETURN count(DISTINCT c) AS creatures_with_hp
```

**Expect:** `creatures_with_hp >= 5` (conservative — more is fine).

### D4-P3 — Closed rels (no HAS_STAT) (quoted from briefing-20)

```cypher
MATCH (c)-[r]->()
WHERE (c)-[:INSTANCE_OF]->(:Creature) OR 'Creature' IN labels(c)
  AND type(r) STARTS WITH 'HAS_'
RETURN DISTINCT type(r) AS rel ORDER BY rel
```

**Expect:** only `HAS_HIT_POINTS`, `HAS_MORALE`, `HAS_ARMOR`, `HAS_ATTACK` (plus any pre-existing non-sheet `HAS_*` if present — **not** `HAS_STAT`).

### D4-P4 — SUPERSEDES still present (added; shape from briefing-22 / handoff-19)

```cypher
MATCH ()-[r:SUPERSEDES]->()
RETURN count(r) AS n
```

**Expect:** `n >= 3` (handoff-19 was 11).

```cypher
MATCH (o:If:IngestNode)-[:SUPERSEDES]->(d:If)
MATCH (o)-[:FOR]->(proc)
MATCH (o)-[:`IF`]->(:BoolExpression)-[:HAS_ATOM]->(:Circumstance)-[:APPLIES_TO]->(c)
WHERE toLower(coalesce(c.name, c.title, '')) = 'goblin'
  AND d.id IN ['if:melee-hit-default', 'if:ranged-hit-default', 'if:defence-default']
RETURN coalesce(proc.name, head([l IN labels(proc) WHERE NOT l IN ['IngestNode','SeedNode']])) AS procedure,
       d.id AS default_id
ORDER BY procedure
```

**Expect:** three rows (Melee / Ranged / Defense → matching defaults). Do **not** require a specific override `If.id` — ids stay opaque.

---

## Gate checklist

| Gate | Required |
|---|---|
| Typed sheet edges only | **Required** |
| Goblin exemplar HP 6 / Morale 7 / armor / attack | **Required** |
| Batch CREATURES | **Required** |
| D1–D3 spines intact | **Required** |
| `SUPERSEDES` still present (D4-P4) | **Required** |
| No `ArmorClass` / `HAS_STAT` invention | **Required** |

---

## What ADA will do after a green handoff

1. Retrieval hop: creature in situation → sheet slots into CONTEXT.
2. Smokes S1–S4 (below).
3. PC sheets later.

Do not start those ADA hops until this handoff is green ([AGENTS.md](../../AGENTS.md) principle 14).

---

## Standing smokes (ADA — after handoff; quoted from briefing-20)

| Id | Prompt | Expect in CONTEXT |
|---|---|---|
| **S1** | *What is a Goblin’s HP?* | `HAS_HIT_POINTS` value **6** |
| **S2** | *What armor does a Goblin have?* | Ropy skin / **-d2** (or reduce d2) |
| **S3** | *What does a Goblin attack with?* | Knife/shortbow **d4** |
| **S4** | *What’s a Goblin’s morale?* | **7** |

---

## Sync

`.\scripts\sync-outbox-briefings.ps1` from AI-DM-Assistant root, or paste **this** file into the pgb Cursor session.

---

*Briefing 23 — 2026-08-15 — execute D4 sheets (lock = briefing-20; keep SUPERSEDES)*
