# AI-DM-Assistant Handoff 22: Coverage 2c — ReactionTable + rematerialize

**From:** pdf-graph-builder  
**Date:** 2026-08-16  
**Context:** Follow-up to [handoff-21](./ai-dm-assistant-handoff-21.md) / [Briefing 24](./pdf-graph-builder-briefing-24.md). Operator PDF review: Reaction (2D6) on p.32 should be a lookup table (same class as Initiative), not prose-only. Briefing P3 “no table” **reopened**.

**Verdict:** **ReactionTable green** (5 rows) + section/catalog **re-materialized** after the contract fix. P2 still green. **Ball remains with ADA** — promote contracts, prefer table rows for M1 when retrieving.

---

## What was vs wasn’t stale

| Work | On bad data? |
|---|---|
| Handoff-21 `MAPS_TO_SECTION` (Reaction + Morale) | **No** — section Chunk stream already had correct p.32 prose; only catalog links were missing |
| Anything that assumed structured reaction **bands as `:HAS_ENTRY` rows** | **Yes** — table did not exist until this follow-up |
| Full Ollama `/extract` | **Not required** for this fix (no seed-evidence change) |

After declaring the table, we **re-ran** (no full ingest):

1. `materialize_passage_sections` (phase ≤ 2) — refresh `reaction-morale` Chunk / passages  
2. `link_index_entries_to_sections` — re-assert P2  
3. `run_lookup_table_pipeline(table_names=['ReactionTable'])` — 5 rows

---

## Contracts to promote

| File | Version | Change |
|---|---|---|
| `passage-sections.json` | **0.5.12** | `contains_lookup_tables: ["ReactionTable"]`; prior `index_titles` Reaction+Morale |
| `ingest-manifest.json` | **0.3.6** | `ReactionTable` (`range_list` 2-3…11-12, stop before Morale) |

ADA: `sync-passage-sections-from-pgb.ps1` + pull ingest-manifest when your sync direction allows (ADA SoT note on manifest — reconcile with this pgb addition).

---

## Proof (pasted)

### ReactionTable

```cypher
MATCH (t:ReactionTable)-[:HAS_ENTRY]->(r:TableEntry)
RETURN t.id AS table, count(r) AS entry_count
```

| table | entry_count |
|---|---|
| ReactionTable | **5** |

```cypher
MATCH (t:ReactionTable)-[:HAS_ENTRY]->(r:TableEntry)
RETURN r.id AS entry, r.cells AS cells
ORDER BY r.id
```

| entry | cells (abbrev) |
|---|---|
| ReactionTable:row:2-3 | 2-3 / Kill! |
| ReactionTable:row:4-6 | 4-6 / Angered |
| ReactionTable:row:7-8 | 7-8 / Indifferent |
| ReactionTable:row:9-10 | 9-10 / Almost friendly |
| ReactionTable:row:11-12 | 11-12 / Helpful |

### P2 still green

```cypher
MATCH (e:IndexEntry)-[:MAPS_TO_SECTION]->(c:Chunk {section_id: 'reaction-morale'})
RETURN e.title ORDER BY e.title
// Morale, Reaction
```

Section Chunk remains prose stream (441 chars) + structured rows on `:ReactionTable` (pdf-as-md renders the Markdown table via `resolve_tables_in_span`).

---

## Smokes

| Id | Note |
|---|---|
| **M1** | Prefer `ReactionTable` / declared section — band **7–8 Indifferent** |
| **M2** | Unchanged — Morale → `MAPS_TO_SECTION` (procedure prose, not a flee-d6 table) |

No flee/surrender d6 table invented.

---

## Promote

```powershell
Copy-Item -Force .\docs\ai-dm-assistant-handoff-22.md D:\GitHub\AI-DM-Assistant\docs\inbox\
```
