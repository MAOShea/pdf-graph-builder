# Structured JSON Ingest Schema

Hand-authored JSON replaces PDF extraction for rulebook content where layout matters (side-by-side tables, lookup tables, section hierarchy).

**Pipeline behaviour:** each leaf block → one atomic `Chunk` (no `TokenTextSplitter`, no 19-chunk cap).

---

## File envelope

Every file is a JSON object with optional metadata and a `blocks` array:

```json
{
  "source": "mork-borg",
  "section_id": "character-names",
  "title": "Character Names",
  "blocks": [ ... ]
}
```

| Field | Required | Purpose |
|---|---|---|
| `source` | No | Game or corpus identifier |
| `section_id` | No | Stable ID for queries; defaults to filename stem |
| `title` | No | Human title for the file |
| `blocks` | Yes* | Ordered list of content blocks |

\* Shorthand roots without `blocks` are accepted — see below.

---

## Block types (simple → complex)

### Level 0 — plain text string (whole file)

```json
"Man? Woman? Lost souls all."
```

### Level 0b — `{ "text": "..." }`

```json
{ "text": "Roll d20 + Agility. Meet or beat the DR." }
```

### Level 1 — titled text

```json
{
  "type": "text",
  "title": "Ability Scores",
  "text": "Characters have four abilities: Agility, Presence, Strength, Toughness."
}
```

### Level 2 — nested sections (1..n deep)

```json
{
  "type": "section",
  "title": "Combat",
  "blocks": [
    {
      "type": "section",
      "title": "Melee",
      "blocks": [
        { "type": "text", "text": "..." }
      ]
    }
  ]
}
```

Section wrappers do not become chunks themselves — only their leaf children do. Children inherit a `heading_path` breadcrumb (`Combat > Melee`).

### Level 3 — simple table

```json
{
  "type": "table",
  "title": "Occult Treasures",
  "columns": ["d10", "Treasure"],
  "rows": [
    [1, "Ash-grey ring a finger-width wide..."],
    [2, "Keening flute animates a fetus-sized meat golem..."]
  ]
}
```

Tables are rendered as markdown for the LLM and stored as `table_json` on the `Chunk` node for direct lookup.

**Out of scope (for now):** nested tables, rowspan/colspan, multi-table page layouts.

---

## Shorthand file roots

| Root shape | Interpreted as |
|---|---|
| `"string"` | One text block |
| `{ "text": "..." }` | One titled text block |
| `{ "title", "columns", "rows" }` | One table block |
| `{ "blocks": [...] }` | Full envelope |

---

## Chunk node properties (Neo4j)

Structured ingest sets these on `:Chunk`:

| Property | Example |
|---|---|
| `source_format` | `structured-json` |
| `block_type` | `text` or `table` |
| `block_title` | `Occult Treasures` |
| `section_id` | `occult-treasures` |
| `file_title` | envelope `title` |
| `heading_path` | `["Combat", "Melee"]` |
| `block_index` | `0` |
| `table_json` | JSON string (tables only) |

---

## Query examples

```cypher
-- All structured table chunks
MATCH (c:Chunk)
WHERE c.source_format = 'structured-json' AND c.block_type = 'table'
RETURN c.section_id, c.block_title, c.table_json

-- Evidence for a section
MATCH (c:Chunk {section_id: 'character-names'})
RETURN c.text
```

---

## Authoring workflow

1. Place structured-json block files under `games/mork-borg/hand-authored-overrides/` when they override PDF extraction.
2. Run `.\ingest-morkborg-json.ps1` from the workspace root.
3. Review in Bloom with the Scaffold Diff perspective.

Recommended order: lookup tables first (`name-table`, `occult-treasures`, `traps-d12`), then mechanics prose.

---

## PDF vs structured JSON

| | PDF | Structured JSON |
|---|---|---|
| Side-by-side tables | Collapsed | Separate blocks |
| Chunk cap (19) | Yes | No |
| Evidence granularity | Coarse | One block = one rule/table |
| Authoring effort | Zero | Manual / scripted from SRD |
