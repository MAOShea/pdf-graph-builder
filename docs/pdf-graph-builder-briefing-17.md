# Briefing 17: Altitude D — materialize Violence `If` spines (D1)

**For pdf-graph-builder agents.** First **operational fill** under altitude D ([DESIGN §8.2.4](../../DESIGN.md#824-altitude-d-build-plan-dependency-order), [OQ-SEED-08](../../DESIGN.md#154-seed-ontology-governance)).

**Prerequisite (ADA, before / during your run):** operator has **reset + bootstrapped** Mörk Borg so Neo4j scaffold includes Tier-0 spine labels (`If`, `BoolExpression`, `Circumstance`, `Compare`) and rels (`FOR`, `IF`, `THEN`, `ELSE`, `HAS_ATOM`). Seeds: `corpus/seeds/universal/ludemes.json` **v0.4.0** + `d20-core` / `osr-d20-dc` wiring. If those `:SeedNode` labels are missing, **stop** and ask ADA to finish D0.4 — do not invent substitute types.

**Prior context:** [briefing-14](./pdf-graph-builder-briefing-14.md) (Violence parse/chunk), [briefing-16](./pdf-graph-builder-briefing-16.md) (catalog→section). D1 **consumes** `violence-combat` passages; it does not replace section/catalog gates.

---

## Framing (do not dilute)

| Side | Role |
|---|---|
| **DM prompt** | Situation to analyse — **not** an IF/THEN/ELSE |
| **Rulebook** | Library of adjudicable **`If` spines** |
| **pgb** | Materialize those spines from Bare Bones + cite passages |
| **ADA (later)** | **Select** which spine(s) apply from the prompt |

Encode **rules**, not prompts. Closed vocabulary only — **no** open LLM-invented predicates or parallel “DR property on MeleeAttack” shortcuts that bypass `Compare`.

---

## Closed vocabulary (scaffold — do not invent)

**Nodes:** `If`, `BoolExpression`, `Circumstance`, `Compare`, `Outcome` (existing), plus existing `MeleeAttack` / `RangedAttack` / `DefenseRoll` / `DifficultyRating` / `DR`.

**Rels:**

| Rel | From → To | Notes |
|---|---|---|
| `FOR` | `If` → procedure seed | MeleeAttack / RangedAttack / DefenseRoll |
| `IF` | `If` → `BoolExpression` | Exactly one guard |
| `THEN` / `ELSE` | `If` → `Outcome` | ELSE optional if book silent |
| `HAS_ATOM` | `BoolExpression` → `Circumstance` \| `Compare` | Composition B |
| `COMPARED_TO` | `Compare` → `DifficultyRating` / `DR` | Reuse; threshold **12** for normal Violence |

**Property:** `BoolExpression.combinator` ∈ {`LEAF`, `AND`, `OR`, `NOT`}. D1 default melee/ranged/defence = `LEAF`.

**Not in this briefing:** status `Condition` (d20 character status). Do not overload it for guards.

**Evidence (required on every spine):** `DOCUMENTED_BY` and/or `CONFIRMS_SEED` → `RulePassage` in section `violence-combat` (prefer passage nodes over raw page Chunks).

---

## D1 scope — what to materialize

Bare Bones **Violence** (section `violence-combat`). Three spines minimum:

### 1. Melee hit (DR 12)

```text
(:If)-[:FOR]->(:MeleeAttack)
(:If)-[:IF]->(:BoolExpression {combinator: "LEAF"})
(:BoolExpression)-[:HAS_ATOM]->(:Compare)
(:Compare)-[:COMPARED_TO]->(:DR|DifficultyRating)   // threshold / normal DR 12
(:If)-[:THEN]->(:Outcome)   // hit (name/id stable; prose in properties OK)
(:If)-[:ELSE]->(:Outcome)   // miss
```

Book cue: melee / Test Strength DR12 (and existing seed `MeleeAttack`-`APPLIES_TO`-`Strength` — do not re-derive ability in a new ad hoc edge).

### 2. Ranged hit (DR 12)

Same shape with `FOR` → `RangedAttack` (Presence binding already in Tier-4 seeds).

### 3. Defence (DR 12)

Same shape with `FOR` → `DefenseRoll` (Agility binding already in seeds).

**Instance identity:** use stable ids/names (e.g. `if:melee-hit-default`, `compare:melee-dr12`) so re-ingest merges cleanly. Mark Tier-5 / `:IngestNode` (or your existing ingest labels) — do not overwrite `:SeedNode` concept rows.

---

## Out of scope (do not do in this briefing)

| Deferred | Why |
|---|---|
| Crit / fumble / rest / infection spines | **D2** — same metamodel, later briefing |
| Goblin DR14 / `Circumstance` “fighting Goblin” | **D3** / creature sheet lane |
| Natural-20 `Compare` crit spine | **D2** |
| Lore edges, creature-type taxonomies | Never for D1 |
| Changing ADA `ludemes.json` | Gap → handoff report; ADA fixes seeds + reset/bootstrap |
| Cowboy “MeleeAttack.dr = 12” without `If`/`Compare` | Violates locked metamodel |

---

## Ops path

1. Confirm scaffold: `MATCH (n:SeedNode) WHERE n.name IN ['If','BoolExpression','Compare','Circumstance'] RETURN n.name` — four rows.
2. Full `POST /extract` via `.\ingest-morkborg.ps1` with **`section_phase` ≥ 2** so `violence-combat` exists ([briefing-13](./pdf-graph-builder-briefing-13.md)). Prefer product path over `materialize-*` CLIs alone.
3. Implement / extend an **operational spine materializer** (or constrained extract emit) that creates the three `If` graphs above and wires evidence.
4. Keep catalog→section for Attack / Melee / Ranged / Defence → `violence-combat` green ([briefing-16](./pdf-graph-builder-briefing-16.md) optional table).
5. Author handoff with **acceptance Cypher results pasted**. Do not say “ball with ADA” until gates below are green.

**Contract SoT:** `passage-sections.json` / `ingest-manifest.json` remain pgb-authored; ADA only promotes mirrors. This briefing does **not** require new section contracts if `violence-combat` + passages already pass briefing-14 gates.

---

## Acceptance gates (handoff must paste results)

### D1-P0 — Scaffold present

```cypher
MATCH (n:SeedNode)
WHERE n.name IN ['If', 'BoolExpression', 'Compare', 'Circumstance']
RETURN n.name
ORDER BY n.name
```

**Expect:** 4 rows. If not → stop; ADA D0.4 incomplete.

### D1-P1 — Three procedure spines with DR12 Compare

```cypher
MATCH (i:If)-[:FOR]->(proc)
WHERE proc.name IN ['MeleeAttack', 'RangedAttack', 'DefenseRoll']
  OR 'MeleeAttack' IN labels(proc) OR 'RangedAttack' IN labels(proc) OR 'DefenseRoll' IN labels(proc)
MATCH (i)-[:IF]->(b:BoolExpression)-[:HAS_ATOM]->(c:Compare)
OPTIONAL MATCH (c)-[:COMPARED_TO]->(dr)
OPTIONAL MATCH (i)-[:THEN]->(t)
OPTIONAL MATCH (i)-[:ELSE]->(e)
RETURN coalesce(proc.name, labels(proc)[0]) AS procedure,
       b.combinator AS combinator,
       coalesce(dr.name, dr.value, c.threshold, c.right) AS threshold,
       count(DISTINCT t) AS then_count,
       count(DISTINCT e) AS else_count
ORDER BY procedure
```

**Expect:** one row each for MeleeAttack, RangedAttack, DefenseRoll; combinator `LEAF` (or null→treat as LEAF); threshold **12**; `then_count` ≥ 1; `else_count` ≥ 1 preferred.

Adjust property names (`threshold` / `value`) to whatever you emit — handoff must document the property used and still prove **12**.

### D1-P2 — Evidence into violence-combat

```cypher
MATCH (i:If)-[:FOR]->(proc)
WHERE coalesce(proc.name, '') IN ['MeleeAttack', 'RangedAttack', 'DefenseRoll']
   OR any(l IN labels(proc) WHERE l IN ['MeleeAttack', 'RangedAttack', 'DefenseRoll'])
MATCH (i)-[:DOCUMENTED_BY|CONFIRMS_SEED]->(p:RulePassage)
WHERE p.section_id = 'violence-combat'
   OR p.id CONTAINS 'violence-combat'
RETURN coalesce(proc.name, labels(proc)[0]) AS procedure, count(DISTINCT p) AS passages
ORDER BY procedure
```

**Expect:** ≥ 1 passage per procedure. Evidence may hang on `If`, `Compare`, or `Outcome` — if you attach only to children, extend the MATCH accordingly and paste the working query.

### D1-P3 — No vocabulary leakage

```cypher
// Rel types on If / BoolExpression / Compare created this ingest — sample
MATCH (i:If)-[r]->()
WHERE NOT type(r) IN ['FOR', 'IF', 'THEN', 'ELSE', 'DOCUMENTED_BY', 'CONFIRMS_SEED', 'INSTANCE_OF']
RETURN DISTINCT type(r) AS unexpected_rel
```

**Expect:** zero unexpected spine rels (empty result). Fix emit if anything else appears for the guard chain.

---

## Gate checklist (handoff)

| Gate | Required |
|---|---|
| Briefing-14 Violence section/passages | Keep green |
| Catalog→`violence-combat` for Attack/Melee/Ranged/Defence | Preferred green |
| **D1-P0** SeedNode spine labels | **Required** |
| **D1-P1** Three `If` spines + Compare→12 | **Required** |
| **D1-P2** Evidence → `violence-combat` | **Required** |
| **D1-P3** Closed rel set | **Required** |

**Handoff must not say “ball with ADA” until D1-P0–P3 are green with pasted Cypher.**

---

## What ADA will do after a green handoff

1. Add retrieval hop: situation → candidate `If` (`FOR` procedure) → `IF`/`THEN`/`ELSE` + citing passage (standing combat smokes C1–C3).  
2. **Not** paper over missing spines in `retrieval.py` ([AGENTS.md](../../AGENTS.md) principle 14).  
3. Open **D2** briefing (crit/fumble/rest/infection) only after D1 is green.

---

## Standing smokes (ADA, after handoff)

| ID | Prompt | CONTEXT / graph should support |
|---|---|---|
| C1 | *How does a melee attack work? … what's the DR?* | `If` FOR MeleeAttack → Compare threshold 12 + `violence-combat` citation |
| C2 | *I shoot a bow — which ability and DR?* | RangedAttack spine + Presence (seed) + DR12 |
| C3 | *How do I defend? …* | DefenseRoll spine + Agility + DR12 |

Judge Sources + Retrieved context first; answer prose alone is insufficient.

---

## Sync

After ADA authors this file: `.\scripts\sync-outbox-briefings.ps1` from AI-DM-Assistant root (or paste this briefing into the pgb Cursor session). Reply with `docs/inbox/ai-dm-assistant-handoff-*.md` (or pgb `docs/` equivalent for ADA to copy).
