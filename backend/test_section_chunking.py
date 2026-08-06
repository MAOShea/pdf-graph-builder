from unittest.mock import patch

from langchain_core.documents import Document

from src.section_chunking import (
    _load_page_texts,
    apply_text_filters,
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


def test_resolve_page_range_section():
    page_texts = {
        5: "Corpse leftovers",
        6: "Colophon\nPelle Nilsson",
        7: "Music that helped\nBand names",
        8: "Should not appear",
    }
    stream, spans = build_page_indexed_stream(
        {p: normalize_stream_text(t) for p, t in page_texts.items()}
    )
    section = {
        "id": "front-matter-colophon-credits",
        "start_anchor": {
            "type": "page_range",
            "start_page": 6,
            "end_page": 7,
        },
    }
    span = resolve_section_span(
        stream, section, anchor_matching={}, page_spans=spans
    )
    assert span is not None
    start, end = span
    text = stream[start:end]
    assert "Colophon" in text
    assert "Music that helped" in text
    assert "Should not appear" not in text
    assert "Corpse leftovers" not in text


def test_load_page_texts_prefers_pdf_over_langchain_pages():
    pages = [Document(page_content="langchain text", metadata={"page_number": 1})]
    with patch(
        "src.section_chunking.load_pdf_text_by_page",
        return_value={27: "Abilities"},
    ) as load_pdf:
        result = _load_page_texts(
            "mork-borg.pdf",
            pages=pages,
            pdf_path="/tmp/x.pdf",
            text_filters={},
            normalize_whitespace=True,
        )
    load_pdf.assert_called_once()
    assert result == {27: "Abilities"}


def test_apply_text_filters_strips_bare_bones_footer():
    filters = {
        "drop_line_patterns": [
            r"^M[ÖO]RK\s+BORG\s+BARE\s+BONES\s+EDITION\s*$"
        ],
        "strip_inline_patterns": [
            r"\s*M[ÖO]RK\s+BORG\s+BARE\s+BONES\s+EDITION(?:\s+\d+)?\s*"
        ],
        "drop_edge_page_number": True,
    }
    raw = (
        "27\n"
        "Abilities\n"
        "AGILITY defend stuff\n"
        "MÖRK BORG BARE BONES EDITION\n"
        "1\n"
        "mid-page table key stays\n"
        "27\n"
    )
    out = apply_text_filters(raw, filters, page_number=27)
    assert "MÖRK BORG" not in out
    assert "Abilities" in out
    assert out.splitlines()[0] != "27"
    assert out.splitlines()[-1] != "27"
    assert "1" in out  # mid-page index kept
