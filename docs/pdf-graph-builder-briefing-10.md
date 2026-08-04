# Briefing 10: Entity-scoped prose for catalog fiction (anti page-bleed)

**For pdf-graph-builder agents.** After Briefings 7–9 (catalog + typed fiction + `INSTANCE_OF` fix), runtime still often attaches **whole-page** `Chunk` text to an `IndexEntry` (ADA page-anchored fallback). On dense pages (e.g. Creatures p.58), one ask for **Goblin** pulls Seth / Bent / Scum / bounty lines into CONTEXT → LLM mixes entities.

**ADA side (done separately):** stricter DM prompt (attribute only the asked entity). That is not enough alone — **narrow the prose graph** so Goblin CONTEXT is Goblin text.

**Prerequisites:**

1. Briefings 7–9 green on `morkborg` (IndexEntry, DENOTES, single `INSTANCE_OF`).
2. Synced `passage-sections.json` / `ingest-manifest.json` (no new contract version required to start; extend if you add passage ids).

**Symptom (ADA smoke):** Q3 Goblin — CONTEXT page-anchored p.58 includes Goblin **and** Bent/Scum/poisoned knife; answer merged neighbors into Goblin.

---

## Goal

For each fiction-relevant `IndexEntry` (at least **CREATURES** and **THE_WORLD**), expose **entity-scoped** text the runtime can prefer over the full page chunk:

```text
(e:IndexEntry)-[:DENOTES]->(entity:IngestNode)
(entity)-[:DOCUMENTED_BY|HAS_PASSAGE]->(p:RulePassage)   // or equivalent
// p.text ≈ only that entity's block (Goblin paragraph), not the whole page
```

Optional but useful:

```text
(e)-[:MAPS_TO_PASSAGE]->(p:RulePassage)
```

ADA already prefers `MAPS_TO_SECTION` → section/`RulePassage`, then page-anchored `Chunk`. Add a path that wins for named entities **before** page chunk.

---

## Scope

| In | Out (this briefing) |
|---|---|
| CREATURES rows → one passage per creature | Full RULES mechanism sections (already briefing-6) |
| THE_WORLD place / supporting_character / faction / world_lore when text is a discrete block | Re-OCR / PDF fix |
| Link passage to existing `IngestNode` from briefing-8 | Changing `entry_kind` ontology |

**Minimum viable:** CREATURES only (highest bleed). WORLD blocks (e.g. Galgenbeck) are usually one topic per page — nice-to-have same pattern.

---

## How to delimit text

Prefer **deterministic** splits over LLM guess:

1. **Heading / name anchors** on the creatures (or world) page — start at entry title (`Goblin`), end before next titled creature / next bold name / next HP line pattern.
2. Operator-maintained spans in contract if needed, e.g. extend `passage-sections.json` or a sibling `entity-passages.json`:

```json
{
  "document": "MÖRK BORG BARE BONES EDITION.pdf",
  "entities": [
    {
      "index_title": "Goblin",
      "column": "CREATURES",
      "page": 58,
      "text_start_hint": "Goblin",
      "text_end_hint": "Head 7s"
    }
  ]
}
```

(Exact schema is yours — document it in the handoff.)

3. Store as `:RulePassage` (or `:IngestNode` passage) with `page`, `section_id` or `entity_id`, `text`.

**Do not** leave Goblin’s only prose as the undifferentiated page `Chunk` if a scoped passage exists.

---

## Materialization sketch

```python
def materialize_entity_passages(graph, file_name: str, ...) -> dict:
    """
    For each fiction IndexEntry (start: CREATURES):
      resolve page text → slice entity span → MERGE RulePassage
      MERGE (entity)-[:DOCUMENTED_BY]->(passage)
      optional MERGE (entry)-[:MAPS_TO_PASSAGE]->(passage)
    Idempotent on passage id = f"{fileName}#entity-passage:{slug}"
    """
```

Reuse page text already in `Chunk` for that page; do not require re-embed if you only add passage nodes + edges (embeddings optional).

---

## Acceptance criteria

```cypher
// Goblin prose must not be only a shared page blob
MATCH (e:IndexEntry {title:'Goblin'})-[:DENOTES]->(x)
OPTIONAL MATCH (x)-[:DOCUMENTED_BY|HAS_PASSAGE]->(p)
OPTIONAL MATCH (e)-[:MAPS_TO_PASSAGE]->(p2)
WITH x, coalesce(p, p2) AS passage
RETURN x.name,
       passage IS NOT NULL AS has_scoped,
       passage.page AS page,
       substring(coalesce(passage.text, ''), 0, 80) AS preview;
// expect has_scoped = true; preview starts with / contains "Goblin";
// preview must NOT be dominated by "Bent" / "Scum" / "Poisoned knife" as primary subject

// Neighbor creature has its own passage
MATCH (e:IndexEntry {title:'Goblin'})-[:DENOTES]->(g)-[:DOCUMENTED_BY|HAS_PASSAGE]->(pg)
MATCH (e2:IndexEntry)-[:DENOTES]->(o)-[:DOCUMENTED_BY|HAS_PASSAGE]->(po)
WHERE e2.column = 'CREATURES' AND e2.title <> 'Goblin' AND po <> pg
RETURN count(DISTINCT e2) AS other_creatures_with_own_passage;
// expect > 0 after full CREATURES pass
```

**Pass:** Asking “Goblin” in ADA (after they prefer entity passage over page chunk) yields CONTEXT without Bent/Scum as Goblin stats.

**Fail:** Only page-level `Chunk` remains for CREATURES entries.

---

## ADA follow-up (not this repo)

After handoff: ADA retrieval should prefer  
`(IndexEntry|IngestNode)→RulePassage` entity text **before** page-anchored `Chunk`. Coordinate edge names (`DOCUMENTED_BY` vs `MAPS_TO_PASSAGE`) in the handoff.

---

## Out of scope

- Rewriting briefing-9 `INSTANCE_OF` logic  
- Raising `section_phase` for all RULES sections (separate)  
- Chat UI / prompts (ADA)

---

## Operator checklist (AI-DM-Assistant)

- [ ] Sync: `.\scripts\sync-outbox-briefings.ps1`
- [ ] Paste this briefing into pgb session
- [ ] After green handoff: wire ADA retrieval preference if edge names differ from current code
- [ ] Re-smoke Q3 Goblin CONTEXT (no Bent/Scum bleed)

---

## Checklist for pgb agent

- [ ] Implement entity-span extraction for CREATURES (MVP)
- [ ] MERGE scoped `RulePassage` + link to fiction `IngestNode` / `IndexEntry`
- [ ] Acceptance Cypher green
- [ ] Document edge type names + id scheme in inbox handoff for ADA
