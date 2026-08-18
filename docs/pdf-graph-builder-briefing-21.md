# Briefing 21: Stop seed evidence fan-out onto front-matter (colophon / occult)

**For pdf-graph-builder agents.** Hot fix — same class as [briefing-12](./pdf-graph-builder-briefing-12.md) (broad `CONFIRMS_SEED` / `DOCUMENTED_BY` onto unrelated pages), now confirmed on **front-matter** sections that ADA packs into every combat ask.

**This is an ingest / evidence-routing bug in pdf-graph-builder — not an ADA short-circuit or prompt fix.**

**Do not require ADA reset+bootstrap** for this briefing. Scaffold is fine. Delete bad Tier-5 evidence edges (and prevent re-writing them). Preserve D1–D3 `If` spines, entity passages, tables.

---

## Symptoms (ADA, 2026-08-14)

Standing combat / Goblin asks retrieve a large block:

```text
Rule passages (via seed evidence):
[p.3 / occult-treasures] …
[p.6 / front-matter-colophon-credits] Colophon …
… also character-creation / early pages …
[p.30 / violence-combat] Defence Test Agility DR12 …
```

On a Goblin defence ask, that seed-evidence section alone is **~3.3k chars (~55% of CONTEXT)**. The correct D3 spine (`threshold=14`) is present, but so is default **DR12** Violence prose plus occult items that literally mention DR14/DR12. LLM-only smokes (`cli_chat --no-short-circuit`) still flip Goblin melee/defence to **DR12**.

**Expected:** Front-matter is never evidence for combat / resolution seeds. Colophon and occult treasures must not appear in combat CONTEXT via seed evidence.

---

## Neo4j evidence (operator DB `morkborg`, confirmed)

Front-matter section chunks have **both** `DOCUMENTED_BY` and `CONFIRMS_SEED` from **dozens** of `SeedNode`s — including combat seeds.

```cypher
MATCH (n:SeedNode)<-[r:CONFIRMS_SEED|DOCUMENTED_BY]-(p)
WHERE coalesce(p.section_id, '') IN [
  'occult-treasures',
  'front-matter-colophon-credits',
  'character-names'
]
RETURN p.section_id AS section,
       type(r) AS rel,
       [l IN labels(n) WHERE NOT l IN ['SeedNode','IngestNode']] AS seed_labels,
       coalesce(n.name, n.id) AS seed
ORDER BY section, seed
```

**Sample (non-exhaustive):** `occult-treasures` and `front-matter-colophon-credits` each link to e.g. `MeleeAttack`, `RangedAttack`, `DefenseRoll`, `DR`, `AbilityScore`, `Creature`, `If`, `BoolExpression`, … — effectively a **book-wide fan-out**, not a confirm of that concept.

Combat/resolution → those three sections alone: **~48** edges in one operator count (pair of rel types × seeds).

---

## Root cause (expected)

Same pattern as briefing-12:

- Section / page materialization writes `CONFIRMS_SEED` / `DOCUMENTED_BY` from a chunk onto **many or all** scaffold seeds, or
- A linker treats “any seed active in the extract” as confirmed by every section in the phase.

Front-matter sections (`passage-sections.json`: `occult-treasures`, `front-matter-colophon-credits`, `character-names`, …) are **not** Violence / Tests / Creature evidence.

---

## Required fix

### 1. Delete existing bad edges (immediate cleanup)

Safe cleanup — **do not** delete `If` spines, entity passages, or legitimate Violence evidence:

```cypher
// Preview
MATCH (n:SeedNode)<-[r:CONFIRMS_SEED|DOCUMENTED_BY]-(p)
WHERE coalesce(p.section_id, '') IN [
  'occult-treasures',
  'front-matter-colophon-credits',
  'character-names'
]
RETURN p.section_id AS section, count(r) AS edges
```

```cypher
// Delete
MATCH (n:SeedNode)<-[r:CONFIRMS_SEED|DOCUMENTED_BY]-(p)
WHERE coalesce(p.section_id, '') IN [
  'occult-treasures',
  'front-matter-colophon-credits',
  'character-names'
]
DELETE r
RETURN count(*) AS deleted
```

Widen the section deny-list if other front-matter / title / credits `section_id`s show the same fan-out (check `passage-sections.json` early ids).

Optional broader hygiene (only if preview shows the same pattern): any evidence edge from a front-matter / credits / title `section_id` onto combat seeds `MeleeAttack|RangedAttack|DefenseRoll|DR|AbilityTest|…` — prefer the section deny-list first.

### 2. Prevent on future ingest

| Rule | Detail |
|---|---|
| **No evidence fan-out from front-matter** | Sections such as `occult-treasures`, `front-matter-colophon-credits`, `character-names` must **not** emit `CONFIRMS_SEED` / `DOCUMENTED_BY` onto scaffold `SeedNode`s (unless a future contract explicitly binds a named seed for that section — none today). |
| **Combat seeds ← only combat/tests prose** | `MeleeAttack` / `RangedAttack` / `DefenseRoll` evidence stays on `violence-combat` / `tests-and-dr` / spine `DOCUMENTED_BY` cites — not p.3–6. |
| **Do not “confirm” metamodel seeds from credits** | `If`, `BoolExpression`, `Compare`, `Outcome`, etc. must not gain evidence from the Colophon page. |
| **Handoff gate** | Paste acceptance Cypher below — fail ingest if front-matter still fans out. |

Related prior: briefing-12 (fiction `Creature`/`Place` fan-out). This briefing is specifically **front-matter ↔ any SeedNode**.

### 3. Out of scope

| Deferred | Why |
|---|---|
| ADA reset+bootstrap | Not needed — Tier-5 edge delete only |
| D4 creature sheets ([briefing-20](./pdf-graph-builder-briefing-20.md)) | Separate track; do not block this hot fix |
| ADA deny-list / skip seed evidence when spines selected | Optional packaging shield; **not** a substitute for this fix |
| Re-chunking occult/colophon text | Keep the sections; stop wrong **edges** |

---

## Ops path

1. **No ADA reset.**  
2. Paste this briefing into a pgb session.  
3. pgb: run cleanup Cypher (or equivalent product path), fix linker so re-ingest cannot recreate the fan-out.  
4. Re-smoke evidence gates below; write `docs/ai-dm-assistant-handoff-*.md` and copy into ADA `docs/inbox/`.  
5. ADA operator: re-ask Goblin defence / `cli_chat --suite d3 --check-context --no-short-circuit` — CONTEXT must not contain colophon / occult under seed evidence.

Sync: `.\scripts\sync-outbox-briefings.ps1` from ADA repo root.

---

## Acceptance gates (handoff must paste results)

### E21-P0 — Front-matter has no seed evidence edges

```cypher
MATCH (n:SeedNode)<-[r:CONFIRMS_SEED|DOCUMENTED_BY]-(p)
WHERE coalesce(p.section_id, '') IN [
  'occult-treasures',
  'front-matter-colophon-credits',
  'character-names'
]
RETURN count(r) AS bad_edges
```

**Expect:** `bad_edges = 0`.

### E21-P1 — Combat seeds do not cite occult/colophon

```cypher
MATCH (n:SeedNode)<-[:CONFIRMS_SEED|DOCUMENTED_BY]-(p)
WHERE any(lbl IN labels(n) WHERE lbl IN [
  'MeleeAttack', 'RangedAttack', 'DefenseRoll', 'DR', 'DifficultyRating'
])
AND coalesce(p.section_id, '') IN [
  'occult-treasures',
  'front-matter-colophon-credits',
  'character-names'
]
RETURN count(*) AS bad_combat_evidence
```

**Expect:** `bad_combat_evidence = 0`.

### E21-P2 — Legitimate Violence evidence still present

```cypher
MATCH (n:SeedNode)<-[:CONFIRMS_SEED|DOCUMENTED_BY]-(p)
WHERE any(lbl IN labels(n) WHERE lbl IN ['MeleeAttack', 'DefenseRoll'])
  AND coalesce(p.section_id, '') = 'violence-combat'
RETURN count(*) AS violence_evidence
```

**Expect:** `violence_evidence >= 1` (do not delete real combat cites while cleaning front-matter).

### E21-P3 — D1–D3 spines intact

```cypher
MATCH (i:If:IngestNode)
WHERE i.id IN [
  'if:melee-hit-default',
  'if:defence-default',
  'if:crit-attack',
  'if:d3-2393b8d674143b52'
]
   OR i.id STARTS WITH 'if:d3-'
RETURN count(i) AS spines
```

**Expect:** `spines >= 4` (defaults + at least one D3 Goblin defence id or any `if:d3-*`).

---

## ADA verification (after handoff)

```powershell
cd backend
.\venv\Scripts\python.exe -m smokes.cli_chat --suite d3 --check-context --show-context
# Optional faithfulness baseline (no short-circuit):
.\venv\Scripts\python.exe -m smokes.cli_chat --suite d3 --check-context --no-short-circuit
```

**CONTEXT must not** include `front-matter-colophon-credits` or `occult-treasures` under “Rule passages (via seed evidence)” for Goblin / melee probes.

---

## Handoff checklist

- [ ] E21-P0 `bad_edges = 0`
- [ ] E21-P1 `bad_combat_evidence = 0`
- [ ] E21-P2 Violence evidence retained
- [ ] E21-P3 spines intact
- [ ] Linker/ingest change documented so a future full ingest cannot recreate front-matter fan-out
- [ ] Handoff copied to ADA `docs/inbox/`

---

*Briefing 21 — 2026-08-14 — front-matter seed evidence fan-out (colophon / occult)*
