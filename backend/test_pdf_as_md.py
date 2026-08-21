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


def test_render_spine_preview_md_shows_then_and_evidence():
    from pdf_as_md import _render_spine_preview_md

    md = "\n".join(
        _render_spine_preview_md(
            {
                "if_id": "if:omen-optional-rule",
                "procedures": ["Omen"],
                "evidence": [("Use Omens to", True), ("begins with d2", False)],
                "then": ["Use an Omen to deal maximum damage with an attack."],
                "else": [],
            }
        )
    )
    assert "spine `if:omen-optional-rule` FOR Omen · contract (not PDF-parsed)" in md
    assert "`Use Omens to` yes" in md
    assert "`begins with d2` MISSING" in md
    assert "maximum damage" in md


def test_replace_pdf_bullet_run_tags_like_a_table():
    from pdf_as_md import _replace_pdf_bullet_runs

    text = (
        "Use Omens to:\n"
        "\u2020\t\n"
        "\x07deal maximum damage with an attack\n"
        "\u2020\t\n"
        "\x07reroll a dice roll (yours or someone else\u2019s)\n"
        "\u2020\t\n"
        "\x07lower damage dealt to you by d6\n"
        "\u2020\t\n"
        "\x07neutralize a Crit or Fumble\n"
        "\u2020\t\n"
        "\x07lower one test\u2019s DR by -4\n"
    )
    warnings: list[str] = []
    out = _replace_pdf_bullet_runs(
        text,
        game="mork-borg",
        section_id="optional-rules-omens",
        warnings=warnings,
    )
    assert "\u2020" not in out
    assert "\x07" not in out
    assert "> spine `if:omen-optional-rule` FOR Omen · 5/5 list items" in out
    assert "- Use an Omen to deal maximum damage with an attack." in out
    assert warnings == []
    leftover = _replace_pdf_bullet_runs(
        text,
        game="mork-borg",
        section_id="no-such-section",
        warnings=[],
    )
    assert "\u2020" in leftover
