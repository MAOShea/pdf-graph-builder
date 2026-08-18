# AI-DM-Assistant Handoff 21: Coverage 2c — Reaction / Morale catalog wiring

**From:** pdf-graph-builder  
**Date:** 2026-08-16  
**Context:** [Briefing 24](./pdf-graph-builder-briefing-24.md) / coverage slice **2c** (`reaction-morale`).

**Verdict:** **P2 green** — both RULES IndexEntries **Reaction** and **Morale** now `MAPS_TO_SECTION` → `Chunk {section_id:'reaction-morale'}`. **Ball is with ADA** — promote `passage-sections.json` v0.5.11, re-smoke **M1 / M2**.

---

## Ops (what we did)

| Action | Done? |
|---|---|
| Contract: `index_titles` = `Reaction`, `Morale` on `reaction-morale` | **Yes** — `games/mork-borg/passage-sections.json` **v0.5.11** |
| Full `.\ingest-morkborg.ps1` | **No** — section Chunk already present (P0/P1) |
| Catalog re-link only | **Yes** — `link_index_entries_to_sections(..., phase=2)` |

```powershell
# From pdf-graph-builder root (after contract edit):
backend\venv\Scripts\python.exe -c "..."  # or re-run link via materialize-rulebook-index.ps1 -Phase 2
# Equivalent durable path:
.\materialize-rulebook-index.ps1 -Phase 2 -NoFiction
```

**Fill mode named:** catalog **re-link** (`MAPS_TO_SECTION` only). No Ollama. No new tables / seeds / spines.

---

## What pgb shipped

| Item | Detail |
|---|---|
| SoT contract | `passage-sections.json` **0.5.11** — `reaction-morale.index_titles`: `["Reaction", "Morale"]` |
| Notes | Slice 2c; combined paragraph passage OK (optional `passage_split` on `Morale` deferred) |
| Tables / seeds | None invented (P3 / P5) |

ADA promote: `sync-passage-sections-from-pgb.ps1` when convenient.

---

## Acceptance Cypher (pasted)

### P1 — Section Chunk focused

```cypher
MATCH (c:Chunk {section_id: 'reaction-morale'})-[:PART_OF]->(:Document {fileName: 'mork-borg.pdf'})
RETURN c.section_id AS section_id, c.source_format AS source_format,
       c.page_number_start AS p_start, c.page_number_end AS p_end,
       size(c.text) AS chars,
       substring(c.text, 0, 140) AS head,
       substring(c.text, size(c.text)-100, 100) AS tail
```

| section_id | source_format | p_start | p_end | chars | head (abbrev) | tail (abbrev) |
|---|---|---|---|---|---|---|
| reaction-morale | passage-section | **32** | **32** | **441** | When meeting… Kill! … Helpful / Morale / Most ene… | …demoralized… (1–3) flees or (4–6) surrenders. |

Body stops before Getting Better; not Violence/Crit mash.

### P2 — Both index rows → section

```cypher
MATCH (e:IndexEntry)-[:MAPS_TO_SECTION]->(c:Chunk {section_id: 'reaction-morale'})
RETURN e.title AS title, c.section_id AS section_id
ORDER BY e.title
```

| title | section_id |
|---|---|
| **Morale** | reaction-morale |
| **Reaction** | reaction-morale |

### DIAG (IndexEntry edges)

```cypher
MATCH (e:IndexEntry)
WHERE toLower(e.title) IN ['reaction', 'morale']
OPTIONAL MATCH (e)-[r]->(n)
RETURN e.title, e.id, type(r) AS rel, labels(n) AS labels,
       coalesce(n.section_id, n.id) AS other
ORDER BY e.title, rel
```

| title | rel | other |
|---|---|---|
| Morale | INDEXED_IN | Document |
| Morale | **MAPS_TO_SECTION** | **reaction-morale** |
| Reaction | INDEXED_IN | Document |
| Reaction | **MAPS_TO_SECTION** | **reaction-morale** |

### P3 / P4 / P5

| Gate | Result |
|---|---|
| P3 no `ReactionTable` / flee-d6 table invent | **Pass** — none added |
| P4 no fiction-seed fan-out from section | **Pass** — only existing `DOCUMENTED_BY` → `RulePassage` (`…#section:reaction-morale#p0`); no `Creature`/`Place` `CONFIRMS_SEED` |
| P5 empty `links_to_seed_labels` | **Pass** — unchanged |

---

## Standing smokes (ADA)

| Id | Expect |
|---|---|
| **M1** | Reaction ask → declared `reaction-morale`; **7–8 Indifferent** |
| **M2** | Morale ask → **same section via Morale → MAPS_TO_SECTION** (not page-32 fallback / not creature `HAS_MORALE` sheet) |

---

## Remaining WIP

- Optional `passage_split` on `^\s*Morale\s*$` (briefing: not blocking 2c).
- Slice **2d** (`getting-better-or-worse`) — out of this briefing.
- THE WORLD place `index_title` warnings during re-link (Galgenbeck, …) are pre-existing / unrelated to 2c.

---

## Promote

```powershell
# From pdf-graph-builder root — promote this handoff into ADA inbox:
Copy-Item -Force .\docs\ai-dm-assistant-handoff-21.md D:\GitHub\AI-DM-Assistant\docs\inbox\

# ADA: sync passage-sections when ready
# .\scripts\sync-passage-sections-from-pgb.ps1
```
