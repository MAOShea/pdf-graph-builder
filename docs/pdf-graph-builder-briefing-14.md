# Briefing 14: Parse / chunk preconditions for combat slice 2a (Violence)

**For pdf-graph-builder agents.** ADA has scoped coverage **slice 2a — Violence core** ([OQ-COV-02](../../DESIGN.md#155-product-coverage-and-poc-scope)). Before treating combat ingest as “done,” **PDF → focused evidence** must meet the preconditions below.

**Context:** pgb’s ability to turn the Bare Bones PDF into meaningful, well-focused chunks / passages is still **WIP**. This briefing states **acceptance gates on parsing quality**, not a request to invent ontology or to paper over bleed in ADA.

**Do not skip to “full combat extract success”** until these gates are green (or explicitly blocked with a handoff saying which gate failed).

---

## Slice 2a target (what must be parseable)

| Contract | Id / name | Role |
|---|---|---|
| `passage-sections.json` | `violence-combat` (phase **2**) | Declared section: Violence → stop before `Crit (natural 20)` |
| `ingest-manifest.json` (**pgb SoT**) | `InitiativeTable` | d6 range table on p.30 (1–3 / 4–6), not six singleton rows — **set `phase: 2` in pgb** for slice 2a (may still be phase 3 in older mirrors) |
| Seeds (already in scaffold) | `MeleeAttack`, `RangedAttack`, `DefenseRoll` | SPECIALIZES `AbilityTest`; MB delta binds STR / PRE / AGI |

**Out of slice (do not require for 2a):** `crit-fumble-rest`, reaction/morale, armor tables, powers, optional classes.

**Ops path (when parsing is ready):** full `POST /extract` via `.\ingest-morkborg.ps1` with **`section_phase` ≥ 2**. Not `materialize-*` as the product path ([briefing-13](./pdf-graph-builder-briefing-13.md)).

**Contract SoT:** edit `ingest-manifest.json` / `passage-sections.json` in **pdf-graph-builder**. ADA only **promotes** mirrors (`sync-ingest-contracts-from-pgb.ps1`, `sync-passage-sections-from-pgb.ps1`). There is no ADA → pgb push for these files.

---

## Why parsing quality is the bottleneck

ADA retrieval already prefers:

1. Declared `passage-section` Chunks  
2. Entity / rule `RulePassage` evidence  
3. Lookup-table rows  

Page-anchored whole-page Chunks are a **last resort**. If Violence lands as “all of p.30” or bleeds into Crit / Rest, combat smokes will fail for **bucket 1 (graph / chunking)** — not something ADA should trim with prompts ([DESIGN §4.5](../../DESIGN.md#45-mechanism-coverage-phases-per-system) step 3, [§8.4](../../DESIGN.md#84-section-driven-chunking-heading-anchors)).

---

## Preconditions the parser / section materializer must fulfill

### P0 — Text layer is usable

- [ ] PDF text layer for Bare Bones p.30 (Violence / Initiative / melee / ranged / defence) is extractable without empty or garbage OCR-only gaps at the Violence heading.
- [ ] Heading lines used by the contract are visible in the same text stream the section matcher uses (not only in a layout channel the matcher ignores).

### P1 — Section anchors resolve (declared section)

Contract (`violence-combat`):

```text
start: ^\s*Violence\s*$
end:   ^\s*Crit\s*\(natural 20\)\s*$
```

- [ ] **Start hits** exactly once (or documented unique win) on the combat chapter heading.
- [ ] **End hits** the Crit heading; section body **excludes** Crit / fumble / rest prose.
- [ ] Materialized `Chunk` has `source_format: "passage-section"`, `section_id: "violence-combat"`, body = text **after** start heading through **before** end heading.
- [ ] Body is **not** an undifferentiated full-page dump of p.30+31 when the contract only asks for Violence→Crit.

Shape (same as briefing-13):

```text
(:Chunk {
  id: "{file}#section:violence-combat",
  section_id: "violence-combat",
  section_title: "Violence",
  text,  // focused section body
  page_number_start / page_number_end,
  source_format: "passage-section"
})-[:PART_OF]->(:Document)
```

### P2 — Intra-section focus (paragraph / RulePassage)

Slice 2a answers need **mechanism focus**, not a single blob that mixes initiative + three procedures + damage as one undifferentiated string with no structure.

- [ ] Within `violence-combat`, paragraph (or contract `passage_granularity`) `RulePassage` nodes exist so melee / ranged / defence / initiative can be cited without pulling Crit.
- [ ] A passage about **melee** does not need to omit every other Violence sentence, but it **must not** include the next chapter (`Crit…`) or unrelated index topics from other pages.
- [ ] No “neighbor bleed” from THE WORLD / CREATURES / optional-class pages into Violence evidence (same anti-bleed bar as [briefing-10](./pdf-graph-builder-briefing-10.md) / [briefing-11](./pdf-graph-builder-briefing-11.md)).

### P3 — Initiative table is a real table extract

`InitiativeTable` in `ingest-manifest.json`:

- [ ] Header match `Initiative\s*\(d6\)` finds the table on p.30.
- [ ] Rows are **range pairs** (`1-3`, `4-6`) per contract — not six fabricated singleton rows.
- [ ] Extract **stops before** following combat prose that is not part of the table (contract `stop_before`: `Agility \+ d6` etc.).
- [ ] `:LookupTable` / columns / entries land as Tier-5 ingest nodes usable by ADA matched-row retrieval.

### P4 — Evidence wiring does not poison CONTEXT

Once chunks/passages exist:

- [ ] `links_to_seed_labels` on `violence-combat` (`MeleeAttack`, `RangedAttack`, `DefenseRoll`, …) attach evidence to those seeds — **not** fan-out `DOCUMENTED_BY` / `CONFIRMS_SEED` onto every fiction SeedNode ([briefing-12](./pdf-graph-builder-briefing-12.md)).
- [ ] Broad seeds (`Creature`, `Place`, …) are not given Violence page Chunks as “confirmation.”

### P5 — Strict scaffold (policy reminder)

ADA policy ([DESIGN §6.3](../../DESIGN.md#63-ontology-first-ingest-as-evidence-strict-scaffold)): schema gaps / hard seed conflicts are **build failures**, not dual-truth in the game DB. For 2a, prefer **failing a gate above** over shipping a dirty graph. Report packaging remains [OQ-SEED-04](../../DESIGN.md#154-seed-ontology-governance).

---

## Standing smokes (ADA — only after P1–P4)

Do not expect these green until parsing preconditions pass:

| Id | Question | Needs |
|---|---|---|
| C1 | How does a melee attack work? I have Strength +1 — what's the DR? | Violence section / passages; STR + DR 12 |
| C2 | I shoot a bow — which ability and DR? | Ranged / Presence DR 12 |
| C3 | How do I defend? I rolled 11 on Agility (+0). | Defence / Agility DR 12; fail on 11 |
| C4 | Who goes first in a fight? I rolled 4 on the initiative d6. | `InitiativeTable` matched row (4–6 range) |

Listed in ADA `corpus/games/mork-borg/deltas.json` → `phase_2_slice_2a.standing_smokes` and `probe-snippets.md`.

---

## Suggested pgb work order (WIP-friendly)

1. **Prove P0–P1 offline** — dump matched Violence span text; confirm Crit is excluded. Fix anchors / text-layer issues before full extract.
2. **Prove P3** — Initiative table row dump vs acceptance ranges.
3. **Prove P2** — sample RulePassage texts for melee / defence.
4. **Full `/extract`** with `section_phase` ≥ 2.
5. **Handoff** to ADA `docs/inbox/` with: gate checklist, Cypher counts for `section_id = 'violence-combat'`, InitiativeTable row dump, known WIP gaps.

If a gate cannot be met yet, **say which one** and stop — do not mark slice 2a ingest complete.

---

## Acceptance checklist (handoff)

- [ ] P0 text layer OK for Violence headings  
- [ ] P1 `violence-combat` `passage-section` Chunk exists; body stops before Crit  
- [ ] P2 RulePassages usable for melee / ranged / defence without chapter bleed  
- [ ] P3 `InitiativeTable` rows = 1–3 / 4–6 (or documented equivalent)  
- [ ] P4 no fiction-seed evidence fan-out from Violence page  
- [ ] Handoff lists any remaining WIP parser limits  

**ADA already prepared:** OQ-COV-02 Decided; combat retrieval hints + DM framing; smokes C1–C4. No further ADA combat work until this briefing’s parse gates are green (or blocked with cause).
