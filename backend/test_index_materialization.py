#!/usr/bin/env python3
"""Unit tests for rulebook index materialization helpers (Briefings 7+8)."""

from src.index_materialization import (
    _iter_index_rows,
    index_titles_for_section,
    maps_to_seed_labels,
    normalize_index_title,
    slug_title,
)


def test_slug_title():
    assert slug_title("Tests") == "tests"
    assert slug_title("Calendar of Nechrubel, the") == "calendar-of-nechrubel-the"
    assert slug_title("Hit Points") == "hit-points"
    assert slug_title("Wästland") == "wastland"


def test_normalize_index_title_cross_column():
    assert normalize_index_title("Calendar of Nechrubel") == normalize_index_title(
        "Calendar of Nechrubel, the"
    )
    assert normalize_index_title("Basilisks, the") == "basilisks"
    assert normalize_index_title("The Endless Sea, the") == "endless sea"


def test_iter_index_rows_counts():
    index_source = {
        "world_index": [{"page": 12, "title": "Galgenbeck", "entry_kind": "place"}],
        "creatures_index": [{"page": 58, "title": "Goblin", "entry_kind": "creature"}],
        "rules_index": [{"page": 28, "title": "Tests", "entry_kind": "rule_topic"}],
    }
    column_map = {
        "THE_WORLD": "world_index",
        "CREATURES": "creatures_index",
        "RULES": "rules_index",
    }
    rows = _iter_index_rows(index_source, column_map)
    assert len(rows) == 3
    assert {r["column"] for r in rows} == {"THE_WORLD", "CREATURES", "RULES"}


def test_index_titles_for_section_compound_and_singular():
    assert index_titles_for_section({"index_title": "Crit"}) == ["Crit"]
    assert index_titles_for_section(
        {
            "index_title": "Crit",
            "index_titles": ["Crit", "Fumble", "Resting", "Infection", "Crit"],
        }
    ) == ["Crit", "Fumble", "Resting", "Infection"]
    assert index_titles_for_section({"index_titles": ["Attack", "Defence"]}) == [
        "Attack",
        "Defence",
    ]
    assert index_titles_for_section({}) == []


def test_maps_to_seed_labels_dedupes_and_skips_empty():
    assert maps_to_seed_labels({}) == []
    assert maps_to_seed_labels({"maps_to_seed": ["Power", "Power", ""]}) == ["Power"]


def test_iter_index_rows_carries_maps_to_seed():
    index_source = {
        "rules_index": [
            {
                "page": 34,
                "title": "Scrolls",
                "entry_kind": "rule_topic",
                "maps_to_seed": ["Power"],
            }
        ],
    }
    rows = _iter_index_rows(index_source, {"RULES": "rules_index"})
    assert rows[0]["maps_to_seed"] == ["Power"]
