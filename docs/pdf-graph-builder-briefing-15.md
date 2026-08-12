# Briefing 15: Parse / chunk preconditions for combat slice 2b (Crit / fumble / rest)

**For pdf-graph-builder agents.** ADA has decided the full coverage **phase-2 slice ladder** (`2a`–`2g`) from the Bare Bones PDF + contracts ([DESIGN §9.2.1](../../DESIGN.md#921-mörk-borg-mechanism-coverage-roadmap), `corpus/games/mork-borg/deltas.json` → `phase_2_slices`). Slice **2a (Violence)** parse gates were [briefing-14](./pdf-graph-builder-briefing-14.md) / [handoff-11](../inbox/ai-dm-assistant-handoff-11.md). **Next product slice is 2b.**

Before treating 2b ingest as “done,” **PDF → focused evidence** for `crit-fumble-rest` must meet the gates below.

**Do not** expand into reaction/morale, powers, or creation in this briefing. **Do not** paper over bleed in ADA prompts.

---

## Slice 2b target

| Contract | Id / name | Role |
|---|---|---|
| `passage-sections.json` (**pgb SoT**) | `crit-fumble-rest` (phase **2**) | Declared section: Crit (natural 20) → stop before `Reaction (2D6)` |
| `ingest-manifest.json` | *(none required for 2b)* | No new lookup table for this slice; armor tier rules live in section prose (ArmorTable is slice **2f**) |
| Seeds | *(none new required)* | Section `links_to_seed_labels` is empty today — **do not invent** Crit/Fumble/Rest SeedNodes in pgb. Evidence attaches via section Chunk / RulePassage; ADA may add seeds later |

**PDF (Bare Bones p.31) must surface in focused form:**

- Crit (natural 20): attack → double damage + armor/protection −1 tier; defence → PC free attack  
- Fumble (natural 1): attack → weapon breaks/lost; defence → double damage + armor −1 tier; armor below 1st tier ruined  
- How long is a round?  
- Rest: catch breath d4 HP; night d6 HP; no food/drink / infection rules  

**Out of slice (do not require for 2b):** `reaction-morale` (2c), `getting-better-or-worse` (2d), `powers-and-scrolls` (2e), character creation / equipment (2f–2g), Optional Rules / Omens (phase 3).

**Ops path:** full `POST /extract` via `.\ingest-morkborg.ps1` with **`section_phase` ≥ 2** (same product path as briefing-13/14). Prefer proving the section span offline before claiming 2b complete.

**Contract SoT:** edit `passage-sections.json` / `ingest-manifest.json` in **pdf-graph-builder**. ADA promotes mirrors only (`sync-passage-sections-from-pgb.ps1`, `sync-ingest-contracts-from-pgb.ps1`). No ADA → pgb push.

---

## Why this slice is next

Book order after Violence (p.30 → p.31). ADA standing smokes for 2b are already listed; they need **bucket-1-clean CONTEXT** (section / passages that stop before Reaction), not LLM invention of crit/rest rules.

---

## Preconditions the parser / section materializer must fulfill

### P0 — Text layer usable (p.31)

- [ ] PDF text layer for Bare Bones p.31 exposes headings `Crit (natural 20)`, `Fumble (natural 1)`, `How long is a round?`, `Rest` (or equivalent lines the matcher uses).
- [ ] No empty/garbage gap that skips the Crit heading or merges Crit into the previous Violence page dump without a resolvable start anchor.

### P1 — Section anchors resolve (`crit-fumble-rest`)

Contract:

```text
start: ^\s*Crit\s*\(natural 20\)\s*$
end:   ^\s*Reaction\s*\(2D6\)\s*$
```

- [ ] **Start hits** the Crit heading (unique win or documented).
- [ ] **End hits** Reaction (2D6); section body **excludes** Reaction / Morale prose (p.32).
- [ ] Materialized `Chunk` has `source_format: "passage-section"`, `section_id: "crit-fumble-rest"`, body = after start through before end.
- [ ] Body is **not** a full dump of p.30–32 (Violence + Crit + Reaction). Violence may appear only if the text layer incorrectly lacks a Crit start — that is a **P0/P1 failure**, not acceptable 2b content.

Shape:

```text
(:Chunk {
  id: "{file}#section:crit-fumble-rest",
  section_id: "crit-fumble-rest",
  section_title: "Crit, fumble, and rest",
  text,  // focused section body
  page_number_start / page_number_end,
  source_format: "passage-section"
})-[:PART_OF]->(:Document)
```

### P2 — Intra-section focus (paragraph / RulePassage)

Smokes need separable facts: crit vs fumble vs rest vs infection.

- [ ] With `passage_granularity: "paragraph"` (contract), `RulePassage` nodes exist so a **rest** ask does not require the entire Crit/Fumble block as the only unit (prefer distinct passages or clear paragraph boundaries inside the section Chunk).
- [ ] A **crit** passage must not include **Reaction (2D6)** or later chapters.
- [ ] No fiction/CREATURES/WORLD neighbor bleed into this RULES section ([briefing-10](./pdf-graph-builder-briefing-10.md)–[12](./pdf-graph-builder-briefing-12.md)).

### P3 — No new table required (explicit non-goal)

- [ ] Do **not** block 2b on inventing `CritTable` / `RestTable` unless the PDF layout forces a real extractable table (it does not — bullets/prose).
- [ ] Armor **tier** language in Crit/Fumble prose must remain in the section text (ADA smokes cite that prose). Do not require `ArmorTable` (p.23) for 2b.

### P4 — Evidence wiring does not poison CONTEXT

- [ ] If any seed evidence edges are written for this section, do **not** fan out `DOCUMENTED_BY` / `CONFIRMS_SEED` onto fiction seeds (`Creature`, `Place`, …) ([briefing-12](./pdf-graph-builder-briefing-12.md)).
- [ ] Prefer catalog / section retrieval path: `IndexEntry` titles Crit / Fumble / Resting / Infection → `MAPS_TO_SECTION` / section Chunk when wired.

### P5 — Strict scaffold

Schema gaps / hard seed conflicts remain **build failures** ([DESIGN §6.3](../../DESIGN.md#63-ontology-first-ingest-as-evidence-strict-scaffold)). Empty `links_to_seed_labels` is OK for 2b — do not invent Tier-0/4 labels in pgb to “fill” the contract.

---

## Standing smokes (ADA — only after P1–P2)

| Id | Question | Needs in CONTEXT |
|---|---|---|
| R1 | I crit on a melee attack (natural 20). What happens to damage and armor? | Crit attack: double damage; armor −1 tier |
| R2 | I fumbled my defence (natural 1). What happens? | Fumble defence: double damage; armor −1 tier |
| R3 | How much HP do I recover if I catch my breath and drink? | Rest: restore d4 HP |
| R4 | My character is infected — do they heal from a full night's sleep? | Infected: no rest benefit; d6 HP lost daily |

Listed in ADA `deltas.json` → `phase_2_slices.2b.standing_smokes` and `probe-snippets.md`.

---

## Suggested pgb work order

1. **Prove P0–P1 offline** — dump matched `crit-fumble-rest` span; confirm Reaction excluded and Violence not re-included as the whole body.
2. **Prove P2** — sample RulePassage / paragraph splits for Crit vs Rest.
3. **Full `/extract`** with `section_phase` ≥ 2 (or re-run section materialization path you use for phase-2 RULES — document which).
4. **Handoff** to ADA `docs/inbox/` with: gate checklist, Cypher for `section_id = 'crit-fumble-rest'`, substring of Chunk text (start/end), known WIP gaps.

If a gate cannot be met, **name it** and stop — do not mark slice 2b ingest complete.

---

## Acceptance checklist (handoff)

- [ ] P0 text layer OK for Crit / Rest headings on p.31  
- [ ] P1 `crit-fumble-rest` `passage-section` Chunk exists; body stops before Reaction  
- [ ] P2 passages usable for crit vs rest without chapter bleed  
- [ ] P3 no bogus table invent for 2b  
- [ ] P4 no fiction-seed evidence fan-out  
- [ ] Handoff lists remaining WIP parser limits  

**ADA already prepared:** phase-2 ladder 2a–2g; 2b smokes R1–R4; retrieval prefers declared sections. After handoff, ADA promotes contracts and runs smokes — no ADA 2b “done” until these gates are green (or blocked with cause).

**Optional non-blocker for this briefing:** residual `Misery→abilities` evidence edges (still suppressed on matched-row asks) — out of scope for 2b.
