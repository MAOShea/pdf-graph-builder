# AI-DM-Assistant Handoff 4: Briefings 6–8 phase 1 green

**From:** pdf-graph-builder  
**Date:** 2026-08-03  
**Context:** Follows Briefings [6](./pdf-graph-builder-briefing-6.md) (section chunking), [7](./pdf-graph-builder-briefing-7.md) (rulebook index), [8](./pdf-graph-builder-briefing-8.md) (typed fiction). Full ingest via `.\ingest-morkborg.ps1` → `POST /extract` (`scaffold-diff`) against bootstrapped `morkborg`.

**Verdict:** Phase 1 acceptance for Briefings 6–8 is **green** on a single full `/extract` path (no parallel materialize CLIs required).

---

## Coverage (`check_coverage.py`)

```
Seeds:     60/60 ingest-confirmed (0 research-only)
Tables:    50/50 OK
Bundles:   6/6 (SELECTS 6/6, CONTAINS 12/12)
Flags:     84 open (FlaggedRelationship: 84; OVERRIDES_SEED: 0)
Phase 1:   DRTable 7 rows -> Agility, RulePassage 6, AbilityTest 1
Index:     entries=81 (CREATURES=12, RULES=41, THE_WORLD=28), section_links=4, fiction=40
Chunks:    116 (pages 1-76)

PASS
```

---

## Briefing status

| Briefing | Status | Evidence |
|---|---|---|
| **6** Section chunking | ✅ phase 1 | 4 section `:Chunk` nodes (`#section:`), 6 `RulePassage`, token chunks superseded on overlap pages |
| **7** Rulebook catalog | ✅ | 81 `IndexEntry` (28 / 12 / 41), `MAPS_TO_SECTION` = 4 (phase-1 RULES titles) |
| **8** Fiction instances | ✅ | 40 typed entities: 13 Place, 12 Creature, 9 SupportingCharacter, 3 Faction, 3 WorldLore; 0 `:Location` |

Default ingest uses **`section_phase=1`** (4 of 17 sections in `passage-sections.json`). Raising phase is a pdf-graph-builder follow-up.

---

## Bug fixed in this cycle

Section chunking during `/extract` previously preferred LangChain page text over PyMuPDF. Anchors in `passage-sections.json` were validated against PyMuPDF, so all phase-1 headings failed silently (0 section chunks).

**Fix:** `backend/src/section_chunking.py` → `_load_page_texts()` prefers PDF on disk when available. Verified on a clean full ingest after backend restart.

---

## Operational model (for ADA agents)

- **Canonical path:** `backend\start.ps1` + Ollama + Neo4j → `.\ingest-morkborg.ps1` (same `/extract` as the web UI).
- **`materialize-*` scripts** are recovery/dev only, not the operator workflow.
- Cleanup on ingest clears ingest data; scaffold seeds remain — no re-bootstrap unless the DB was wiped.

---

## What AI-DM-Assistant can use now

```cypher
:use morkborg

-- RULES index → section chunk → passages
MATCH (e:IndexEntry {column:'RULES'})-[:MAPS_TO_SECTION]->(c:Chunk)
OPTIONAL MATCH (p:RulePassage)
WHERE p.id STARTS WITH c.id + '#p' OR p.section_id = c.section_id
RETURN e.title, c.section_id, count(p) AS passages
ORDER BY e.title;

-- Fiction catalog
MATCH (e:IndexEntry)-[:DENOTES]->(x)-[:INSTANCE_OF]->(seed:SeedNode)
WHERE e.column IN ['THE_WORLD','CREATURES']
RETURN e.entry_kind, labels(seed) AS seed_labels, count(x) AS n
ORDER BY e.entry_kind;

-- Places (no Location label)
MATCH (e:IndexEntry {entry_kind:'place'})-[:DENOTES]->(x)-[:INSTANCE_OF]->(:Place:SeedNode)
RETURN x.name ORDER BY x.name;
```

Prefer `ingest-confirmed` seeds + `RulePassage` / section chunks for rule answers. Prefer typed fiction `IngestNode`s (via `DENOTES`) for “who/where/what creature” over keyword chunk search.

---

## Open / next

| Item | Owner |
|---|---|
| Expose / raise `section_phase` on full ingest (all 17 sections) | pdf-graph-builder |
| Triage 84 `FlaggedRelationship` (promote legitimate rels into scaffold) | AI-DM-Assistant + operator |
| Runtime retrieval updates for `IndexEntry` / `RulePassage` / fiction | AI-DM-Assistant |
| Report when phase > 1 is green | pdf-graph-builder |

---

## Copy into ADA inbox

Place this file at:

`AI-DM-Assistant/docs/inbox/ai-dm-assistant-handoff-4.md`
