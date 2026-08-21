"""pdf-as-md render flags — focused ``--section`` vs full-book dump."""

from __future__ import annotations

import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1] / "tools" / "pdf-as-md"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from pdf_as_md import render_options  # noqa: E402


def test_bare_run_is_full_document_with_entities():
    mode, clip, skip_entities = render_options(
        section_ids=[],
        pages_only=False,
        sections_only=False,
        no_entities=False,
    )
    assert mode == "document"
    assert clip is False
    assert skip_entities is False


def test_section_clips_and_skips_creatures_appendix():
    mode, clip, skip_entities = render_options(
        section_ids=["equipment"],
        pages_only=False,
        sections_only=False,
        no_entities=False,
    )
    assert mode == "document"
    assert clip is True
    assert skip_entities is True


def test_sections_only_has_no_unsectioned_gaps():
    mode, clip, skip_entities = render_options(
        section_ids=["equipment"],
        pages_only=False,
        sections_only=True,
        no_entities=False,
    )
    assert mode == "sections-only"
    assert clip is False
    assert skip_entities is True


def test_pages_only_skips_entities():
    mode, clip, skip_entities = render_options(
        section_ids=[],
        pages_only=True,
        sections_only=False,
        no_entities=False,
    )
    assert mode == "pages-only"
    assert clip is False
    assert skip_entities is True
