# AI-DM-Assistant Handoff 1: Mork Borg Scaffold-Diff Ingest — Findings

**Last updated:** 2026-07-13 (fourth ingest run)  
**Source:** `pdf-graph-builder` scaffold-diff ingestion of `mork-borg.pdf`  
**Target DB:** Neo4j `morkborg` database (AutoMechanic instance)  
**Model:** Ollama llama3 (`ollama_llama3`)  
**Chunks processed:** 19 | **Tokens used:** ~40k | **Processing time:** ~7 minutes

---

## What Was Done

A scaffold-diff ingest was run against the Mork Borg rulebook PDF. This mode compares PDF-extracted content against a pre-existing scaffold of seed nodes, classifying extractions as:

| Signal | Meaning |
|---|---|
| `CONFIRMS_SEED` | PDF passage explicitly confirms a scaffold concept |
| `OVERRIDES_SEED` | PDF passage explicitly contradicts a scaffold claim |
| `POSSIBLE_OVERRIDES_SEED` | LLM was uncertain — flagged for human triage |
| `INSTANCE_OF` | A concrete rulebook value is an instance of a scaffold concept |
| `REFERENCES` | Structural mechanic dependency ("X is used for Y") |
| `FlaggedConcept` | LLM found a concept with no matching scaffold label — queued for review |

After ingest, confirmed seed nodes have `coverage` upgraded from `research-only` → `ingest-confirmed`.

---

## Run History

| Run | OVERRIDES_SEED | POSSIBLE_OVERRIDES_SEED | IngestNodes | Notes |
|---|---|---|---|---|
| 1 | — | — | — | Initial pipeline wiring |
| 2 | — | — | — | Chunking parameter fixes |
| 3 | 20 (false positives) | — | 80 | Pre-prompt-fix baseline |
| **4** | **0** | **0** | **57** | Post-prompt-fix, clean result |

---

## Final Results (Run 4)

### Confirmed Seeds
- **56 / 56** scaffold seed nodes confirmed (`coverage = "ingest-confirmed"`)
- 0 seeds remain at `research-only`
- The rulebook fully covers the scaffold

### Contradictions
- **0 `OVERRIDES_SEED`** — no confirmed contradictions
- **0 `POSSIBLE_OVERRIDES_SEED`** — LLM found nothing ambiguously contradictory
- **1 `REFERENCES`** — one clean structural mechanic dependency emitted

### IngestNode Instances (57 total)
Concrete named entities extracted from the rulebook, linked via `INSTANCE_OF` to scaffold concepts:

| Scaffold type | Count |
|---|---|
| GameWorld | 6 |
| NonPlayerCharacter | 5 |
| Group | 4 |
| AbilityScore | 3 |
| Setting | 3 |
| Presence | 2 |
| Outcome | 2 |
| Misery | 2 |
| Omen | 2 |
| DicePool | 2 |
| Modifier | 2 |
| CreatureTest | 2 |
| AbilityTest | 2 |
| RulesReference | 2 |
| Scene | 2 |
| Various (1 each) | 15 |

Examples: Bergen Chrypt, Endless Sea, Sarkash, Gorgh, Josilfa Migol, Agility, Strength, Toughness, Catastrophe, D20Roll.

### Evidence Coverage
6 PDF chunks linked to all 56 confirmed seeds via `DOCUMENTED_BY`. Coverage is intentionally coarse — a game rulebook presents many concepts together in the same passages.

---

## What Changed Between Run 3 and Run 4

### Prompt fix — `OVERRIDES_SEED` false positives

Run 3 produced 20 `OVERRIDES_SEED` relationships, all false positives. The LLM was
emitting them for structural mechanic dependencies ("D20Roll is used for AbilityTest")
and NPC interactions, not true contradictions.

`SCAFFOLD_DIFF_INSTRUCTIONS` in `backend/src/shared/constants.py` was updated to enforce
a three-tier model:

| Relationship | Trigger |
|---|---|
| `OVERRIDES_SEED` | Rulebook text explicitly states something that conflicts with the scaffold |
| `POSSIBLE_OVERRIDES_SEED` | LLM is uncertain — emit for triage rather than silently drop |
| `REFERENCES` | Structural mechanic dependency |

Run 4 confirmed the fix: zero contradiction signals, one clean `REFERENCES`.

---

## Architectural Insight: Two-Layer Scaffold

The current scaffold has two implicit layers that should be made explicit:

```
Layer 1: ttrpg-universal
  └── Generic concepts true of all TTRPGs
  └── Confirmed by: community knowledge, not rulebook ingestion
  └── Examples: GameMaster, Player, Session, Scene

Layer 2: morkborg-specific  ← MISSING, needs to be built
  └── SPECIALIZES or EXTENDS the universal layer
  └── Confirmed by: rulebook PDF ingestion
  └── Examples: Omen, Scvm, Misery, DR, Powers, Scrolls, Catastrophe
```

The `IngestNode` instances from this ingest run are a **first draft** of what Layer 2
should contain — concrete named entities the PDF surfaced that the scaffold treated as
instances of universal concepts.

---

## Recommended Next Steps

### For AI-DM-Assistant
See [Handoff 2](./ai-dm-assistant-handoff-2.md) for the full schema handoff. Key points:

1. **Prefer `ingest-confirmed` nodes** when answering rules questions — those are ground-truth from the PDF
2. **Caveat or skip `research-only` nodes** — unverified scaffold claims
3. **Query both contradiction types** when surfacing conflicts to the DM:
   ```cypher
   MATCH (a)-[r:OVERRIDES_SEED|POSSIBLE_OVERRIDES_SEED]->(b)
   RETURN a.name, type(r) AS signal, b.name ORDER BY signal
   ```
4. **Use `CONFIRMS_SEED` trails** to retrieve the actual PDF chunk text that backs up a fact:
   ```cypher
   MATCH (seed)<-[:CONFIRMS_SEED]-(chunk:Chunk)
   WHERE seed.coverage = 'ingest-confirmed'
   RETURN seed.name, chunk.text ORDER BY chunk.position
   ```

### For the Mork Borg Scaffold
1. **Build a Mork Borg-specific scaffold layer** — promote the 57 `IngestNode` instances into proper scaffold seed nodes with `SPECIALIZES` relationships to the universal layer
2. **Re-ingest** with the enriched scaffold — confirmation rate will be higher and instances will map more precisely
3. **Consider a better model** — llama3.1:70b or a cloud model would map rulebook terminology to scaffold concepts more reliably than llama3 7B

### The Repeatable Workflow
```
1. Build/refine universal scaffold (game-agnostic)
2. Build game-specific scaffold layer (SPECIALIZES universal)
3. Ingest rulebook PDF → CONFIRMS_SEED, INSTANCE_OF, FlaggedConcept
4. Human reviews POSSIBLE_OVERRIDES_SEED → confirm or discard
5. Human reviews FlaggedConcepts → promotes to scaffold
6. Re-ingest → higher confirmation rate, tighter instances
7. AI-DM-Assistant queries confirmed-only nodes for reliable answers
```

---

## Queries for Ongoing Review

```cypher
-- What did the PDF confirm?
MATCH p=(c:Chunk)-[:CONFIRMS_SEED]->(seed) RETURN p LIMIT 50

-- What is still unverified?
MATCH (n) WHERE n.coverage = 'research-only' AND n.seed_id IS NOT NULL
RETURN labels(n) AS label, n.seed_id AS seed_id ORDER BY label

-- Any uncertain contradictions to triage?
MATCH (a)-[r:POSSIBLE_OVERRIDES_SEED]->(b)
RETURN a.name AS from, b.name AS to ORDER BY a.name

-- Concrete instances extracted from the rulebook:
MATCH (n:IngestNode)-[:INSTANCE_OF]->(s)
RETURN n.name AS instance, [l IN labels(s) WHERE NOT l IN ['__Entity__','SeedNode','IngestNode']] AS scaffold_type
ORDER BY scaffold_type, instance

-- Grounded evidence for a concept:
MATCH (seed)<-[:CONFIRMS_SEED]-(chunk:Chunk)
WHERE seed.coverage = 'ingest-confirmed'
RETURN seed.name, chunk.text ORDER BY chunk.position LIMIT 20
```
