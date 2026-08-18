# Briefing 25: Retarget morale `If` spines `FOR` `MoraleCheck`

**For pdf-graph-builder agents.** Handoff-24 leftover: morale procedure spines currently `FOR` sheet `SeedNode:Morale` (`HAS_MORALE` target). ADA has locked a dedicated procedure label. **Retarget `for_procedure` only.** Do not invent `Reaction` SeedNodes. Do not change D4 sheet edges. Do not start 2d.

Lineage: [handoff-24](../inbox/ai-dm-assistant-handoff-24.md) remaining WIP; [DESIGN §8.2.4](../../DESIGN.md#824-altitude-d-build-plan-dependency-order) (same split as `MeleeAttack` vs `Strength`).

---

## Why

| Label | Role | Edges |
|---|---|---|
| **`Morale`** | Sheet score | `Creature/Monster-[:HAS_MORALE]->`; Compare `COMPARED_TO` |
| **`MoraleCheck`** | Procedure (2d6 vs that score) | `If-[:FOR]->` |

Handoff-24 P5 greened “no invented MoraleCheck” so 2c could land on existing wiring. That reuse mixes S4 (*What’s a Goblin’s morale?*) with M2 (*how does morale work?*). Sheet slot stays procedure-free.

**ADA already changed** (this repo):

| File | Change |
|---|---|
| `corpus/seeds/frameworks/osr-d20-dc.json` | **0.3.0** — `MoraleCheck` `SPECIALIZES` `Test`; `If FOR MoraleCheck`; `MoraleCheck COMPARED_TO Morale` |
| `corpus/games/mork-borg/deltas.json` | **0.4.1** — 2c labels / contract gap |
| `corpus/games/mork-borg/operational-spines.json` | **0.4.1** — three `if:morale-*` `for_procedure`: **`MoraleCheck`** (`compared_to` still **`Morale`**) |
| `backend/app/retrieval.py` | R16 selects `If-[:FOR]->MoraleCheck` (no fallback to sheet `Morale`) |

Until pgb retargets, **M2 is red** (fail closed). S4 must stay R17 `HAS_MORALE`.

---

## Operator order (required)

Seed bump → **principle 7**: wipe then bootstrap, then re-ingest. Additive bootstrap alone is not enough.

**ADA (before pgb ingest):**

```powershell
cd D:\GitHub\AI-DM-Assistant
python schema/reset_db.py --game mork-borg --confirm
python schema/bootstrap.py --game mork-borg
```

**Expect after bootstrap:** `(:MoraleCheck:SeedNode)` exists; `(:Morale:SeedNode)` still exists for sheets. No Tier-5 `If` nodes yet.

**pgb:** full `.\ingest-morkborg.ps1` (`section_phase` ≥ 2) so D1–D4 + 2c return after the wipe. Product path is `/extract`, not chaining `materialize-*` as the success path. If you rematerialize spines from JSON, `for_procedure` must resolve to **SeedNode `MoraleCheck`**.

**Contract SoT:** `operational-spines.json` — match ADA **0.4.1** (`for_procedure`: `MoraleCheck`). Promote ADA mirror after you edit pgb SoT if that file is authored in pgb; the three morale spines must not say `for_procedure: Morale`.

---

## Do / do not

**Do**

- Point `if:morale-trigger`, `if:morale-demoralized`, `if:morale-flee-or-surrender` `FOR` → `MoraleCheck` SeedNode.
- Keep Compare `compared_to` / `COMPARED_TO` → sheet **`Morale`**.
- Keep Goblin (and all creatures) `HAS_MORALE` → `:Morale:IngestNode` (value **7** on Goblin).
- Keep Reaction + Morale `IndexEntry-[:MAPS_TO_SECTION]->reaction-morale`.
- Keep `ReactionTable`.

**Do not**

- `FOR` sheet `Morale`.
- Retarget `HAS_MORALE` to `MoraleCheck`.
- Invent `Reaction` / extra morale SeedNodes.
- Materialize a flee d6 lookup table in this briefing (still a listed 2c gap).
- Encode DR / Goblin 7 / demoralized bands in ADA prompts (not your job; do not ask ADA to).
- Expand into 2d (`getting-better-or-worse`).

---

## Acceptance Cypher (database `morkborg`)

### P0 — scaffold

```cypher
MATCH (n:SeedNode)
WHERE n:MoraleCheck OR n:Morale
RETURN labels(n) AS labels, n.name
ORDER BY n.name
```

**Expect:** both `MoraleCheck` and `Morale` SeedNodes.

### P1 — no procedure on the sheet slot

```cypher
MATCH (i:If)-[:FOR]->(p)
WHERE p:Morale OR (p:SeedNode AND coalesce(p.name,'') = 'Morale')
RETURN i.id, labels(p), p.name
```

**Expect:** **0 rows.**

### P2 — three spines on the procedure

```cypher
MATCH (i:If:IngestNode)-[:FOR]->(p:MoraleCheck)
RETURN coalesce(i.id,'') AS if_id
ORDER BY if_id
```

**Expect:** `if:morale-demoralized`, `if:morale-flee-or-surrender`, `if:morale-trigger` (and only those morale procedure ids).

### P3 — threshold is still the sheet score

```cypher
MATCH (i:If {id:'if:morale-demoralized'})-[:`IF`]->(b)-[:HAS_ATOM]->(c:Compare)
OPTIONAL MATCH (c)-[:COMPARED_TO]->(m)
RETURN c.op, c.left, labels(m) AS compared_labels, coalesce(m.name,'') AS compared_name
```

**Expect:** Compare greater-than 2d6; `COMPARED_TO` **`Morale`** (not `MoraleCheck`, not a numeric DR).

### P4 — D4 sheet hop unchanged

```cypher
MATCH (g)-[:HAS_MORALE]->(m:Morale)
WHERE toLower(coalesce(g.name,g.title,'')) CONTAINS 'goblin'
RETURN coalesce(g.name,g.title) AS creature, m.value
```

**Expect:** Goblin morale **7**. Target label **`Morale`**, not `MoraleCheck`.

### P5 — D1 still `FOR` attack procedures (sanity after reset+ingest)

```cypher
MATCH (i:If {id:'if:melee-hit-default'})-[:FOR]->(p)
RETURN labels(p), coalesce(p.name,'')
```

**Expect:** `MeleeAttack`.

---

## ADA smokes (after handoff)

```powershell
cd D:\GitHub\AI-DM-Assistant\backend
.\venv\Scripts\python.exe -m smokes.cli_chat --suite 2c --check-context
.\venv\Scripts\python.exe -m smokes.smoke_d4_select_hop
.\venv\Scripts\python.exe -m smokes.cli_chat --suite all --check-context
```

| Smoke | Expect |
|---|---|
| **M1** | `answer_path=table` — Reaction 7–8 Indifferent |
| **M2** | `answer_path=llm` — CONTEXT has `If-[:FOR]->MoraleCheck`; 9>7 → demoralized; **not** S4 sheet-only |
| **S4** | R17 `HAS_MORALE` **7** — **not** morale procedure spines as the answer |

---

## Out of slice

`getting-better-or-worse` (2d), flee d6 table, `passage_split` on the Morale heading, PC sheets, bake-off.

---

## Promote

```powershell
# pgb → ADA inbox after you write the handoff:
Copy-Item -Force .\docs\ai-dm-assistant-handoff-25.md D:\GitHub\AI-DM-Assistant\docs\inbox\
```
