"""Unit tests for Briefing 10–11 entity-span slicing (contract-driven stop_before)."""

from src.entity_passage_materialization import (
    compile_stop_before_patterns,
    find_stop_before_start,
    find_title_start,
    load_entity_passage_config,
    slice_entity_spans,
)
from src.section_chunking import normalize_stream_text

PAGE_58 = normalize_stream_text(
    """
Creatures
Seth, Goblin
HP 6 Morale 7 Ropy skin -d2 Knife/shortbow d4
Special: Quick, attacks and defence are DR14.
All goblins carry a curse.
Head 7s
Captured 150s
Dead 20s
Bent, Scum
HP 7 Morale 8 No armor
Poisoned knife d4 + special
There are few fiends more fell than poverty.
Captured 50-120s
"""
)


def _mork_stop_patterns():
    return compile_stop_before_patterns(load_entity_passage_config(game="mork-borg"))


def test_contract_has_stop_before_patterns():
    patterns = _mork_stop_patterns()
    assert len(patterns) >= 2


def test_find_goblin_and_scum_starts():
    g = find_title_start(PAGE_58, "Goblin")
    s = find_title_start(PAGE_58, "Scum")
    assert g is not None and s is not None
    assert g < s


def test_slice_goblin_excludes_scum_and_bounty():
    entries = [
        {"title": "Goblin", "column": "CREATURES", "page": 58, "entry_kind": "creature"},
        {"title": "Scum", "column": "CREATURES", "page": 58, "entry_kind": "creature"},
    ]
    spans = {
        s["title"]: s["text"]
        for s in slice_entity_spans(PAGE_58, entries, stop_patterns=_mork_stop_patterns())
    }
    assert "Goblin" in spans and "Scum" in spans
    assert "Seth, Goblin" in spans["Goblin"] or "Goblin" in spans["Goblin"]
    assert "curse" in spans["Goblin"].lower()
    assert "Ropy skin" in spans["Goblin"]
    assert "Bent" not in spans["Goblin"]
    assert "Poisoned knife" not in spans["Goblin"]
    assert "Head 7s" not in spans["Goblin"]
    assert "Captured 150s" not in spans["Goblin"]
    assert "Dead 20s" not in spans["Goblin"]
    assert "Scum" in spans["Scum"]
    assert "Captured 50-120s" not in spans["Scum"]


def test_stop_before_detects_reversed_silver_label():
    text = "Special: Easy to hit.\nThey grow larger.\n200s Captured\n100s Corpse\n"
    at = find_stop_before_start(text, _mork_stop_patterns())
    assert at is not None
    assert text[at:].startswith("200s Captured")


def test_per_entry_text_end_hint():
    entries = [
        {
            "title": "Goblin",
            "column": "CREATURES",
            "page": 58,
            "entry_kind": "creature",
            "text_end_hint": "All goblins carry a curse.",
        },
        {"title": "Scum", "column": "CREATURES", "page": 58, "entry_kind": "creature"},
    ]
    spans = {
        s["title"]: s["text"]
        for s in slice_entity_spans(PAGE_58, entries, stop_patterns=_mork_stop_patterns())
    }
    assert "curse" not in spans["Goblin"].lower()
    assert "Ropy skin" in spans["Goblin"]


def test_undead_necromancer_flexible_match():
    page = normalize_stream_text(
        "Lich, Undead (weak) necromancer\nHP 15\nArbint, Troll\nHP 32\n"
    )
    start = find_title_start(page, "Undead necromancer")
    assert start is not None
    spans = slice_entity_spans(
        page,
        [
            {
                "title": "Undead necromancer",
                "column": "CREATURES",
                "page": 60,
                "entry_kind": "creature",
            },
            {"title": "Troll", "column": "CREATURES", "page": 60, "entry_kind": "creature"},
        ],
        stop_patterns=_mork_stop_patterns(),
    )
    by_title = {s["title"]: s["text"] for s in spans}
    assert "necromancer" in by_title["Undead necromancer"].lower()
    assert "Troll" not in by_title["Undead necromancer"]
