# Mork Borg Scaffold-Diff Ingest — Findings & Handoff Notes

**Date:** 2026-07-13  
**Source:** `pdf-graph-builder` scaffold-diff ingestion of `mork-borg.pdf`  
**Target DB:** Neo4j `morkborg` database (AutoMechanic instance)  
**Model:** Ollama llama3 (`ollama_llama3`)  
**Chunks processed:** 19 | **Tokens used:** 40,332 | **Processing time:** ~7 minutes

---

## What Was Done

A scaffold-diff ingest was run against the Mork Borg rulebook PDF. This mode compares PDF-extracted content against a pre-existing scaffold of seed nodes, classifying extractions as:

| Signal | Meaning |
|---|---|
| `CONFIRMS_SEED` | PDF passage explicitly confirms a scaffold concept |
| `OVERRIDES_SEED` | PDF passage contradicts a scaffold claim |
| `INSTANCE_OF` | A concrete rulebook value is an instance of a scaffold concept |
| `FlaggedConcept` | LLM found a concept with no matching scaffold label — queued for review |
| `FlaggedRelationship` | LLM found a relationship type not in the scaffold |

After ingest, confirmed seed nodes have `coverage` upgraded from `research-only` → `ingest-confirmed`.

---

## Results Summary

### Confirmed Seeds (coverage = ingest-confirmed)
Concepts the PDF explicitly confirmed, including:
- **Toughness** — HP/durability stat
- **Misery** — apocalyptic doom progression tracker
- **Catastrophe** — end-of-world events
- **DifficultyRating** — Mork Borg uses "DR" (not "DC")
- Several other core Mork Borg mechanics

### Contradictions (OVERRIDES_SEED)
**Zero.** The PDF did not contradict any scaffold claim. Expected, given the scaffold was bootstrapped from Mork Borg knowledge. Most useful when comparing editions or community-vs-official sources.

### Unconfirmed Seeds (coverage = research-only)
41 nodes remain unconfirmed. They fall into two categories:

#### 1. Generic TTRPG meta-concepts (`ttrpg-universal` seed_id)
These will **never** be confirmed by a single rulebook — they describe how TTRPGs work in general, not Mork Borg specifically:
`GameMaster`, `Player`, `Session`, `TableTalk`, `Roleplay`, `SocialContract`, `Scene`, `Situation`, `Setting`, `Group`, `Adjudication`, `CharacterCreation`, `CharacterState`, `Action`, `InCharacterAction`, `PlayerDeclaration`, `GMNarration`, `Outcome`, `Randomizer`, `ResolutionProcedure`, `Downtime`, `RulesReference`, `Uncertainty`, `Color`

#### 2. Generic OSR/D20 mechanics (`osr-d20-dc`, `d20-core`, `polyhedral-dice` seed_ids)
These *should* appear in Mork Borg but didn't match because the game uses its own terminology:
`DifficultyClass` (Mork Borg uses DR, not DC), `D20Roll`, `AbilityScore`, `AbilityTest`, `DefenseRoll`, `MeleeAttack`, `RangedAttack`, `Modifier`, `DicePool`, `PolyhedralDice`

**Key insight:** `DifficultyRating` was confirmed but `DifficultyClass` was not — because Mork Borg calls it "DR", not "DC". The scaffold had both; only the Mork Borg-native one matched.

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

The `FlaggedConcept` nodes from this ingest run are a **first draft** of what Layer 2 should contain — concepts the PDF surfaced that the scaffold didn't anticipate.

---

## Recommended Next Steps

### For AI-DM-Assistant
The RAG query logic should be updated to respect coverage signals:

1. **Prefer `ingest-confirmed` nodes** over `research-only` when answering rules questions — those are ground-truth from the PDF
2. **Caveat or skip `research-only` nodes** — these are unverified scaffold claims
3. **Ignore unreviewed `FlaggedConcept` nodes** until an operator promotes them
4. **Use `CONFIRMS_SEED` trails** to retrieve the actual PDF chunk text that backs up a fact — this gives the LLM grounded, citable evidence rather than just graph data

Example traversal pattern for grounded answers:
```cypher
MATCH (seed {name: $concept})<-[:CONFIRMS_SEED]-(chunk:Chunk)
WHERE seed.coverage = 'ingest-confirmed'
RETURN seed, chunk.text ORDER BY chunk.position
```

### For the Mork Borg Scaffold
1. **Review `FlaggedConcept` nodes** — run `MATCH (f:FlaggedConcept) RETURN f.id, f.proposedLabel` to see what the PDF surfaced that wasn't in the scaffold
2. **Promote valid flagged concepts** into a Mork Borg-specific scaffold layer with `SPECIALIZES` relationships to the universal layer
3. **Re-ingest** with the enriched scaffold — confirmation rate will be much higher
4. **Consider a better model** — llama3.1:70b or a cloud model would map rulebook terminology to scaffold concepts more reliably than llama3 7B

### The Repeatable Workflow
```
1. Build/refine universal scaffold (game-agnostic)
2. Build game-specific scaffold layer (SPECIALIZES universal)
3. Ingest rulebook PDF → CONFIRMS_SEED, FlaggedConcept
4. Human reviews FlaggedConcepts → promotes to scaffold
5. Re-ingest → higher confirmation rate
6. AI-DM-Assistant queries confirmed-only nodes for reliable answers
```

---

## Queries for Ongoing Review

```cypher
-- What did the PDF confirm?
MATCH p=(c:Chunk)-[:CONFIRMS_SEED]->(seed) RETURN p LIMIT 50

-- What is still unverified?
MATCH (n) WHERE n.coverage = 'research-only' AND n.seed_id IS NOT NULL
RETURN labels(n) AS label, n.seed_id AS seed_id ORDER BY label

-- What new concepts did the PDF surface?
MATCH (f:FlaggedConcept) RETURN f.id, f.proposedLabel, f.signal ORDER BY f.flaggedAt

-- Grounded evidence for a concept:
MATCH (seed)<-[:CONFIRMS_SEED]-(chunk:Chunk)
WHERE seed.coverage = 'ingest-confirmed'
RETURN seed.name, chunk.text ORDER BY chunk.position LIMIT 20
```
