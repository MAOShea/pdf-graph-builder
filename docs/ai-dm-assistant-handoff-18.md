# AI-DM-Assistant Handoff 18: Stop front-matter seed evidence fan-out

**From:** pdf-graph-builder  
**Date:** 2026-08-14  
**Context:** [Briefing 21](./pdf-graph-builder-briefing-21.md) / [handoff-17](./ai-dm-assistant-handoff-17.md).

**Verdict:** **E21 green** — deleted **250** `CONFIRMS_SEED`/`DOCUMENTED_BY` edges from front-matter section chunks onto scaffold seeds. Linker + contract prevent recreation. Violence evidence and D1–D3 spines intact. **Ball is with ADA** — re-smoke Goblin / `cli_chat --suite d3 --check-context`; CONTEXT must not list colophon / occult under seed evidence.

**No ADA reset. No pgb re-ingest.** Cleanup already applied on the live `morkborg` DB; ADA can re-smoke immediately. The linker/contract changes only matter on a **future** full ingest so the fan-out cannot return.

---

## Ops note (ADA)

| Action | Needed? |
|---|---|
| ADA reset + bootstrap | **No** |
| pgb `.\ingest-morkborg.ps1` / re-extract | **No** (for this fix to take effect) |
| ADA `cli_chat --suite d3 --check-context` | **Yes** — verify CONTEXT |
| Next full pgb ingest (whenever you next dress the DB) | Uses `seed_evidence` guards automatically |

---

## Root cause

Scaffold-diff (`save_scaffold_diff_in_neo4j`) wrote `Chunk-[:CONFIRMS_SEED|DOCUMENTED_BY]->SeedNode` for **every** extracted seed concept onto **every** chunk in the LLM batch — including section chunks for:

- `occult-treasures` (126 edges)
- `front-matter-colophon-credits` (122)
- `character-names` (2)

Those chunks had empty `links_to_seed_labels` but still received book-wide fan-out from LLM extract (DR mentions on occult items, combined batches, etc.).

---

## What pgb shipped

| Item | Detail |
|---|---|
| Cleanup | `backend/repair_briefing21_frontmatter.py` — delete deny-list edges; stamp `Chunk.seed_evidence=false` |
| Contract | `passage-sections.json` **v0.5.10** — `seed_evidence: false` on the three front-matter sections |
| Section merge | `_merge_section_chunk` persists `c.seed_evidence` |
| Linker guard | `common_fn.save_scaffold_diff_in_neo4j` only MERGEs seed evidence when `coalesce(c.seed_evidence, true) <> false` |
| LLM list | `section_chunks_for_llm` omits `seed_evidence: false` sections |

```powershell
# Idempotent cleanup (already run on operator DB)
backend\venv\Scripts\python.exe backend\repair_briefing21_frontmatter.py
```

---

## Acceptance Cypher (pasted post-repair)

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

| bad_edges |
|---|
| **0** |

(Before: 250.)

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

| bad_combat_evidence |
|---|
| **0** |

### E21-P2 — Legitimate Violence evidence still present

```cypher
MATCH (n:SeedNode)<-[:CONFIRMS_SEED|DOCUMENTED_BY]-(p)
WHERE any(lbl IN labels(n) WHERE lbl IN ['MeleeAttack', 'DefenseRoll'])
  AND coalesce(p.section_id, '') = 'violence-combat'
RETURN count(*) AS violence_evidence
```

| violence_evidence |
|---|
| **8** |

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

| spines |
|---|
| **14** |

---

## Gate checklist

| Gate | Status |
|---|---|
| E21-P0 `bad_edges = 0` | ✅ |
| E21-P1 `bad_combat_evidence = 0` | ✅ |
| E21-P2 Violence evidence retained | ✅ |
| E21-P3 spines intact | ✅ |
| Linker/ingest cannot recreate fan-out | ✅ (`seed_evidence` flag + LLM omit) |

---

## ADA next

1. **Do not wait for a pgb re-ingest** — graph is already cleaned.  
2. Re-ask Goblin defence / melee with `--check-context` (and optionally `--no-short-circuit`).  
3. Confirm CONTEXT has **no** `front-matter-colophon-credits` / `occult-treasures` under “Rule passages (via seed evidence)”.  
4. Expect D3 threshold **14** without DR12 Violence prose drowning the pack.

Promote: this handoff → ADA `docs/inbox/`; `passage-sections.json` v0.5.10 via `sync-passage-sections-from-pgb.ps1` when convenient.
