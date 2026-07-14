# AI-DM-Assistant Handoff 3: Contradiction Signals & Graph Consumption

**Context:** This follows [Briefing 2](./pdf-graph-builder-briefing-2.md) (inbound) and the fourth (clean) ingest run documented in [Handoff 1](./ai-dm-assistant-handoff-1.md). The ingest pipeline is now stable. This handoff describes schema changes AI-DM-Assistant must account for when reading the graph, and the new worldbuilding data surfaced by the ingest that the scaffold should eventually absorb.

---

## What Is Now in the Graph

After the fourth ingest of `mork-borg.pdf` against the `morkborg` database:

| Node/Rel type | Count | Meaning |
|---|---|---|
| `SeedNode` (ingest-confirmed) | 56 | Scaffold concepts confirmed by the rulebook |
| `SeedNode` (research-only) | 0 | All seeds covered |
| `IngestNode` | 57 | Concrete named entities from the rulebook |
| `CONFIRMS_SEED` | 56 | PDF chunk → scaffold concept confirmations |
| `INSTANCE_OF` | 57 | IngestNode → scaffold concept links |
| `DOCUMENTED_BY` | 57+ | Node → PDF chunk evidence links |
| `OVERRIDES_SEED` | 0 | No confirmed contradictions |
| `POSSIBLE_OVERRIDES_SEED` | 0 | No uncertain contradictions |
| `REFERENCES` | 1 | One structural mechanic dependency |
| `FlaggedRelationship` | 12 | LLM-invented rel types not in the scaffold |
| `FlaggedConcept` | 0 | No unrecognised node labels |

---

## New: Three-Tier Contradiction Model

Previous ingests overloaded `OVERRIDES_SEED` with false positives (structural mechanic relationships, NPC interactions). The pipeline prompt has been tightened. The contradiction signal set is now:

| Relationship | Trigger | AI-DM-Assistant action |
|---|---|---|
| `OVERRIDES_SEED` | Rulebook text explicitly contradicts a scaffold claim | Surface as a rule conflict alert to the DM (red) |
| `POSSIBLE_OVERRIDES_SEED` | LLM was uncertain — flagged for triage | Show as "needs review" notice to operator (amber); do not surface to players |
| `REFERENCES` | Structural mechanic dependency ("X is used for Y") | Do not surface — internal wiring only |

**Query for contradiction review:**
```cypher
MATCH (a)-[r:OVERRIDES_SEED|POSSIBLE_OVERRIDES_SEED]->(b)
RETURN a.name AS from, type(r) AS signal, b.name AS to
ORDER BY signal
```

---

## New: IngestNode Instances

The 57 `IngestNode` nodes are concrete named entities from the rulebook — places, NPCs, items, specific mechanics. They are linked to scaffold concepts via `INSTANCE_OF` and to PDF chunks via `DOCUMENTED_BY`.

**Query pattern for grounded answers:**
```cypher
-- Find all named entities of a given scaffold type
MATCH (n:IngestNode)-[:INSTANCE_OF]->(s)
WHERE s.seed_id = $concept
RETURN n.name, n

-- Retrieve the PDF chunk that backs up a scaffold concept
MATCH (seed)<-[:CONFIRMS_SEED]-(chunk:Chunk)
WHERE seed.coverage = 'ingest-confirmed' AND seed.seed_id = $concept
RETURN seed.name, chunk.text ORDER BY chunk.position
```

**Prefer `ingest-confirmed` nodes** for answers about game rules. Do not rely on `research-only` seeds for rule answers — those are unverified scaffold claims.

---

## FlaggedRelationship Nodes — Worldbuilding to Absorb

12 relationship types were flagged as `NEW_REL` — the LLM extracted them from the rulebook text but they are not in the scaffold's permitted set. These are legitimate worldbuilding relationships that the scaffold did not anticipate:

| From | Rel type | To | Notes |
|---|---|---|---|
| Josilfa Migol | RULESREFERENCE | Galgenbeck | NPC rules reference |
| Two-Headed Basilisks | RULESREFERENCE | Nechrubel | Creature rules reference |
| Mörk Borg | LOCATION | Valley Of The Unfortunate Undead | Setting geography |
| Fathmu's Men | OCCUPANT | Valley Of The Unfortunate Undead | Faction location |
| Morkborgedition | ISSUED | Mörkborg Bare Bones Edition | Edition relationship |
| Occult Treasures | HAS_ITEM | Famine Spoon | Treasure table entry |
| Mörk Borg | RESIDENCY | Dark Fort | Setting geography |
| Basilisk | TWIN | Arkh | Named NPC relationship |
| Basilisk | TWIN | Gorgh | Named NPC relationship |
| Mork-Borg-Deltas | CAUSES | Paranoid-Mind | Lore causality |
| Fathmu-Men | IS_RESPONSIBLE_FOR | Valley-Of-The-Unfortunate-Undead | Faction lore |
| Mörk Borg | GMNARRATION | Bare Bones Edition 1 | Edition narration |

**Recommended action for AI-DM-Assistant:** promote the legitimate ones (`TWIN`, `LOCATION`, `OCCUPANT`, `HAS_ITEM`) into the Mork Borg-specific scaffold layer, then re-ingest so they are captured as proper `IngestNode` relationships rather than flags.

Query to retrieve them:
```cypher
MATCH (f:FlaggedRelationship)
RETURN f.sourceId AS from, f.relType AS rel_type, f.targetId AS to
ORDER BY f.relType
```

---

## Bloom Perspective Updated

`docs/Scaffold Diff.json` has been updated. Re-import in Bloom (delete old, import new). Colour legend:

| Relationship | Colour |
|---|---|
| `CONFIRMS_SEED` | Green `#22c55e` |
| `OVERRIDES_SEED` | Red `#ef4444` |
| `POSSIBLE_OVERRIDES_SEED` | Amber `#f59e0b` |
| `INSTANCE_OF` | Purple `#a855f7` |
| `DOCUMENTED_BY` | Teal `#14b8a6` |
| `REFERENCES` | Blue `#3b82f6` |

---

## Pre-Ingest Cleanup

`ingest-morkborg.ps1` now runs a cleanup step before every ingest, clearing all ingest-created data while leaving the scaffold intact:

```powershell
MATCH ()-[r:OVERRIDES_SEED]->() DELETE r
MATCH (n:IngestNode) DETACH DELETE n
MATCH (n:FlaggedRelationship) DETACH DELETE n
MATCH (n:FlaggedConcept) DETACH DELETE n
```

Scaffold seed nodes and `SPECIALIZES` relationships are never touched.
