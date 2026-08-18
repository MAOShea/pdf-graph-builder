# AI-DM-Assistant Handoff 19: `SUPERSEDES` D3 override → D1 default

**From:** pdf-graph-builder  
**Date:** 2026-08-14  
**Context:** [Briefing 22](./pdf-graph-builder-briefing-22.md) / [handoff-17](./ai-dm-assistant-handoff-17.md) / [handoff-18](./ai-dm-assistant-handoff-18.md).

**Verdict:** **S22 green** — every D3 Violence override `If` now `[:SUPERSEDES]->` the matching D1 default. **Live MERGE-only** (no ADA reset, no full re-ingest). D1–D3 spines intact. **Ball is with ADA** — demote superseded defaults in CONTEXT; skip seed-evidence when selected spine has outgoing `SUPERSEDES`. Re-smoke `cli_chat --suite d3 --check-context`.

---

## Ops (what we did)

| Action | Done? |
|---|---|
| ADA reset + bootstrap | **No** (live fill; scaffold triplet optional for this MERGE) |
| Full `.\ingest-morkborg.ps1` | **No** |
| pgb live `SUPERSEDES` MERGE | **Yes** — `backend/materialize_spine_supersedes.py` |

```powershell
backend\venv\Scripts\python.exe backend\materialize_spine_supersedes.py
```

Future full spine materialize (`section_phase >= 2` or `materialize_operational_spines`) re-emits these edges via `link_creature_dr_supersedes()`.

---

## What pgb shipped

| Item | Detail |
|---|---|
| Contract | `operational-spines.json` **v0.3.1** |
| Materializer | `link_creature_dr_supersedes()` — map `MeleeAttack`→`if:melee-hit-default`, `RangedAttack`→`if:ranged-hit-default`, `DefenseRoll`→`if:defence-default` |
| Live CLI | `backend/materialize_spine_supersedes.py` |
| Constants | `SUPERSEDES` added to `INGEST_REL_TYPES` |

**Fill mode:** live MERGE-only on existing D3 + D1 spines (`d3_supersedes_links` = **11**).

---

## Acceptance Cypher (pasted)

### S22-P0 — SUPERSEDES count

```cypher
MATCH ()-[r:SUPERSEDES]->()
RETURN count(r) AS n
```

| n |
|---|
| **11** |

### S22-P1 — Goblin defence supersedes default

```cypher
MATCH (o:If:IngestNode)-[:FOR]->(:DefenseRoll)
MATCH (o)-[:`IF`]->(:BoolExpression)-[:HAS_ATOM]->(:Circumstance)-[:APPLIES_TO]->(c)
WHERE toLower(coalesce(c.name, c.title, '')) = 'goblin'
MATCH (o)-[:SUPERSEDES]->(d:If {id: 'if:defence-default'})
RETURN o.id AS override_id, d.id AS default_id
```

| override_id | default_id |
|---|---|
| `if:d3-2393b8d674143b52` | `if:defence-default` |

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

| procedure | default_id | override_id |
|---|---|---|
| DefenseRoll | `if:defence-default` | `if:d3-2393b8d674143b52` |
| MeleeAttack | `if:melee-hit-default` | `if:d3-0724f59052a53acd` |
| RangedAttack | `if:ranged-hit-default` | `if:d3-795bad78deaf9b85` |

### S22-P3 — D1–D3 spines intact

```cypher
MATCH (i:If:IngestNode)
WHERE i.id IN ['if:melee-hit-default', 'if:defence-default']
   OR i.id STARTS WITH 'if:d3-'
RETURN count(i) AS spines
```

| spines |
|---|
| **13** |

---

## Gate checklist

| Gate | Status |
|---|---|
| S22-P0 `n >= 3` | ✅ (11) |
| S22-P1 Goblin defence | ✅ |
| S22-P2 Goblin trio | ✅ |
| S22-P3 spines intact | ✅ |
| Fill mode documented | ✅ live MERGE-only |

---

## ADA next

1. Prefer override spines with outgoing `SUPERSEDES`; drop superseded defaults from CONTEXT.  
2. When a selected spine has `SUPERSEDES`, skip competing Violence seed-evidence dump (same spirit as briefing-21).  
3. Re-smoke **d3** (+ optional `--no-short-circuit`) — Goblin should cite DR14 override and show `SUPERSEDES: if:…-default`, not DR12 drowning CONTEXT.  
4. On next full rebuild: ADA reset+bootstrap (ludemes 0.4.2 scaffold triplet) then pgb dress-up; materializer will re-emit `SUPERSEDES` with D3.

Promote: this handoff → ADA `docs/inbox/`.
