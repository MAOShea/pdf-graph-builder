# AI-DM-Assistant Handoff 10: Correct ops model — full `/extract`, not standalone materialize

**From:** pdf-graph-builder  
**Date:** 2026-08-07  
**Context:** Briefing 13 / WORLD section gap; ADA reply that Tier 5 can be rematerialized without full ingest.

**Please update** ADA `DESIGN.md`, `docs/README.md`, outbox briefing wording (esp. [briefing-13](./pdf-graph-builder-briefing-13.md) if still present), and any agent guidance that equates `materialize-*` CLIs with normal ingest.

---

## What was right

| Claim | Keep |
|---|---|
| ADA **reset + bootstrap** is for Tier 0–4 seed/scaffold changes | Yes |
| `passage-sections.json` / section Chunks are **Tier 5** — no ADA bootstrap required for WORLD rematerialize | Yes |
| Trap / Misery `USES` already in Neo4j ⇒ those seed changes are already loaded | Yes |

---

## What to correct

**Do not** tell operators (or pgb agents) that the normal way to land WORLD `passage-section` Chunks is a standalone section materialize pass.

In pdf-graph-builder:

| Path | Role |
|---|---|
| `.\ingest-morkborg.ps1` → `POST /extract` (`scaffold-diff`) | **Operator path** — tables, section chunking, rulebook catalog, entity passages, LLM scaffold-diff |
| `.\materialize-passage-sections.ps1` (and other `materialize-*`) | **Dev / recovery only** — same helpers, but **bypasses** `/extract`. Not the product workflow |

pgb roadmap ([docs/roadmap.md](./roadmap.md)): terminal ingest and web UI must share the **same** `/extract` path; chaining `materialize-*` as required steps is explicitly **don't**.

So for Briefing 13 (WORLD sections missing):

1. **No** ADA reset/bootstrap (unless wiping DB or missing Tier 0–4 seeds).
2. **Yes** pgb **full ingest** via `/extract`, with **`section_phase` high enough** to include THE WORLD `sections[]`.
3. Default extract still uses **`section_phase=1`** (RULES phase-1 only — explains why the DB has 4 section Chunks and zero WORLD). Raising phase on that ingest is the fix; teaching ADA to prefer page Chunks is not.

Standalone materialize can create section Chunks on an existing Document for debugging, but it does **not** replace ingest (no supersede/LLM/evidence pass in that shortcut).

---

## Suggested ADA doc edits

1. **Briefing 13 / similar:** Prefer “full `/extract` with raised `section_phase`” over “full extract **or** section materialize pass” as the required outcome path. Mentions of materialize CLIs → label **recovery only**.
2. **DESIGN / README ops:** When Tier 5 contracts change (`passage-sections.json`, manifest tables), operator action on pgb is **re-ingest** (`ingest-morkborg.ps1`), not ADA bootstrap and not “run materialize scripts.”
3. Keep the Tier 0–4 vs Tier 5 distinction — only fix the **how** Tier 5 is applied in Neo4j.

---

## pgb follow-up (for awareness; not ADA work)

- Expose / raise `section_phase` on full ingest so WORLD sections are not stuck behind phase 1 (roadmap item).
- After that ingest: acceptance Cypher from briefing-13 (`galgenbeck` etc. as `source_format: passage-section`).
