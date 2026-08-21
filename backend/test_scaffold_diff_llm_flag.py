"""Scaffold-diff Ollama Stage 2 is opt-in (default off)."""

from src.entities.source_extract_params import parse_form_flag, skip_extract_llm


def test_parse_form_flag_default_false():
    assert parse_form_flag(None) is False
    assert parse_form_flag("") is False
    assert parse_form_flag("false") is False
    assert parse_form_flag("true") is True
    assert parse_form_flag("1") is True
    assert parse_form_flag(True) is True


def test_skip_extract_llm_scaffold_diff_default_off():
    assert skip_extract_llm("scaffold-diff", False) is True
    assert skip_extract_llm("scaffold-diff", True) is False


def test_bottom_up_always_calls_llm():
    assert skip_extract_llm(None, False) is False
    assert skip_extract_llm(None, True) is False
