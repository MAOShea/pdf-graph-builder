# AI-DM-Assistant Handoff 7: Briefing 11 — CREATURES bounty-trail cut

**From:** pdf-graph-builder  
**Date:** 2026-08-04  
**Context:** [Briefing 11](./pdf-graph-builder-briefing-11.md) — finish entity-passage end boundaries after handoff-6.

**Verdict:** **PASS** — Goblin passage keeps curse/body; excludes Head/Captured/Dead tallies and neighbor creatures.

---

## Root cause

End cut was only “next creature heading.” On Bare Bones pages, silver/bounty lines (`Head 7s`, `Captured 150s`, `Dead 20s`, …) sit **between** creature blocks and were left inside the prior `RulePassage`.

---

## Fix (contract-owned boundaries)

**Contract:** `passage-sections.json` **v0.4.0** → top-level `entity_passage.end_detection.stop_before` (line regexes). Synced to ADA `corpus/games/mork-borg/`.

**Code:** `backend/src/entity_passage_materialization.py` loads and compiles those patterns; optional per-row `text_end_hint` on `creatures_index`.

End detection (first match wins after start):

1. Next creature heading on the page.
2. First whole-line match from contract `stop_before` (exclusive).
3. Optional `text_end_hint` on that index row (exclusive).

**Design:** passage boundaries live in JSON (like RULES `sections[]` anchors and table `stop_before`), not as hardcoded layout vocabulary in Python. Operator PDF pass can amend patterns without code changes.

Re-materialize with `--entity-passages-only` after contract edits.

---

## Before / after (Goblin preview)

**Before (handoff-6):** body + curse + `Head 7s` / `Captured 150s` / `Dead 20s`  
**After:** ends at curse close (`…dark of Sarkash will hide you.`); no Head/Captured/Dead; still has `Ropy skin` + curse.

`backend\verify_briefing11.py` → **PASS**.

---

## ADA smoke

Re-ask “What is a Goblin in Mörk Borg?” — entity-scoped CONTEXT should not include bounty tallies.

No ADA retrieval change required (still prefer `MAPS_TO_PASSAGE`).

---

## DESIGN §4.5

CREATURES fiction-gate step 3 (passage/chunk boundary quality) is closable on the pgb side for this bestiary set once ADA smoke is green.
