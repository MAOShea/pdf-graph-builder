# Briefing 22: Altitude D — `SUPERSEDES` between override and default `If` spines

**For pdf-graph-builder agents.** Follow-on to D3 creature DR overrides ([briefing-19](./pdf-graph-builder-briefing-19.md) / [handoff-17](../inbox/ai-dm-assistant-handoff-17.md)). Wire explicit **exception precedence** so ADA can demote default Violence spines (and skip competing seed-evidence) when a creature override applies.

**Prerequisite:** D1–D3 spines already in the DB. **ADA seed grammar updated:** `ludemes` **0.4.2** adds scaffold `If-[:SUPERSEDES]->If`. Operator must **reset + bootstrap** in ADA before relying on the scaffold triplet (Tier 0 change). Then Tier-5 fill in **pgb** only — no need to re-emit entire D3 spines if they already exist; **add `SUPERSEDES` edges**.

**Do not confuse with:**

| Type | Job |
|---|---|
| `OVERRIDES` | Tier-4 ontology (e.g. `CreatureTest` → `AbilityTest`) |
| `OVERRIDES_SEED` | Ingest conflict report — not a chat edge |
| **`SUPERSEDES`** | Altitude **D**: more specific **`If`** wins over default **`If`** |

---

## Framing

| Side | Role |
|---|---|
| **DM prompt** | “I defend against a Goblin — DR?” |
| **Rulebook** | Default DR12 + creature Special DR14 |
| **pgb** | `(overrideIf)-[:SUPERSEDES]->(defaultIf)` for same `FOR` procedure |
| **ADA** | Drop superseded defaults from CONTEXT; skip seed-evidence when a selected spine has outgoing `SUPERSEDES` |

---

## Required edges (Tier-5)

For each D3 creature override `If` that `FOR`s a Violence procedure, link to the matching D1 default:

| Override `FOR` | Default target `If.id` |
|---|---|
| `MeleeAttack` | `if:melee-hit-default` |
| `RangedAttack` | `if:ranged-hit-default` |
| `DefenseRoll` | `if:defence-default` |

```text
(:If:IngestNode {id: <opaque d3>})-[:SUPERSEDES]->(:If {id: 'if:melee-hit-default'})
(:If:IngestNode {id: <opaque d3>})-[:SUPERSEDES]->(:If {id: 'if:ranged-hit-default'})
(:If:IngestNode {id: <opaque d3>})-[:SUPERSEDES]->(:If {id: 'if:defence-default'})
```

**Goblin exemplar:** three override spines (melee / ranged / defence, threshold 14) each `SUPERSEDES` the matching default above.

**Match targets by `If.id` (defaults) or by graph shape** — do not invent new default ids.

**Skip** D2 spines (crit / fumble / rest) — no `SUPERSEDES` required for this briefing unless a clear book exception exists later.

---

## Ops path

| Where | What |
|---|---|
| **ADA** | `reset_db` + `bootstrap` after `ludemes` 0.4.2 pull (new scaffold triplet). Confirm `If-[:SUPERSEDES]->If` exists on SeedNodes. Paste this briefing to pgb. |
| **pgb** | Emit `SUPERSEDES` for existing D3 overrides → D1 defaults. Prefer a small materializer / repair script over full re-extract if spines are already green. |
| **ADA after handoff** | Re-smoke `cli_chat --suite d3 --check-context` (+ optional `--no-short-circuit`). Goblin CONTEXT should show `SUPERSEDES: if:…-default` and **no** seed-evidence Violence dump competing. |

**Note:** A full reset wipes Tier-5. If you reset for the scaffold, you must re-run D1–D3 (and D4 if in scope) ingest afterward — or only bootstrap on a DB that will be re-dressed. If the live DB already has D1–D3 and you only need edges, ADA can bootstrap after reset **or** pgb can MERGE `SUPERSEDES` without waiting for scaffold (Neo4j allows the rel type without the seed triplet), but **product policy** is: scaffold first, then ingest.

Recommended operator sequence when the DB already has spines you want to keep:

1. Prefer **pgb-only** `SUPERSEDES` MERGE on the live DB (rel type need not pre-exist as a seed edge for MERGE to work).  
2. ADA reset+bootstrap when next doing a full rebuild (D4) so scaffold includes `SUPERSEDES`.  
3. On that rebuild, pgb re-emits D3 **with** `SUPERSEDES` in the same pass.

If operator chooses reset now: ADA reset+bootstrap → pgb full dress-up including this briefing.

---

## Acceptance gates (handoff must paste results)

### S22-P0 — Scaffold or live: SUPERSEDES exists as a type (optional if live-only fill)

```cypher
MATCH ()-[r:SUPERSEDES]->()
RETURN count(r) AS n
```

**Expect after fill:** `n >= 3` (Goblin trio minimum; more if other creatures linked).

### S22-P1 — Goblin defence supersedes default

```cypher
MATCH (o:If:IngestNode)-[:FOR]->(:DefenseRoll)
MATCH (o)-[:`IF`]->(:BoolExpression)-[:HAS_ATOM]->(:Circumstance)-[:APPLIES_TO]->(c)
WHERE toLower(coalesce(c.name, c.title, '')) = 'goblin'
MATCH (o)-[:SUPERSEDES]->(d:If {id: 'if:defence-default'})
RETURN o.id AS override_id, d.id AS default_id
```

**Expect:** one row.

### S22-P2 — Goblin melee + ranged likewise

```cypher
MATCH (o:If:IngestNode)-[:SUPERSEDES]->(d:If)
MATCH (o)-[:FOR]->(proc)
MATCH (o)-[:`IF`]->(:BoolExpression)-[:HAS_ATOM]->(:Circumstance)-[:APPLIES_TO]->(c)
WHERE toLower(coalesce(c.name, c.title, '')) = 'goblin'
  AND d.id IN ['if:melee-hit-default', 'if:ranged-hit-default', 'if:defence-default']
RETURN coalesce(proc.name, head([l IN labels(proc) WHERE NOT l IN ['IngestNode','SeedNode']])) AS procedure,
       d.id AS default_id,
       o.id AS override_id
ORDER BY procedure
```

**Expect:** three rows (Melee / Ranged / Defense → matching defaults).

### S22-P3 — D1–D3 spines still intact

```cypher
MATCH (i:If:IngestNode)
WHERE i.id IN ['if:melee-hit-default', 'if:defence-default']
   OR i.id STARTS WITH 'if:d3-'
RETURN count(i) AS spines
```

**Expect:** `spines >= 5`.

---

## Out of scope

| Deferred | Why |
|---|---|
| Rewriting D3 identity / opaque ids | Keep briefing-19 |
| D4 sheets | [briefing-20](./pdf-graph-builder-briefing-20.md) |
| `SUPERSEDES` for non-combat exceptions | Later |
| ADA inventing `SUPERSEDES` without graph | Forbidden — graph only |

---

## Handoff checklist

- [ ] S22-P0 / P1 / P2 / P3 green (paste Cypher results)
- [ ] Document whether fill was live MERGE-only or post-reset re-ingest
- [ ] Handoff → ADA `docs/inbox/`
- [ ] ADA re-smoke d3 (+ optional `--no-short-circuit`)

---

*Briefing 22 — 2026-08-14 — If SUPERSEDES If (creature DR exception precedence)*
