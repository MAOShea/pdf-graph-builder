# SoT split — no copies

Contracts in this repo are the only copy. Do not copy them into AI-DM-Assistant `corpus/`.

| File | SoT | Read by |
|---|---|---|
| `games/<game>/passage-sections.json` | **this repo** | section / entity materializers |
| `games/<game>/ingest-manifest.json` | **this repo** | ingest / table pipeline |
| `games/<game>/operational-spines.json` | **this repo** | spine materializer |
| `games/<game>/hand-authored-overrides/*` | **this repo** | table materialization |
| ADA `corpus/games/<game>/deltas.json` | **AI-DM-Assistant** | ADA bootstrap (not this repo) |

One Cursor workspace, both roots, one agent. Edit here; ingest here. Seeds change in ADA (reset + bootstrap) before a full re-ingest. Historical briefing/handoff markdown lives in git only.
