# AI-DM-Assistant Handoff 2: Post-Ingest Schema Changes

**Date:** 2026-07-13  
**Source:** `pdf-graph-builder` scaffold-diff pipeline refinements  
**Relevant project:** AI-DM-Assistant (scaffold bootstrap + graph query layer)

---

## What Changed

After the third Mork Borg ingest run, the scaffold-diff pipeline was refined to produce
cleaner, more actionable contradiction signals. Two changes affect how downstream
consumers (AI-DM-Assistant) should read the graph.

### 1. New relationship type: `POSSIBLE_OVERRIDES_SEED`

The `OVERRIDES_SEED` relationship was being overloaded. The LLM was emitting it for:

- True contradictions (correct use)
- Structural mechanic dependencies ("D20Roll is used for AbilityTest") — false positive
- NPC interactions ("Gorgh defeats Verhu") — false positive

The prompt in `SCAFFOLD_DIFF_INSTRUCTIONS` now enforces a three-tier contradiction model:

| Relationship | Meaning | Action |
|---|---|---|
| `OVERRIDES_SEED` | Confirmed contradiction — rulebook explicitly contradicts the scaffold | Escalate to operator |
| `POSSIBLE_OVERRIDES_SEED` | LLM was uncertain — flagged for human triage | Review before acting |
| `REFERENCES` | Structural mechanic dependency ("X is used for Y") | Informational only |

`POSSIBLE_OVERRIDES_SEED` is a new type. It will appear in the graph from the next ingest onwards.

### 2. `OVERRIDES_SEED` is now stricter

Previous ingests may contain false-positive `OVERRIDES_SEED` relationships.
Before relying on `OVERRIDES_SEED` data, clear the existing ones and re-ingest:

```cypher
MATCH ()-[r:OVERRIDES_SEED]->() DELETE r;
MATCH (n:IngestNode) DETACH DELETE n;
```

---

## What AI-DM-Assistant Needs to Update

### Seeding code — no changes needed

The scaffold bootstrap process (what AI-DM-Assistant writes into Neo4j) is unchanged.
It still produces `SeedNode` nodes with `coverage: "research-only"` and `SPECIALIZES`
relationships. No seeding code needs to be touched.

### Graph query code — add `POSSIBLE_OVERRIDES_SEED`

Any query that surfaces contradictions to the DM must now include both types.

**Before:**
```cypher
MATCH (a)-[:OVERRIDES_SEED]->(b)
RETURN a.name AS from, b.name AS to
```

**After:**
```cypher
MATCH (a)-[r:OVERRIDES_SEED|POSSIBLE_OVERRIDES_SEED]->(b)
RETURN a.name AS from, type(r) AS signal, b.name AS to
ORDER BY signal
```

The `signal` column lets the DM UI distinguish confirmed contradictions
from ones that still need human review.

### Suggested DM-facing presentation

| Signal | UI treatment |
|---|---|
| `OVERRIDES_SEED` | Show as a rule conflict alert (red) |
| `POSSIBLE_OVERRIDES_SEED` | Show as "needs review" notice (amber) — do not auto-surface to players |
| `REFERENCES` | Do not surface — internal mechanic wiring only |

---

## Bloom Perspective

`docs/Scaffold Diff.json` has been updated with visual styling for all three types:

| Relationship | Colour |
|---|---|
| `CONFIRMS_SEED` | Green `#22c55e` |
| `OVERRIDES_SEED` | Red `#ef4444` |
| `POSSIBLE_OVERRIDES_SEED` | Amber `#f59e0b` |
| `INSTANCE_OF` | Purple `#a855f7` |

Re-import the perspective in Bloom (delete the old one first, then import `docs/Scaffold Diff.json`).

Triage query for the amber relationships after re-ingest:

```cypher
MATCH (a)-[r:POSSIBLE_OVERRIDES_SEED]->(b)
RETURN a.name AS from, b.name AS to
ORDER BY a.name
```

---

## Full Relationship Type Glossary (post-ingest graph)

| Type | Created by | Meaning |
|---|---|---|
| `SPECIALIZES` | Scaffold bootstrap | Concept is a subtype of another scaffold concept |
| `CONFIRMS_SEED` | Ingest | PDF chunk confirms a scaffold concept |
| `OVERRIDES_SEED` | Ingest | PDF explicitly contradicts a scaffold claim |
| `POSSIBLE_OVERRIDES_SEED` | Ingest | Uncertain — LLM flagged for triage |
| `INSTANCE_OF` | Ingest | Named entity is a concrete instance of a scaffold concept |
| `DOCUMENTED_BY` | Ingest | Node is evidenced by a specific PDF chunk |
| `REFERENCES` | Ingest | Structural mechanic dependency |
| `PART_OF` | Chunking | Chunk belongs to a Document |
| `NEXT_CHUNK` | Chunking | Sequential chunk ordering |
| `HAS_ENTITY` | Ingest (bottom-up) | Chunk contains an extracted entity |
