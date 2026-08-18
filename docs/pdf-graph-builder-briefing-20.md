# Briefing 20: Altitude D — creature sheet materialization (D4)

> **Lock only.** Execute via **[briefing-23](./pdf-graph-builder-briefing-23.md)** (2026-08-15). Do not paste this file as the current pgb request.

**For pdf-graph-builder agents.** Fourth **operational fill** under altitude D ([DESIGN §8.2.4](../../DESIGN.md#824-altitude-d-build-plan-dependency-order)). Builds on D3 creature instances ([handoff-17](../inbox/ai-dm-assistant-handoff-17.md) / [briefing-19](./pdf-graph-builder-briefing-19.md)).

**Prerequisite:** D1–D3 green. CREATURES entity passages exist. **ADA seed grammar updated:**

| File | Version | Adds |
|---|---|---|
| `frameworks/osr-d20-dc.json` | **0.2.0** | `HitPoints`, `Morale`, `Armor`, `AttackProfile`; `Monster`/`PlayerCharacter` → `HAS_HIT_POINTS` / `HAS_MORALE` / `HAS_ARMOR` / `HAS_ATTACK` |
| `games/mork-borg/deltas.json` | **0.4.0** | Same edges from book-vocab `Creature` |

Operator must **reset + bootstrap** in ADA before this fill (new scaffold edges). Then full Tier-5 dress-up in **pgb** (ingest is only here).

**Do not invent** `HAS_STAT`, `HAS_ATTACK` as free-form without the locked target labels, or d20 `ArmorClass` for MB reduce-die armor.

---

## Framing

| Side | Role |
|---|---|
| **DM prompt** | “What’s a Goblin’s HP / armor / attack?” |
| **Rulebook** | Bestiary lines on entity passages |
| **pgb** | Materialize sheet slots on creature **instances** via closed `HAS_*` edges |
| **ADA** | Hop instance → sheet nodes into CONTEXT (after handoff) |

---

## Locked shape (batch CREATURES)

For each creature instance `C` with a parseable bestiary line:

```text
(C)-[:HAS_HIT_POINTS]->(:HitPoints:IngestNode {value: <int>})
(C)-[:HAS_MORALE]->(:Morale:IngestNode {value: <int|null>, none: true?})
(C)-[:HAS_ARMOR]->(:Armor:IngestNode {name: <str>, reduce: <die|null>})   // "No armor" → name only / reduce null
(C)-[:HAS_ATTACK]->(:AttackProfile:IngestNode {name: <str>, damage: <die>})  // one+ edges OK
Each sheet node -[:DOCUMENTED_BY]->(entity RulePassage)  // or C DOCUMENTED_BY is enough if already present
```

**Goblin exemplar** (acceptance):

| Slot | Expect |
|---|---|
| HP | `value: 6` |
| Morale | `value: 7` |
| Armor | name ≈ `Ropy skin`, reduce ≈ `d2` |
| Attack | name ≈ `Knife/shortbow`, damage ≈ `d4` |

**Skip** fields the prose lacks (do not invent). Multiple `HAS_ATTACK` when the book lists several attacks.

**Ids:** opaque / stable per `(creature_id, slot, ordinal)` — **no** `goblin-hp` required; creature identity stays on the instance node.

---

## Out of scope

| Deferred | Why |
|---|---|
| D3 DR override spines | Keep |
| PC sheets / ability scores on PCs | Same edges exist on `PlayerCharacter`; fill later |
| `ArmorClass` / d20 AC math | Wrong model for MB |
| Generic `HAS_STAT` bag | Forbidden — typed edges only |
| Lore-only Special lines as sheet slots | Cite passage; structured Special later if needed |

---

## Ops path

| Where | What |
|---|---|
| **ADA** | `reset_db` + `bootstrap` after seed pull; confirm scaffold has `Creature-[:HAS_HIT_POINTS]->HitPoints` (etc.). Paste this briefing to pgb. |
| **pgb** | Full product-path ingest (fiction + D1–D3 + **this D4 sheet materialize**). |

1. ADA reset + bootstrap.  
2. Hand this briefing to pgb.  
3. pgb: sheet materializer over CREATURES entity passages; closed vocab only.  
4. Handoff with Cypher pasted (gates below).

---

## Acceptance gates (handoff must paste results)

### D4-P0 — Prior spines intact

```cypher
MATCH (i:If:IngestNode)
WHERE i.id IN ['if:melee-hit-default', 'if:crit-attack']
   OR i.id STARTS WITH 'if:d3-'
RETURN count(i) AS n
```

**Expect:** `n >= 5` (D1 + D2 sample + some D3).

### D4-P1 — Goblin sheet slots

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

### D4-P2 — Batch: at least N creatures with HP

```cypher
MATCH (c)-[:HAS_HIT_POINTS]->(:HitPoints)
WHERE (c)-[:INSTANCE_OF]->(:Creature) OR c:Creature OR 'Creature' IN labels(c)
RETURN count(DISTINCT c) AS creatures_with_hp
```

**Expect:** `creatures_with_hp >= 5` (conservative — more is fine).

### D4-P3 — Closed rels (no HAS_STAT)

```cypher
MATCH (c)-[r]->()
WHERE (c)-[:INSTANCE_OF]->(:Creature) OR 'Creature' IN labels(c)
  AND type(r) STARTS WITH 'HAS_'
RETURN DISTINCT type(r) AS rel ORDER BY rel
```

**Expect:** only `HAS_HIT_POINTS`, `HAS_MORALE`, `HAS_ARMOR`, `HAS_ATTACK` (plus any pre-existing non-sheet `HAS_*` if present — **not** `HAS_STAT`).

---

## Gate checklist

| Gate | Required |
|---|---|
| Typed sheet edges only | **Required** |
| Goblin exemplar HP 6 / Morale 7 / armor / attack | **Required** |
| Batch CREATURES | **Required** |
| D1–D3 spines intact | **Required** |
| No `ArmorClass` / `HAS_STAT` invention | **Required** |

---

## What ADA will do after a green handoff

1. Retrieval hop: creature in situation → sheet slots into CONTEXT.  
2. Smokes: Goblin HP / armor / attack questions.  
3. PC sheets later.

---

## Standing smokes (ADA)

| Id | Prompt | Expect in CONTEXT |
|---|---|---|
| **S1** | *What is a Goblin’s HP?* | `HAS_HIT_POINTS` value **6** |
| **S2** | *What armor does a Goblin have?* | Ropy skin / **-d2** (or reduce d2) |
| **S3** | *What does a Goblin attack with?* | Knife/shortbow **d4** |
| **S4** | *What’s a Goblin’s morale?* | **7** |

---

## Sync

`.\scripts\sync-outbox-briefings.ps1` from AI-DM-Assistant root, or paste into the pgb Cursor session.
