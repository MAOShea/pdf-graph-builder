# Briefing 24: Coverage slice 2c — Reaction / morale catalog wiring

**For pdf-graph-builder agents.** ADA is starting coverage **2c** (`reaction-morale`, Bare Bones p.32). [DESIGN §9.2.1](../../DESIGN.md#921-mörk-borg-mechanism-coverage-roadmap), `deltas.json` → `phase_2_slices.2c`.

This is **catalog / section wiring**, not a new altitude-D fill. **Do not** invent `Reaction` / `MoraleCheck` SeedNodes. **Do not** invent `ReactionTable` unless P3 below says the PDF is a real extractable table (it is range prose today). **Do not** paper over the missing edge in ADA.

**Do not** expand into 2d (`getting-better-or-worse`), powers, or PC sheets in this briefing.

---

## What ADA already proved (operator DB `morkborg`, 2026-08-16)

| Fact | Status |
|---|---|
| `Chunk` `section_id=reaction-morale` | **Present** — `source_format=passage-section`, p.32–32, 441 chars |
| Body | Focused: Reaction (2D6) ranges + Morale procedure; stops before Getting Better |
| `IndexEntry` **Reaction** | `MAPS_TO_SECTION` → `reaction-morale` |
| `IndexEntry` **Morale** | **`INDEXED_IN` Document only — no `MAPS_TO_SECTION`** |
| Lookup tables | No `ReactionTable` / flee-d6 table (expected) |
| `If` spines | None for reaction/morale (expected — not a D-fill) |

Section body (ADA retrieve; en-dashes may mojibake in some consoles):

```text
When meeting creatures whose reaction is uncertain.
2–3 Kill!
4–6 Angered
7–8 Indifferent
9–10 Almost friendly
11–12 Helpful
Morale
Most enemies will not fight to the last drop of blood.
Roll for morale if
the leader is killed
half the group is eliminated
a single enemy has only 1/3 of its HP left
If you roll greater than the creature’s Morale value with 2d6,
it is demoralized. Roll d6 to see if the enemy (1–3) flees or
(4–6) surrenders.
```

**Reaction ask** already gets this as `Rule passages (declared section from catalog)`.

**Morale ask** cannot take that path. ADA falls back to page-anchored p.32 Chunks (full page + the section Chunk that happens to share `page_number_start=32`). That is **not** the designed R4→R6 walk.

```cypher
MATCH (e:IndexEntry)
WHERE toLower(e.title) IN ['reaction', 'morale']
OPTIONAL MATCH (e)-[r]->(n)
RETURN e.title, e.id, type(r) AS rel, labels(n) AS labels,
       coalesce(n.section_id, n.id) AS other
```

**Expect after this briefing:** Morale has `MAPS_TO_SECTION` → `Chunk {section_id:'reaction-morale'}` (same target as Reaction).

---

## Slice 2c target

| Contract | Id / name | Role |
|---|---|---|
| `passage-sections.json` (**pgb SoT**) | `reaction-morale` (phase **2**) | Declared section: `Reaction (2D6)` → stop before `Getting Better` |
| `ingest-manifest.json` | *(none required for 2c start)* | No lookup table unless P3 fails |
| Seeds | *(none new)* | `links_to_seed_labels` empty — **do not invent** Reaction/MoraleCheck SeedNodes. Sheet label `Morale` (D4 `HAS_MORALE`) stays a **sheet slot**, not this procedure |

**Out of slice:** `getting-better-or-worse` (2d), powers, creation, optional rules, creature-sheet `HAS_MORALE` values, new `If` spines.

**Ops path:** if only catalog links change, a linker / catalog re-link may suffice — **name which**. If `index_titles` on the section contract changes, full `.\ingest-morkborg.ps1` (`section_phase` ≥ 2). Product path remains full `/extract`, not `materialize-*` CLIs.

**Contract SoT:** edit `passage-sections.json` in **pdf-graph-builder**. ADA promotes the mirror (`sync-passage-sections-from-pgb.ps1`). No ADA → pgb push.

---

## Preconditions

### P0 — Text layer (already green on this DB)

- [x] p.32 exposes `Reaction (2D6)` and a `Morale` subhead (or equivalent the matcher used).
- [x] Section Chunk body is not Violence + Crit + Reaction mashed together.

Re-prove after any re-extract.

### P1 — Section anchors (`reaction-morale`)

Contract:

```text
start: ^\s*Reaction\s*\(2D6\)\s*$
end:   ^\s*Getting Better\s*$
```

- [ ] Start / end still unique; body **excludes** Getting Better (p.33) and **excludes** Crit/Violence as the whole body.
- [ ] `source_format: "passage-section"`, `section_id: "reaction-morale"`.

### P2 — Catalog: both index rows reach the section (**the gap**)

`passage-sections.json` today has `index_title: "Reaction"` only. Catalog also has **Morale** p.32 (`RULES`).

- [ ] Add **Morale** to the section’s index titles (same pattern as 2b `index_titles`: Crit / Fumble / Resting / Infection).
- [ ] After ingest / re-link, **both** IndexEntries have `MAPS_TO_SECTION` → `reaction-morale`.

```cypher
MATCH (e:IndexEntry)-[:MAPS_TO_SECTION]->(c:Chunk {section_id: 'reaction-morale'})
RETURN e.title
ORDER BY e.title
// expect: Morale, Reaction
```

Optional (not blocking M1): `passage_split` on `^\s*Morale\s*$` so a reaction ask need not carry the morale half as the only unit (2b used subheading splits). One combined passage is acceptable for 2c start if P1+P2 hold.

### P3 — No new table required (explicit non-goal)

- [ ] Do **not** block 2c on inventing `ReactionTable` or a flee/surrender d6 table. The PDF is range + prose, same class as 2b bullets.
- [ ] Reopen a table contract only if a later ADA `--no-resolved-hit` measure shows the LLM inventing bands **after** CONTEXT is the section only (bucket 3). That is not today’s ticket.

### P4 — Evidence wiring does not poison CONTEXT

- [ ] Do not fan out `CONFIRMS_SEED` / `DOCUMENTED_BY` from this section onto fiction seeds (`Creature`, `Place`, …) ([briefing-12](./pdf-graph-builder-briefing-12.md), [briefing-21](./pdf-graph-builder-briefing-21.md)).
- [ ] ADA will skip seed-evidence **when a declared section is already selected** (generic packaging — same class as spine / table / sheet). That does **not** replace P2.

### P5 — Strict scaffold

Empty `links_to_seed_labels` is OK. Do not invent Tier-0/4 labels in pgb to “fill” 2c.

---

## Standing smokes (ADA)

| Id | Question | Needs in CONTEXT |
|---|---|---|
| M1 | We meet a creature whose reaction is uncertain — I rolled 7 on 2d6. What is their reaction? | Declared `reaction-morale`; band **7–8 Indifferent** (not basilisk lore / powers) |
| M2 | The enemy leader is dead — how does morale work? Their Morale is 7 and I rolled 9 on 2d6. | Same section via **Morale → MAPS_TO_SECTION**; greater-than → demoralized (not a creature `HAS_MORALE` sheet hop) |

M1 can retrieve today. **M2 is blocked on P2.** ADA will not add a page-range or title-CONTAINS recovery.

Listed in ADA `deltas.json` → `phase_2_slices.2c.standing_smokes` and `probe-snippets.md`.

---

## Suggested pgb work order

1. Add Morale to `reaction-morale` `index_titles` (pgb SoT).
2. Re-link or full `/extract` (`section_phase` ≥ 2) so `MAPS_TO_SECTION` lands.
3. Run the Cypher in P2; dump `e.title` + `c.section_id`.
4. Handoff to ADA `docs/inbox/` with: P2 result, whether a full extract was required, remaining WIP.

If P2 cannot be met, **name it** and stop — do not mark 2c ingest complete.

---

## Acceptance checklist (handoff)

- [ ] P1 section Chunk still focused (Reaction → before Getting Better)
- [ ] P2 both Reaction **and** Morale `MAPS_TO_SECTION` → `reaction-morale`
- [ ] P3 no bogus table invent
- [ ] P4 no new fiction-seed fan-out from this section
- [ ] Handoff lists remaining WIP

**ADA will not** treat “page 32 Chunk exists” as P2 green.
