# Briefing: AI-DM-Assistant → pdf-graph-builder integration

This document is a prompt/briefing for a Claude session inside the **pdf-graph-builder** workspace. It explains what AI-DM-Assistant is building and what changes are required in pdf-graph-builder to support it.

---

## What AI-DM-Assistant is

A **TTRPG rules assistant** — a chat interface that helps players and dungeon masters get fast, accurate, grounded answers about game mechanics (dice resolution, ability tests, combat, conditions, procedure). Not lore lookup; mechanism lookup.

The app serves three game systems in increasing complexity order: **Mörk Borg → F.A.T.A.L. → Pathfinder**.

The KG is the authoritative rules store. The chat app queries it at runtime with its own LLM and Bolt connection to Neo4j. **pdf-graph-builder is not involved at runtime** — it is a build-time tool only.

---

## Two-phase KG construction

The KG is built in two phases:

### Phase 1 — Bootstrap (AI-DM-Assistant repo)

AI-DM-Assistant owns curated seed files (`corpus/seeds/`) organised in tiers:

| Tier | Content | File location |
|---|---|---|
| 0 | Universal ludemes (abstract play roles, resolution vocabulary) | `corpus/seeds/universal/ludemes.json` |
| 1 | Mechanism families (polyhedral dice, dice pools, diceless, …) | `corpus/seeds/families/*.json` |
| 2 | Framework primitives (d20, DC, modifier, …) | `corpus/seeds/primitives/*.json` |
| 3 | Framework implementations (OSR d20+DC, D&D 3.5 skill check, …) | `corpus/seeds/frameworks/*.json` |
| 4 | Game-variant deltas (per-game overrides of Tier 3) | `corpus/games/<game>/deltas.json` |

A script (`schema/bootstrap.py`) reads and composes these tiers and writes an **ontology scaffold** to a new Neo4j database. At the end of Phase 1 the DB has full structure — node labels, relationship types, abstract concepts — but **no rulebook content**.

Example (Mörk Borg, abbreviated from `corpus/games/mork-borg/deltas.json`):
```json
{ "source": "Agility", "rel": "SPECIALIZES", "target": "AbilityScore" },
{ "source": "CreatureTest", "rel": "OVERRIDES", "target": "AbilityTest",
  "note": "p.28: creatures roll unmodified d20 vs DR — no ability modifier" }
```

### Phase 2 — Dress-up (pdf-graph-builder)

pdf-graph-builder ingests the rulebook PDF **against the pre-bootstrapped scaffold**. It attaches:

- **Tier-5 evidence**: exact text passages, tables, stat blocks — linked to existing schema nodes
- **Diff edges**: signal whether the rulebook confirms, refines, or contradicts the seed schema

This is the **changed behaviour** required in pdf-graph-builder — details below.

---

## What needs to change in pdf-graph-builder

### Current behaviour (problematic for this use case)

pdf-graph-builder currently performs **bottom-up schema discovery**: it reads a PDF, extracts entities and relationships using an LLM, and builds a KG more or less from scratch, using an allowedNodes/allowedRelationships schema as a loose constraint.

### Required behaviour (ingest-as-diff)

pdf-graph-builder must switch to **top-down, diff-against-scaffold** ingest when a pre-bootstrapped Neo4j DB is provided:

1. **Accept a pre-existing DB as input** — do not wipe or re-create the schema. The Tiers 0–4 scaffold is already there.
2. **Constrain extraction to the existing schema** — use the composed seed stack's node labels and relationship types as the strict allowed set.
3. **Attach evidence to existing nodes** — text passages link to scaffold nodes via `DOCUMENTED_BY`; they do not create new schema nodes.
4. **Emit diff signals** instead of silently merging:

| Signal | Meaning |
|---|---|
| `CONFIRMS_SEED` | Rulebook passage supports an existing seed claim |
| `OVERRIDES_SEED` | Rulebook passage contradicts a seed claim — flag for operator review |
| `NEW_NODE` | Extraction found a concept not in the scaffold — flag, do not auto-add |
| `NEW_REL` | Extraction found a relationship type not in the scaffold — flag, do not auto-add |
| `INSTANCE_OF` | A concrete rulebook value (e.g. STR score 14) is an instance of a scaffold concept |

5. **Never add `SPECIALIZES` relationships** — `SPECIALIZES` is an ontological claim ("`X` IS A kind of `Y`") that belongs in seeds, authored by the operator. If ingest finds an apparently new subtype, it emits `NEW_NODE` and stops. The operator decides whether to add it to Tier 4 deltas and re-bootstrap.

### Relationship type contract

These are the relationship types the two phases respectively own:

| Relationship | Semantics | Owner |
|---|---|---|
| `SPECIALIZES` | Ontological subtype | Bootstrap only |
| `OVERRIDES` | This rule supersedes that rule | Bootstrap (Tier 4); ingest may confirm |
| `USES` | This procedure requires/invokes that element | Bootstrap (Tier 3); ingest may confirm |
| `REFERENCES` | Cross-rule reference | Bootstrap and/or ingest |
| `INSTANCE_OF` | Concrete rulebook value is instance of schema concept | Ingest only |
| `DOCUMENTED_BY` | Schema node supported by a rulebook passage | Ingest only |
| `CONFIRMS_SEED` | Ingest evidence agrees with seed claim | Ingest only |
| `OVERRIDES_SEED` | Ingest evidence contradicts seed — needs operator review | Ingest only |

Provenance (which tier created something) is tracked via `tier` and `seed_id` properties on nodes/relationships — not encoded in the relationship type name.

### Coverage flag propagation

Seed nodes carry a `coverage` property. Ingest should promote it:

| Value | Set when |
|---|---|
| `research-only` | Seed authored from SRD/literature; not yet ingest-confirmed |
| `ingest-confirmed` | At least one `CONFIRMS_SEED` passage found during Tier-5 ingest |
| `operator-verified` | Human reviewed and approved |

When ingest finds a passage that confirms a seed node, upgrade that node's `coverage` from `research-only` → `ingest-confirmed`.

---

## What the scaffold looks like before pdf-graph-builder touches it

For Mörk Borg, the scaffold contains (Tiers 0–4 composed):

- Abstract ludemes: `Test`, `Randomizer`, `GameMaster`, `Player`, `ResolutionProcedure`
- Mechanism family: `PolyhedralDice`
- Primitives: `D20Roll`, `DifficultyRating`, `AbilityModifier`
- OSR framework: `AbilityTest`, `AbilityScore`, `DefenseRoll`, `MeleeAttack`
- Mörk Borg deltas: `Agility`, `Strength`, `Presence`, `Toughness`, `CreatureTest`, `Misery`, `Omen`, `Catastrophe`
- Key relationships already in place: `CreatureTest OVERRIDES AbilityTest`, `Agility SPECIALIZES AbilityScore`, etc.

pdf-graph-builder should confirm (or flag exceptions to) this scaffold — not rebuild it.

---

## Neo4j DB per game

Each game system gets its own Neo4j database:

- `morkborg` — Mörk Borg scaffold + Tier-5 dress-up (first POC)
- `fatal` — F.A.T.A.L. scaffold + dress-up (second POC)
- `pathfinder` — Pathfinder scaffold + dress-up (third POC)

Do not mix systems into one DB — the schema and node labels overlap in ways that make queries ambiguous.

---

## First thing to do in pdf-graph-builder

The Mörk Borg Neo4j DB will be bootstrapped from AI-DM-Assistant using:

```bash
python schema/bootstrap.py --game mork-borg
```

Once that DB exists (with connection details in the operator's `.env`), pdf-graph-builder should ingest:

```
MÖRK BORG BARE BONES EDITION.pdf
```

against that pre-existing DB using the ingest-as-diff mode described above.

The goal: every significant rule claim in the PDF either confirms a seed node (→ `CONFIRMS_SEED`, coverage upgraded) or flags an exception for operator review (→ `OVERRIDES_SEED` or `NEW_NODE`).

---

## What pdf-graph-builder does NOT need to change

- Chunking, embedding, vector store — unchanged
- The extraction LLM — unchanged (it just needs better prompting to operate top-down against an existing schema)
- The API shape — existing `/extract`, `/chat_bot`, `/graph_query` endpoints remain useful; the diff behaviour is a new mode, not a replacement
- Its own internal schema management — it does not need to know about the seed tier model beyond "a scaffold already exists, attach evidence to it"

---

## References

- AI-DM-Assistant `DESIGN.md` — full architecture, seed model, relationship table, bootstrap flow
- AI-DM-Assistant `schema/bootstrap.py` — the script that writes the scaffold to Neo4j
- AI-DM-Assistant `corpus/games/mork-borg/deltas.json` — Tier 4 deltas verified against the Bare Bones Edition PDF
- AI-DM-Assistant `corpus/games/mork-borg/declared-stack.json` — the full stack declaration for Mörk Borg
- pdf-graph-builder `design.md` — existing pipeline design (read before modifying)
- pdf-graph-builder `docs/sme-and-kg-roles.md` — build vs ask vs curate roles
