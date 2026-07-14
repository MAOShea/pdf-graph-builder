# Briefing 2: Mörk Borg Re-ingest — Fixes & Scaffold Update

**Context:** This follows [Briefing 1](./pdf-graph-builder-briefing.md) and the findings from the first ingest run documented in [Handoff 1](../inbox/ai-dm-assistant-handoff-1.md). Three bugs were identified in the ingest process. They have been fixed on the AI-DM-Assistant side (scaffold updated). This briefing describes what to fix in pdf-graph-builder before re-ingesting.

---

## Scaffold change since Briefing 1

The `morkborg` Neo4j DB has been wiped and re-bootstrapped with a corrected scaffold. One structural change was made to the seed files:

**`DifficultyClass` removed from the shared `d20-core` Tier 2 primitive.**

It was incorrectly placed there — `DifficultyClass` is a D&D 3.5 / Pathfinder-specific term, not a universal d20 primitive. The corrected hierarchy is:

```
DifficultyRating  (Tier 2 — abstract target number, in every d20 DB)
  ├── DR           (Tier 4 — Mörk Borg delta, morkborg DB only)
  └── DC           (Tier 3 — d20-3.5 framework, pathfinder DB only — future)
```

`DR` is now a proper named node in the `morkborg` DB with `DR SPECIALIZES DifficultyRating`. The ingest should now be able to confirm it directly by name.

**The `morkborg` DB is clean.** Re-run `MATCH (n) RETURN count(n)` to confirm ~57 nodes before ingesting.

---

## Three bugs to fix in pdf-graph-builder before re-ingesting

### Bug 1 — Case normalisation

**Problem:** The first ingest produced many `FlaggedConcept` nodes with `proposedLabel` values like `Abilityscore`, `Abilitytest`, `Meleeattack`, `Defenseroll` — all of which already exist in the scaffold with correct casing (`AbilityScore`, `AbilityTest`, etc.). The diff code failed to match them because it compared strings case-sensitively.

**Fix:** Before comparing an LLM-extracted label against the scaffold's node labels, normalise both to lowercase (or strip punctuation). A match should be case-insensitive.

```python
# example
scaffold_labels = {label.lower(): label for label in scaffold_node_labels}
extracted = extracted_label.lower()
if extracted in scaffold_labels:
    canonical = scaffold_labels[extracted]  # use the scaffold's casing
    # → emit CONFIRMS_SEED, not FlaggedConcept
```

---

### Bug 2 — Instance routing

**Problem:** The first ingest dumped concrete named things — monsters (`Basilisk`, `Verhu`, `Gorgh`), traps (`Scorpion-Filled Basket`), locations (`Tveland`, `Wüstland`), named rule values — into `FlaggedConcept` as `NEW_NODE` signals. These are not new schema concepts; they are instances of existing scaffold concepts.

**Fix:** Add a classification step after extraction. If the LLM extraction maps a concrete named entity to an existing scaffold label, create an `:IngestNode` rather than a `:FlaggedConcept`:

```
(:Basilisk :IngestNode {name: "Basilisk", source: "chunk_id", page: 34})
  -[:INSTANCE_OF]->
(:NonPlayerCharacter :SeedNode)
```

Heuristics for "this is an instance, not a schema concept":
- The proposed label matches an existing scaffold label (after case normalisation) but the extracted `id`/`name` is a specific proper noun
- The scaffold label is a category (`NonPlayerCharacter`, `GameWorld`, `MeleeAttack`) and the extracted value is a specific named thing

`:IngestNode` nodes should carry:
- `name` — the specific name from the rulebook
- `source` — the chunk or document it came from  
- `page` — page number if available
- `tier: 5` — marks it as Tier-5 ingest content
- No `seed_id` — it is not a seed node

---

### Bug 3 — SeedNode label leaking into extraction

**Problem:** The LLM read the scaffold's internal `:SeedNode` label from the DB and flagged it as an extracted concept, producing nonsense entries like:
- `FlaggedConcept (proposedLabel: Seednode, id: Mork-Borg-Deltas)`
- `FlaggedConcept (proposedLabel: Seednode, id: D20-Core)`

**Fix:** Exclude `:SeedNode` (and any other internal infrastructure labels like `:IngestNode`, `:FlaggedConcept`, `:Chunk`, `:RulePassage`) from the list of scaffold labels passed to the extraction prompt. The LLM should only see domain concept labels:

```python
INTERNAL_LABELS = {"SeedNode", "IngestNode", "FlaggedConcept", "Chunk", "RulePassage"}
scaffold_labels_for_prompt = [l for l in all_scaffold_labels if l not in INTERNAL_LABELS]
```

---

## Expected results after fixes

| Signal | First run | Expected second run |
|---|---|---|
| `CONFIRMS_SEED` | Tier 4 nodes only (15) | Tier 4 + `DR` + some Tier 2/3 nodes via better matching |
| `FlaggedConcept` (spurious) | ~50+ from casing + SeedNode leakage | Near zero |
| `FlaggedConcept` (genuine) | Buried in noise | Visible — real gaps in the scaffold |
| `:IngestNode` (instances) | Zero — all dumped to FlaggedConcept | Monsters, traps, locations, DR value instances |
| `OVERRIDES_SEED` | Zero | Still expected to be zero |

---

## What a good ingest result looks like

After the second run, you should be able to run these queries and get meaningful results:

```cypher
-- Confirmed scaffold concepts
MATCH (n:SeedNode) WHERE n.coverage = 'ingest-confirmed'
RETURN n.name, n.tier ORDER BY n.tier

-- All Mork Borg-specific instances added by ingest
MATCH (n:IngestNode)-[:INSTANCE_OF]->(scaffold:SeedNode)
RETURN n.name, labels(scaffold) AS type ORDER BY type

-- Grounded evidence for a concept
MATCH (seed:SeedNode)<-[:CONFIRMS_SEED]-(chunk)
WHERE seed.name = 'DR'
RETURN seed.name, chunk.text

-- Genuine gaps (real new concepts not in scaffold)
MATCH (f:FlaggedConcept)
RETURN f.proposedLabel, f.id ORDER BY f.proposedLabel
```

---

## What does NOT need to change

- The bootstrap process — that stays in AI-DM-Assistant
- The `SPECIALIZES` constraint — ingest still must not write `SPECIALIZES` relationships
- The diff signal vocabulary — `CONFIRMS_SEED`, `OVERRIDES_SEED`, `NEW_NODE` are still correct for genuine schema gaps
- Chunking, embedding, vector storage — unchanged
