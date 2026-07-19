# Briefing 8: Typed fiction instances from p.75 catalog

**For pdf-graph-builder agents.** After catalog shells exist ([briefing-7](./pdf-graph-builder-briefing-7.md)), create **Tier-5 typed instances** for WORLD and CREATURES rows and link them to seed types from the refreshed scaffold.

**Prerequisites (strict order):**

1. AI-DM-Assistant: **reset + bootstrap** `morkborg` so Tier 0–4 include `Monster`, `SupportingCharacter`, `Place`, `Faction`, `WorldLore`, and MB `Creature` → `Monster` (`ludemes.json` ≥ 0.3.0, `deltas.json` ≥ 0.3.0).
2. [Briefing 7](./pdf-graph-builder-briefing-7.md) — `RulebookIndex` / `IndexEntry` materialization (or implement 7 + 8 in one pass).
3. Synced contracts: `passage-sections.json` ≥ **0.3.0** (rows carry `entry_kind`), `ingest-manifest.json` ≥ **0.3.5** (`entry_kind_to_seed`).

**Design reference:** [DESIGN.md §4.6](../../DESIGN.md#46-ontology-altitudes-platform-resolution-fiction) · [§8.5](../../DESIGN.md#85-rulebook-catalog-layer-p75-index) · [§8.6](../../DESIGN.md#86-full-document-retrieval-standard-query-suite)

**Synced artifacts:**

```powershell
# From AI-DM-Assistant — prefer merge for ingest-manifest if pgb has a longer copy
.\scripts\sync-ingest-manifest.ps1   # may overwrite; see ingest-manifest-sync.md note
.\scripts\sync-outbox-briefings.ps1
```

| Path | Role |
|---|---|
| `games/mork-borg/passage-sections.json` | `index_source.*.entry_kind` on each row |
| `games/mork-borg/ingest-manifest.json` | `rulebook_index.materialization.entry_kind_to_seed` |
| AI-DM-Assistant `corpus/games/mork-borg/deltas.json` → `notes.the_world_index` | Operator routing rationale (read-only for pgb) |

---

## Problem

Briefing-7 alone yields **catalog labels**. Runtime and full-document retrieval need **typed entities**:

| Query | Needs |
|---|---|
| “What places are in the book?” | `Place` instances, not untyped `IndexEntry` |
| “Who is Fathmu IX?” | `SupportingCharacter` instance |
| “List creatures” | `Creature` instances (+ optional StatBlock later) |

THE WORLD is **mixed** — never call rows “locations” just because they are geographic. Use `Place` / `Faction` / `WorldLore` / `SupportingCharacter` per `entry_kind`.

---

## Ontology (already in Neo4j after bootstrap)

```text
GameWorld
└── Setting                         ← one product Setting instance (see below)
      ← Place / Faction / WorldLore / SupportingCharacter  (OCCURS_IN)

NonPlayerCharacter
├── Monster
└── SupportingCharacter

Creature -[:SPECIALIZES]-> Monster   ← Mörk Borg Tier 4
```

**Do not** create a `Location` label. Prefer `Place`.

---

## Contract: `entry_kind` → seed label

From `ingest-manifest.json` → `rulebook_index.materialization.entry_kind_to_seed`:

| `entry_kind` | Seed label (`INSTANCE_OF`) |
|---|---|
| `place` | `Place` |
| `supporting_character` | `SupportingCharacter` |
| `faction` | `Faction` |
| `world_lore` | `WorldLore` |
| `creature` | `Creature` |
| `rule_topic` / `optional_class` / `equipment_category` | *(no fiction instance in this briefing — RULES stays catalog-only for now)* |

`passage-sections.json` v0.3.0 already sets `entry_kind` on WORLD / CREATURES / RULES rows. Operator may amend kinds; re-run materializer after sync.

---

## Graph model (Tier 5)

### A. Setting shell (once per document / game DB)

```cypher
// Pseudocode — MERGE stable id
(:IngestNode:SettingInstance {
  id: $fileName + '#setting',
  name: 'Mörk Borg',           // or 'Dying World' — operator choice
  tier: 5
})-[:INSTANCE_OF]->(:Setting:SeedNode)

MATCH (gw:GameWorld:SeedNode)
MATCH (s {id: $fileName + '#setting'})
MERGE (s)-[:PART_OF]->(gw)     // if Setting seed already PART_OF GameWorld, instance may OCCURS_IN Setting seed instead — pick one pattern and stay consistent
```

Preferred: instance `OCCURS_IN` the **seed** `Setting` node (scaffold), or `INSTANCE_OF` Setting + property `name`. Simplest consistent pattern:

```text
(:IngestNode {name:'Mörk Borg'})-[:INSTANCE_OF]->(:Setting:SeedNode)
(placeInstance)-[:OCCURS_IN]->(:Setting:SeedNode)   // link to seed Setting
```

If multiple Setting seed nodes exist, match by `name` / `seed_id`. Bootstrap should create one `:Setting:SeedNode`.

### B. Typed instance per WORLD / CREATURES IndexEntry

For each `IndexEntry` with `entry_kind` in the fiction map:

| Property | Example |
|---|---|
| `id` | `{fileName}#entity:place:galgenbeck` |
| `name` | `Galgenbeck` (from `IndexEntry.title`) |
| `tier` | 5 |
| Labels | `:IngestNode` + optional convenience label matching type (`:Place` instance may use labels `IngestNode` only + `INSTANCE_OF` — **do not** add `:SeedNode`) |

Relationships:

```text
(e:IndexEntry)-[:INSTANCE_OF]->(entity)           // or (entity)<-[:INDEXES]-(e) — prefer:
(e)-[:DENOTES]->(entity)
(entity)-[:INSTANCE_OF]->(SeedNode for type)      // Place / Faction / …
(entity)-[:OCCURS_IN]->(:Setting:SeedNode)        // WORLD types only; skip for Creature
(entity)-[:DOCUMENTED_BY|CITED_ON]->(page hint)   // optional: page from IndexEntry.page
```

**Recommended edges (pick and document in code):**

```cypher
MERGE (e)-[:DENOTES]->(entity)
MERGE (entity)-[:INSTANCE_OF]->(seedType)
// WORLD only:
MERGE (entity)-[:OCCURS_IN]->(settingSeed)
```

CREATURES: `INSTANCE_OF` → `Creature` seed (not bare `Monster`). Optional later: `MAPS_TO` StatBlock when extract exists.

### C. Idempotency

MERGE on `entity.id`. Re-run safe. If `entry_kind` changes, update `INSTANCE_OF` target and log warning.

---

## Module: extend `index_materialization.py` (or `fiction_instance_materialization.py`)

```python
def materialize_fiction_instances(
    graph,
    file_name: str,
    *,
    game: str = "mork-borg",
) -> dict[str, int]:
    """
    For each IndexEntry with a fiction entry_kind, MERGE typed IngestNode
    and INSTANCE_OF / DENOTES / OCCURS_IN edges.
    Returns counts by entry_kind + warnings.
    """
```

Load `entry_kind_to_seed` from ingest-manifest. Skip RULES kinds in this briefing.

---

## Acceptance criteria

After bootstrap + briefing-7 + this briefing (`:use morkborg`):

```cypher
// Scaffold present
MATCH (m:Monster:SeedNode), (c:Creature:SeedNode)-[:SPECIALIZES]->(m)
MATCH (p:Place:SeedNode), (f:Faction:SeedNode), (w:WorldLore:SeedNode)
RETURN m.name, c.name, p.name, f.name, w.name;

// Typed places
MATCH (e:IndexEntry {column:'THE_WORLD', entry_kind:'place'})-[:DENOTES]->(x)-[:INSTANCE_OF]->(p:Place:SeedNode)
RETURN count(x) AS places;  // expect 13 with current contract

// People
MATCH (e:IndexEntry {entry_kind:'supporting_character'})-[:DENOTES]->(x)-[:INSTANCE_OF]->(:SupportingCharacter:SeedNode)
RETURN x.name ORDER BY x.name;

// Creatures use Creature alias
MATCH (e:IndexEntry {column:'CREATURES'})-[:DENOTES]->(x)-[:INSTANCE_OF]->(:Creature:SeedNode)
RETURN count(x) AS creatures;  // expect 12

// No Location label leakage
MATCH (n) WHERE n:Location OR 'Location' IN labels(n)
RETURN count(n);  // expect 0
```

**Pass:** WORLD rows typed; CREATURES → `Creature`; no `Location` nodes; Setting seed linked via `OCCURS_IN` for WORLD entities.

**Fail → operator:** amend `entry_kind` in `passage-sections.json`, re-sync, re-run.

---

## Out of scope

- Lore/creature **section** chunking (heading anchors for WORLD pages) — later
- StatBlock extract for all CREATURES — link when blocks exist
- RULES → mechanism seed `MAPS_TO_SEED` — can follow; not required for fiction gate
- Chat / retrieval changes in AI-DM-Assistant

---

## Operator checklist (AI-DM-Assistant side)

- [ ] `python schema/reset_db.py --game mork-borg --confirm`
- [ ] `python schema/bootstrap.py --game mork-borg`
- [ ] Sync `passage-sections.json` v0.3.0 + briefings to pgb
- [ ] Confirm scaffold Cypher above (Monster/Creature/Place/…)
- [ ] Paste this briefing into pgb session

---

## Checklist for pgb agent

- [ ] Confirm seed types exist (abort with clear error if `Place` / `Creature` SeedNodes missing)
- [ ] Implement fiction instance materializer (DENOTES + INSTANCE_OF + OCCURS_IN)
- [ ] Read `entry_kind` from contract rows (not LLM guess)
- [ ] CREATURES → `Creature` only
- [ ] Zero `:Location` labels
- [ ] Acceptance Cypher green
- [ ] Report to AI-DM-Assistant [inbox](../inbox/)
