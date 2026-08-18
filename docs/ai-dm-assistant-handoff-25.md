# AI-DM-Assistant Handoff 25: Retarget morale spines `FOR` → `MoraleCheck`

**From:** pdf-graph-builder  
**Date:** 2026-08-17  
**Context:** [Briefing 25](./pdf-graph-builder-briefing-25.md) / leftover from [handoff-24](./ai-dm-assistant-handoff-24.md).

**Verdict:** **P0–P5 green on product-path `/extract` only** (no `materialize-*` recovery as acceptance). Three `if:morale-*` spines `FOR` **`MoraleCheck`**; Compare `COMPARED_TO` sheet **`Morale`**; Goblin `HAS_MORALE` **7**; D1 melee intact. **Ball is with ADA** — run M1 / M2 / S4.

---

## Ops (honest)

| Step | Done? |
|---|---|
| ADA reset + bootstrap (`MoraleCheck` SeedNode) | **Yes** (operator, before pgb work) |
| pgb `operational-spines.json` **0.4.1** | **Yes** — all three morale spines `for_procedure: MoraleCheck`; `compared_to: Morale` |
| Fresh backend after contract on disk | **Yes** — operator restarted uvicorn; prior Anaconda/venv listeners killed |
| Full ingest | **Yes** — `ingest_pdf.py … --cleanup --section-phase 2` → Document **Completed**; nodes=148 / rels=245 / chunks=148 (~70 min) |
| `materialize-*` / tables CLI as green stamp | **No** — acceptance Cypher run **immediately after extract**, no rematerialize |

Earlier same-day attempt: extract against a long-lived backend that had cached pre-0.4.1 spines; P2 failed; recovery CLIs were used incorrectly and must **not** be treated as briefing-25 green. This handoff replaces that claim.

```powershell
# Backend must already be running (fresh process after spines 0.4.1 on disk)
backend\venv\Scripts\python.exe -u backend\ingest_pdf.py mork-borg.pdf `
  --backend-url http://127.0.0.1:8000 `
  --model ollama_llama3 `
  --ingest-mode scaffold-diff `
  --section-phase 2 `
  --cleanup
```

---

## What pgb shipped

| Item | Detail |
|---|---|
| SoT | `games/mork-borg/operational-spines.json` **v0.4.1** |
| Tests | `backend/test_spine_materialization.py` asserts `MoraleCheck` |
| Unchanged | D4 `HAS_MORALE` → `:Morale`; Reaction+Morale catalog; `ReactionTable` (5) |

---

## Acceptance Cypher (pasted — post-extract only)

### P0 — scaffold

| labels | name |
|---|---|
| SeedNode, Morale | Morale |
| SeedNode, MoraleCheck | MoraleCheck |

### P1 — no `If-[:FOR]->Morale`

**0 rows.**

### P2 — procedure spines

| if_id |
|---|
| `if:morale-demoralized` |
| `if:morale-flee-or-surrender` |
| `if:morale-trigger` |

(all `FOR` `MoraleCheck`)

### P3 — demoralized Compare

| op | left | COMPARED_TO |
|---|---|---|
| **>** | **2d6** | **Morale** |

### P4 — Goblin sheet

| creature | value |
|---|---|
| Goblin | **7** |

### P5 — D1

| FOR |
|---|
| MeleeAttack |

### Kept from 2c (same extract)

| Check | Result |
|---|---|
| Document status | **Completed** |
| Reaction + Morale → `reaction-morale` | **Both** |
| `ReactionTable` entries | **5** |

---

## ADA smokes

```powershell
cd D:\GitHub\AI-DM-Assistant\backend
.\venv\Scripts\python.exe -m smokes.cli_chat --suite 2c --check-context
.\venv\Scripts\python.exe -m smokes.smoke_d4_select_hop
```

| Smoke | Expect |
|---|---|
| **M1** | Reaction 7–8 Indifferent |
| **M2** | `If-[:FOR]->MoraleCheck` in CONTEXT; 9>7 demoralized — not sheet-only |
| **S4** | Goblin `HAS_MORALE` **7** — not procedure spines |

---

## Remaining WIP

- Out of slice: 2d, flee d6 table, Morale `passage_split`.
- Prefer restarting backend whenever `operational-spines.json` changes before `/extract` (`load_operational_spines` is process-cached).

---

## Promote

```powershell
Copy-Item -Force .\docs\ai-dm-assistant-handoff-25.md D:\GitHub\AI-DM-Assistant\docs\inbox\
```
