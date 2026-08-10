# AI-DM-Assistant Handoff 8: Contracts ahead + linked-table retrieval (Traps / Agony)

**From:** pdf-graph-builder  
**Date:** 2026-08-06 (updated same day)  
**Context:** pgb is ahead of ADA SoT on Tier-5 contracts and shared extract. Chat still cannot reliably pull structured `HAS_ENTRY` rows for Traps / Agony. THE WORLD place sections are now declared and store title+body as section chunks.

**Operator field guide (schema keywords):** `games/mork-borg/README.md` in pdf-graph-builder (merge into ADA corpus README if you keep a copy).

---

## 1. Contract sync — required

**SoT split (agreed):**

| File | Source of truth | Sync |
|---|---|---|
| `passage-sections.json` | **pdf-graph-builder** `games/mork-borg/` | Copy **pgb → ADA** mirror (`corpus/games/mork-borg/`) |
| `ingest-manifest.json` | **AI-DM-Assistant** `corpus/games/mork-borg/` | Copy **ADA → pgb** (merge carefully; do not wipe pgb table extensions) |

See pdf-graph-builder `docs/ingest-manifest-sync.md`.

| Artifact | pgb path | Action |
|---|---|---|
| `passage-sections.json` **v0.5.5** | `games/mork-borg/passage-sections.json` | ADA: replace corpus mirror from pgb (SoT). Includes `text_filters`, THE WORLD `sections[]`, `subheading_regex` / `passage_split`, RULES / `entity_passage` / `content_source` |
| `AgonyEndTable` | `games/mork-borg/ingest-manifest.json` | Merge into ADA SoT `ingest-manifest.json`, then sync ADA → pgb if needed |
| Hand-authored rows | `games/mork-borg/hand-authored-overrides/agony-end.json` | Copy into ADA corpus (e.g. `tables/agony-end.json`) and align `hand_authored.file` |

**Notable passage-sections additions (pgb SoT):**

- **`text_filters`** — Bare Bones running footer + edge page numbers  
- **THE WORLD sections** — `what-was-written` (Roman I–IV), place blocks through `valley-of-the-unfortunate-undead`, `western-kingdom` p.15→16, Kergüs / Anthelia’s Ambivalence  
- **`AgonyEndTable`** lives in the **manifest** (ADA SoT for that file), not in passage-sections

Preview without Neo4j: pgb `tools/pdf-as-md` (same `document_extract` path as ingest).

---

## 2. Runtime table shape — no new type

`AgonyEndTable` uses the **same** graph shape as dice lookups (`TrapsTable`, `DRTable`, …):

```text
(:AgonyEndTable:IngestNode)-[:INSTANCE_OF]->(:LookupTable)
(:AgonyEndTable)-[:HAS_COLUMN]->(:TableColumn {role:"index"|"result"})
(:AgonyEndTable)-[:HAS_ENTRY]->(:TableEntry {cells: {...}})
```

| | Dice lookup (e.g. Traps) | Agony chooser |
|---|---|---|
| Index column | numeric face (`d12`) | duration label string |
| Result column | outcome text | die to use (`d100` … `d2`) |

No new node label or parser for “chooser vs roll table.” Column names / `role` + `cells` carry the flavour. No ADA adapter change is required merely to *store* or *render* these rows once they are in CONTEXT.

---

## 3. Requirement (not optional): linked-table retrieval for Traps and Agony

**Status:** structured rows enter CONTEXT only via

```cypher
MATCH (n)-[:USES]->(t)-[:HAS_ENTRY]->(r:TableEntry)
```

(`ContextRetriever._add_linked_tables` in ADA `backend/app/retrieval.py`).

`DRTable` works because ingest wires `AbilityTest -[:USES]-> DRTable` from manifest `used_by`.

**`TrapsTable` and `AgonyEndTable` have no `used_by` and therefore no `USES` edges.** Catalog / passage text may mention them; **`HAS_ENTRY` rows do not systematically land in CONTEXT.** That breaks the product path for the prompts below. This is a **hard requirement**, not a nice-to-have.

### ADA must implement

**R1 — Seed owners (Tier 4 / deltas)**  
Declare which scaffold seeds own each table (create or un-defer labels as needed):

| Table | Proposed `used_by` seed(s) | Rationale |
|---|---|---|
| `TrapsTable` | e.g. `Trap` / dungeon-prep seed (ADA chooses canonical label; add to deltas if missing) | Random trap resolution |
| `AgonyEndTable` | `Misery` (and optionally `WorldLore` if Calendar framing is separate) | Campaign-length → Misery die |

Also add Tier-4 `USES` edges seed→`LookupTable` where that is how other tables are scaffolded (mirror `AbilityTest USES LookupTable` / `CharacterCreation USES LookupTable`).

**R2 — Manifest `used_by` (Tier 5 contract)**  
On ADA SoT `ingest-manifest.json`:

- `TrapsTable.used_by`: seed label(s) from R1  
- `AgonyEndTable.used_by`: seed label(s) from R1  

After sync + pgb materialize (`.\ingest-tables.ps1` or full extract), Neo4j must show:

```cypher
MATCH (s)-[:USES]->(t:TrapsTable)-[:HAS_ENTRY]->(r:TableEntry)
RETURN s, count(r)
// expect rows > 0

MATCH (s)-[:USES]->(t:AgonyEndTable)-[:HAS_ENTRY]->(r:TableEntry)
RETURN s, count(r)
// expect 5 rows
```

**R3 — Retrieval hints**  
Extend `systems/mork-borg/retrieval_hints.py` so natural language reaches those seeds (and thus linked tables), e.g.:

- traps / trap / d12 traps / devilry → seed(s) that `USES` `TrapsTable`
- agony / calendar / nechrubel / campaign length / when will all this agony / misery die → seed(s) that `USES` `AgonyEndTable`

(Existing `"misery"` → `Misery` is necessary but not sufficient until R1–R2 wire `Misery USES AgonyEndTable`.)

### Acceptance prompts (smoke)

| # | Human prompt | CONTEXT must include | Reply behaviour |
|---|---|---|---|
| A | *“Corridor trap — I rolled a 7 on the d12 traps table. What happens?”* | `TrapsTable` `HAS_ENTRY` for `d12: 7` (structured rows, not only prose) | Index = roll → trap text |
| B | *“Campaign length: we want about a month of play. Which Misery die does ‘When will all this agony end?’ say we use?”* | `AgonyEndTable` row `duration: A cruel month` → `die: d6` | Index = chosen duration → die |

**Pass criteria:** both prompts show the table in the UI context inspector under linked lookup tables (or equivalent), with row cells present; answers cite that table evidence.

---

## 4. THE WORLD section storage (informational — prefer in retrieval)

After section materialization, place/lore blocks are coherent sets:

```text
(:Chunk {
  id: "{file}#section:{section_id}",
  section_id, section_title,   // title as metadata
  text,                          // body AFTER start heading
  page_number_start / page_number_end,
  source_format: "passage-section"
})-[:PART_OF]->(:Document)

(:Chunk)-[:DOCUMENTED_BY]->(:RulePassage {
  section_id, section_title, passage_index, text, page_number
})
```

- Cross-page bodies (Western Kingdom) are one section chunk with a page range.  
- Nested subheads (Roman I–IV; Anthelia’s Ambivalence) are separate `RulePassage`s under the same `section_id` when `passage_granularity: subheading_regex`.  
- CREATURES `entity-passage` nodes remain a **parallel** path (Briefings 10–11); WORLD places above use `sections[]`, not entity_passage yet.

**ADA follow-up (recommended, not blocking R1–R3):** when answering place/lore questions (“What is Galgenbeck?”), prefer `Chunk` / `RulePassage` with matching `section_id` / `section_title` (or `IndexEntry` → section link) over full-page chunks. Exact wiring is ADA’s call once contracts are synced and sections are materialized.

---

## Ownership split

| Work | Owner |
|---|---|
| Keep `passage-sections.json` SoT in pgb; refresh ADA mirror | pdf-graph-builder → ADA copy |
| Merge `AgonyEndTable` + hand-authored file into ADA manifest SoT | AI-DM-Assistant |
| Seed labels + deltas `USES` (R1) | AI-DM-Assistant |
| Manifest `used_by` (R2) | AI-DM-Assistant (SoT) → sync to pgb |
| Materialize `USES` / section chunks on ingest | pdf-graph-builder (already implemented) |
| `retrieval_hints` + chat smoke (R3; WORLD section prefer) | AI-DM-Assistant |

---

## pgb already delivered

- `AgonyEndTable` + `hand-authored-overrides/agony-end.json` (5 rows); pdf-as-md substitutes via header match  
- `passage-sections.json` v0.5.5: `text_filters`, THE WORLD sections, `subheading_regex`  
- Shared extract: `backend/src/document_extract.py`; preview: `tools/pdf-as-md`  
- Section graph shape: `section_chunking.materialize_passage_sections` (`section_id` + `section_title` + body + `DOCUMENTED_BY` passages)

Neo4j: run full scaffold-diff extract (or `.\ingest-tables.ps1 -Tables AgonyEndTable` + section materialize) when DB is up — after contract sync so ADA SoT and pgb agree.
