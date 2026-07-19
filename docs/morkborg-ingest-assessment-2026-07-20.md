# Mörk Borg ingest assessment — 2026-07-20

**Context:** Full ingest via `.\ingest-morkborg.ps1` after bootstrap refresh (Briefings 7+8 scaffold seeds verified). Backend running on `http://localhost:8000`. Neo4j database: `morkborg`.

**Tools used:** `check_coverage.py --verbose`, direct Cypher against `morkborg`.

**Overall verdict:** **PASS** on manifest contract (seeds, tables, bundles, rulebook index). **Gaps** on Briefing 6 section chunking, `RulePassage`, and `MAPS_TO_SECTION` linking.

---

## Executive summary

| Layer | Status | Notes |
|---|---|---|
| Bootstrap seeds | ✅ | `Place`, `Creature`, `Faction`, `WorldLore`, `SupportingCharacter`, `Monster` present |
| LLM scaffold-diff extract | ✅ | 60/60 seeds ingest-confirmed; 2,574 `CONFIRMS_SEED` edges |
| Lookup tables (Briefing 3–5) | ✅ | 50/50 manifest tables materialized |
| Optional-class bundles | ✅ | 6/6 bundles; SELECTS/CONTAINS wired |
| Rulebook index (Briefing 7) | ✅ | 81 `IndexEntry` nodes; 1 `ALSO_INDEXED_AS` |
| Fiction instances (Briefing 8) | ✅ | 40 typed entities from WORLD/CREATURES index |
| Section chunking (Briefing 6) | ❌ | 0 section chunks, 0 `RulePassage`, 0 superseded token chunks |
| Index → section links | ❌ | 0 `MAPS_TO_SECTION` (blocked by missing section chunks) |

---

## Document state

```
Document:     mork-borg.pdf
Status:       Completed
LLM metadata: nodeCount=112, relationshipCount=187, total_chunks=76
Actual chunks in graph: 112 (pages 1–76)
```

Note: Document node properties reflect the **LLM extract pass only**, not the full Tier-5 graph (tables, index, fiction instances add many more nodes).

---

## Coverage report (`check_coverage.py --verbose`)

```
Seeds:     60/60 ingest-confirmed (0 research-only)
Tables:    50/50 OK
Bundles:   6/6 (SELECTS 6/6, CONTAINS 12/12)
Flags:     157 open (FlaggedRelationship: 157; OVERRIDES_SEED: 0)
Phase 1:   DRTable 7 rows -> Agility, RulePassage 0, AbilityTest 1
Index:     entries=81 (CREATURES=12, RULES=41, THE_WORLD=28), section_links=0, fiction=40
Chunks:    112 (pages 1-76)

PASS
```

---

## Briefing 7 — Rulebook catalog

| Column | Expected | Actual |
|---|---|---|
| THE_WORLD | 28 | 28 |
| CREATURES | 12 | 12 |
| RULES | 41 | 41 |
| **Total** | **81** | **81** |

- One `RulebookIndex` linked to `Document` via `HAS_INDEX`.
- One cross-column duplicate linked via `ALSO_INDEXED_AS` (e.g. Calendar of Nechrubel variants).
- All index rows carry `entry_kind` from `passage-sections.json` v0.3.0.

**Acceptance Cypher:**

```cypher
:use morkborg
MATCH (d:Document {fileName: 'mork-borg.pdf'})-[:HAS_INDEX]->(idx:RulebookIndex)
RETURN d.fileName, idx.index_page, idx.layout;

MATCH (idx:RulebookIndex)-[:HAS_ENTRY]->(e:IndexEntry)
RETURN e.column, count(e) AS n ORDER BY e.column;
```

---

## Briefing 8 — Typed fiction instances

| Kind | Expected (contract) | Actual (`DENOTES` → correct seed) |
|---|---|---|
| `place` | 13 | 13 → `Place:SeedNode` |
| `creature` | 12 | 12 → `Creature:SeedNode` |
| `supporting_character` | 9 | 9 → `SupportingCharacter:SeedNode` |
| `faction` | 3 | 3 → `Faction:SeedNode` |
| `world_lore` | 3 | 3 → `WorldLore:SeedNode` |
| **Total fiction entities** | **40** | **40** |

- Zero `:Location` nodes (correct per briefing).
- CREATURES use `Creature` seed, not bare `Monster`.
- Sample places: Galgenbeck, Arkh, Bergen Chrypt, Endless Sea, Graven-Tosk.
- Sample characters: Anthelia, Anuk Schleger, Fathmu IX, Gorgh, Josilfa Migol.
- WORLD entities have `OCCURS_IN` → `Setting:SeedNode` where Setting seed exists.

**Acceptance Cypher:**

```cypher
MATCH (e:IndexEntry {column:'THE_WORLD', entry_kind:'place'})-[:DENOTES]->(x)-[:INSTANCE_OF]->(:Place:SeedNode)
RETURN count(x) AS places;  // 13

MATCH (e:IndexEntry {column:'CREATURES'})-[:DENOTES]->(x)-[:INSTANCE_OF]->(:Creature:SeedNode)
RETURN count(x) AS creatures;  // 12

MATCH (n) WHERE n:Location RETURN count(n);  // 0
```

---

## Briefing 6 — Section chunking (NOT present)

| Metric | Expected (phase 1) | Actual |
|---|---|---|
| Section `:Chunk` nodes (`#section:` in id) | ≥ 4 | **0** |
| `RulePassage` nodes | ≥ 1 (Abilities section) | **0** |
| Token chunks flagged `superseded_by_section` | > 0 on overlap pages | **0** |
| `MAPS_TO_SECTION` (RULES index → section chunk) | Phase 1 titles linked | **0** |

**Likely cause:** Section materialization did not run during this ingest pass. Possible reasons:

1. Backend was started **before** `section_chunking` / `index_materialization` wiring was loaded (uvicorn `--reload` may not have picked up changes if server predated the code).
2. `materialize_passage_sections()` returned early (warnings in extract logs — check backend stdout from ingest run).

Section chunking is **orthogonal** to the index catalog; the index ran successfully but could not link to sections that do not exist.

---

## LLM extract / flags

| Signal | Count |
|---|---|
| `CONFIRMS_SEED` | 2,574 |
| `OVERRIDES_SEED` | 0 |
| `FlaggedRelationship` | 157 |
| `FlaggedConcept` | 0 |

157 flagged relationships are LLM-invented rel types not in the scaffold — operator triage in Graph Builder (see `docs/ai-dm-assistant-handoff-3.md` for promotion candidates).

---

## Tables spot-check (all OK)

Phase 1: `DRTable` 7 rows, `APPLIES_TO` Agility.

Phase 2–3: WeaponTable, ArmorTable, OptionalClassesTable, NPC location tables, weather, traps, etc. — full list in `check_coverage.py --verbose` output (50 entries, all `[OK]`).

---

## Next session — recommended actions

### 1. Materialize section chunks (Briefing 6)

From repo root (Neo4j only; backend not required):

```powershell
.\materialize-passage-sections.ps1 -Phase 1
# or -Phase 3 for all 17 sections in passage-sections.json
```

Verify:

```cypher
MATCH (c:Chunk) WHERE c.id CONTAINS '#section:' RETURN c.section_id, c.section_title;
MATCH (p:RulePassage) RETURN count(p);
```

### 2. Link index entries to section chunks

Fiction instances already exist — skip recreating them:

```powershell
.\materialize-rulebook-index.ps1 -NoFiction
```

Or with phase filter matching section materialization:

```powershell
.\materialize-rulebook-index.ps1 -NoFiction -Phase 1
```

Verify:

```cypher
MATCH (e:IndexEntry {title: 'Tests'})-[:MAPS_TO_SECTION]->(c:Chunk)
RETURN e.title, c.section_id;
```

### 3. Re-run coverage

```powershell
.\check-coverage.ps1
```

Expect `section_links` > 0 and optionally `RulePassage` > 0 after step 1.

### 4. Optional — full re-ingest with fresh backend

If section chunking should run automatically on every ingest:

1. Restart backend (`backend\start.ps1`) so latest `main.py` is loaded.
2. `.\ingest-morkborg.ps1` (cleans + re-ingests; long run).

Index + fiction will be recreated idempotently; tables re-materialized.

### 5. Report to AI-DM-Assistant inbox

When Briefings 7+8 acceptance Cypher is green and section links exist, post summary to AI-DM-Assistant `docs/inbox/` per briefing checklists.

---

## Reference

| Artifact | Path |
|---|---|
| Index contract | `games/mork-borg/passage-sections.json` v0.3.0 |
| Manifest | `games/mork-borg/ingest-manifest.json` v0.3.4 (`rulebook_index` block) |
| Briefing 6 | `docs/pdf-graph-builder-briefing-6.md` |
| Briefing 7 | `docs/pdf-graph-builder-briefing-7.md` |
| Briefing 8 | `docs/pdf-graph-builder-briefing-8.md` |
| Implementation | `backend/src/index_materialization.py`, `backend/src/section_chunking.py` |
| CLI | `materialize-passage-sections.ps1`, `materialize-rulebook-index.ps1` |

---

## Session notes

- Prior ingest attempt failed with `httpx.ConnectError WinError 10061` — backend was not running. Fix: start `backend\start.ps1` before `ingest-morkborg.ps1`.
- Bootstrap prerequisite for Briefing 8 confirmed before ingest: `Monster`, `Creature`, `Place`, `Faction`, `WorldLore`, `SupportingCharacter` seeds all present in `morkborg`.
