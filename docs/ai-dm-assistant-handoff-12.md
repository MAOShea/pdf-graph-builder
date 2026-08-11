# AI-DM-Assistant Handoff 12: Briefing 15 — Crit / fumble / rest slice 2b

**From:** pdf-graph-builder  
**Date:** 2026-08-10  
**Context:** [Briefing 15](./pdf-graph-builder-briefing-15.md) — combat slice 2b parse / chunk preconditions.

**Verdict:** **P0–P4 green** on operator DB `morkborg`. **Ball is with ADA** — run standing smokes **R1–R4**. No new table; no new seeds invented.

---

## Gate checklist

| Gate | Status | Notes |
|---|---|---|
| **P0** text layer p.31 | ✅ | Crit / Fumble / round / Rest extractable |
| **P1** section anchors | ✅ | `crit-fumble-rest` pages 31–31; Reaction excluded; not a Violence dump |
| **P2** RulePassages | ✅ | 4 passages via `subheading_regex` (Crit body / Fumble / round / Rest) |
| **P3** no new table | ✅ | Prose only — no CritTable/RestTable |
| **P4** no fiction fan-out | ✅ | `links_to_seed_labels: []`; zero fiction evidence edges |

---

## Graph (observed)

```cypher
MATCH (c:Chunk {section_id: 'crit-fumble-rest'})
RETURN c.section_title, c.page_number_start, c.page_number_end, c.source_format, size(c.text)

MATCH (c:Chunk {section_id: 'crit-fumble-rest'})-[:DOCUMENTED_BY]->(p:RulePassage)
RETURN p.id, left(p.text, 100) ORDER BY p.id
```

| Item | Value |
|---|---|
| Section Chunk | `Crit, fumble, and rest`, pages 31–31, `passage-section`, ~860 chars |
| Body start | Crit attack prose (double damage; armor −1 tier; defence free attack) |
| Body end | Infected: no rest benefit; d6 HP lost daily |
| `#p0` | Crit attack / defence outcomes |
| `#p1` | Fumble (natural 1) attack / defence + armor tier ruin |
| `#p2` | How long is a round? |
| `#p3` | Rest (d4 / d6 / starve / infection) |
| Fiction pollution | **0** |
| Seed CONFIRMS from these passages | **0** (by design) |

---

## Contract change (pgb SoT)

| File | Change |
|---|---|
| `passage-sections.json` **v0.5.7** | `crit-fumble-rest` → `passage_granularity: subheading_regex` + split on `Fumble (natural 1)` / `How long is a round?` / `Rest` |

Landed via `.\materialize-passage-sections.ps1 -Phase 2` (recovery). Full `.\ingest-morkborg.ps1` optional, not required before R1–R4.

Promote: copy `passage-sections.json` pgb → ADA corpus (already done with this handoff sync).

---

## Known WIP / non-blockers

1. Chunk body **omits** the start heading line `Crit (natural 20)` (standard section model: body after heading). Crit facts are in `#p0`; catalog/section title still says Crit.
2. Rest bullets use PDF dingbats (`†` / control chars) in text — readable enough for smokes; do not treat as parse failure.
3. No Crit/Fumble/Rest SeedNodes — retrieval via section / IndexEntry / passage text (ADA may add seeds later).

---

## ADA next (required)

| Id | Question | Expect in CONTEXT |
|---|---|---|
| **R1** | I crit on a melee attack (natural 20). What happens to damage and armor? | Double damage; armor −1 tier |
| **R2** | I fumbled my defence (natural 1). What happens? | Double damage; armor −1 tier |
| **R3** | How much HP do I recover if I catch my breath and drink? | Restore d4 HP |
| **R4** | My character is infected — do they heal from a full night's sleep? | No rest benefit; d6 HP lost daily |

Report smoke results (pass / fail + bucket).
