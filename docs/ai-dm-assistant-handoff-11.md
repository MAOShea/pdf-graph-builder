# AI-DM-Assistant Handoff 11: Briefing 14 — Violence slice 2a parse gates

**From:** pdf-graph-builder  
**Date:** 2026-08-10  
**Context:** [Briefing 14](./pdf-graph-builder-briefing-14.md) — combat slice 2a (Violence) parse / chunk preconditions.

**Verdict:** **P0–P4 green** on operator DB `morkborg`. **Ball is with ADA** — run standing smokes **C1–C4**. No further pgb parse work required for slice 2a unless a smoke fails for bucket 1 (graph/chunking).

---

## Gate checklist

| Gate | Status | Notes |
|---|---|---|
| **P0** text layer | ✅ | Bare Bones p.30 Violence / Initiative / Melee / Ranged / Defence extractable |
| **P1** section anchors | ✅ | `violence-combat` → Crit excluded; `page_number_start/end = 30` |
| **P2** RulePassages | ✅ | 4 passages via `subheading_regex` (intro + Melee + Ranged + Defence) |
| **P3** InitiativeTable | ✅ | 2 range rows `1-3` / `4-6`; manifest `phase: 2` |
| **P4** no fiction fan-out | ✅ | No `Creature` / `Place` / … evidence from Violence section Chunk |

---

## Graph counts (Cypher)

```cypher
MATCH (c:Chunk {section_id: 'violence-combat'})
RETURN c.section_title, c.page_number_start, c.page_number_end, c.source_format, size(c.text)

MATCH (c:Chunk {section_id: 'violence-combat'})-[:DOCUMENTED_BY]->(p:RulePassage)
RETURN p.id, left(p.text, 80) ORDER BY p.id

MATCH (t:InitiativeTable)-[:HAS_ENTRY]->(e)
RETURN e.id, e.cells ORDER BY e.id
```

**Observed:**

| Item | Value |
|---|---|
| Section Chunk | `Violence`, pages 30–30, `passage-section`, body ~465 chars (no Crit) |
| RulePassages | `#p0` initiative intro · `#p1` Melee/STR DR12 · `#p2` Ranged/PRE DR12 · `#p3` Defence/AGI DR12 |
| InitiativeTable rows | `1-3` → enemies go first · `4-6` → PCs go first |
| Fiction pollution from section Chunk | **0** |

---

## Contract / code changes (pgb SoT)

| File | Change |
|---|---|
| `passage-sections.json` **v0.5.6** | `violence-combat` `passage_granularity: subheading_regex` + split on `Melee\|Ranged\|Defence` |
| `ingest-manifest.json` | `InitiativeTable.phase: 2`, acceptance rows for 1–3 / 4–6 |
| `section_chunking.page_at_offset` | Inter-page join newline no longer maps section end → page 1 |
| CLI | (prior) `section_phase` on `/extract`; this landing used recovery materialize + `ingest-tables` |

Contracts already copied to ADA `corpus/games/mork-borg/` (`passage-sections.json` v0.5.6 + `ingest-manifest.json` with InitiativeTable phase 2). Re-pull if your tree is older.

---

## Known WIP / not blockers for C1–C4

1. **No `Initiative` SeedNode** in scaffold — table is materialized; no `USES` edge. Matched-row retrieval by table name still works; ADA may add an Initiative seed + `used_by` later.
2. **Section-level `links_to_seed_labels`** — all four Violence RulePassages `CONFIRMS_SEED` → `MeleeAttack`, `RangedAttack`, and `DefenseRoll` (not per-procedure). No Crit / fiction bleed. Per-passage seed binding is a future refinement if CONTEXT is too wide within combat.
3. Graph updates for this handoff used `materialize-passage-sections.ps1 -Phase 2` + `ingest-tables.ps1 -Tables InitiativeTable` (not a full LLM `/extract`). Full `.\ingest-morkborg.ps1` is optional cleanup, not required before C1–C4.

---

## ADA next (required)

| Id | Question | Expect |
|---|---|---|
| **C1** | How does a melee attack work? I have Strength +1 — what's the DR? | Violence / Melee passage; STR; DR 12 |
| **C2** | I shoot a bow — which ability and DR? | Ranged / Presence; DR 12 |
| **C3** | How do I defend? I rolled 11 on Agility (+0). | Defence / Agility; DR 12; fail on 11 |
| **C4** | Who goes first in a fight? I rolled 4 on the initiative d6. | `InitiativeTable` row `4-6` (PCs go first) |

Report back with smoke results (pass / fail + bucket). Optional later: add `Initiative` seed + `used_by` if you want `USES` wiring.
