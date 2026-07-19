from src.section_chunking import (
    build_page_indexed_stream,
    normalize_stream_text,
    resolve_section_span,
    split_passages,
)
from src.ingest_manifest import load_passage_sections


SAMPLE_STREAM = """
26
Some intro page

27
Abilities
AGILITY defend stuff
PRESENCE perceive stuff

28
Tests
Tests are made against a Difficulty Rating.
roll d20 plus ability against the DR.

Carrying Capacity
You can carry Strength plus eight items.

29
Hit Points
Begin with Toughness

30
Violence
Initiative d6
"""


def test_resolve_phase1_sections():
    contract = load_passage_sections("mork-borg")
    anchor_matching = contract.get("anchor_matching") or {}
    stream = normalize_stream_text(SAMPLE_STREAM.strip())
    sections = {s["id"]: s for s in contract["sections"] if s.get("phase") == 1}

    abilities = resolve_section_span(
        stream, sections["abilities"], anchor_matching=anchor_matching
    )
    assert abilities is not None
    a_start, a_end = abilities
    abilities_text = stream[a_start:a_end]
    assert "AGILITY" in abilities_text
    assert "Tests are made" not in abilities_text

    tests = resolve_section_span(
        stream, sections["tests-and-dr"], anchor_matching=anchor_matching
    )
    assert tests is not None
    t_start, t_end = tests
    tests_text = stream[t_start:t_end]
    assert "Difficulty Rating" in tests_text
    assert "Carrying Capacity" not in tests_text
    assert "Violence" not in tests_text


def test_split_paragraphs():
    text = "Line one.\n\nLine two.\n\nLine three."
    assert len(split_passages(text, "paragraph")) == 3
    assert split_passages(text, "section") == [text]


def test_build_page_indexed_stream():
    stream, spans = build_page_indexed_stream({1: "aaa", 2: "bbb"})
    assert "aaa" in stream and "bbb" in stream
    assert len(spans) == 2
    assert spans[0]["page_number"] == 1
