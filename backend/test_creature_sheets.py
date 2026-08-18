"""Unit tests for D4 creature sheet parsing (Briefings 20 / 23)."""

from src.creature_sheet_materialization import parse_creature_sheet


def test_parse_goblin_exemplar():
    text = (
        "Seth, Goblin\n"
        "HP 6 Morale 7 Ropy skin -d2 Knife/shortbow d4\n"
        "Special: Quick, attacks and defence are DR14.\n"
    )
    sheet = parse_creature_sheet(text)
    assert sheet is not None
    assert sheet["hp"] == 6
    assert sheet["morale"] == {"value": 7, "none": False}
    assert sheet["armor"]["name"] == "Ropy skin"
    assert sheet["armor"]["reduce"] == "-d2"
    assert sheet["attacks"] == [{"name": "Knife/shortbow", "damage": "d4"}]


def test_parse_no_armor_and_morale_none():
    text = (
        "Wrat, Wraith\n"
        "HP 15 Morale — No armor\n"
        "Touch d4 + special\n"
        "Special: Swift, elusive and difficult to hit (DR14).\n"
    )
    sheet = parse_creature_sheet(text)
    assert sheet is not None
    assert sheet["hp"] == 15
    assert sheet["morale"]["none"] is True
    assert sheet["armor"]["name"] == "No armor"
    assert sheet["armor"]["reduce"] is None
    assert sheet["attacks"][0]["name"] == "Touch"
    assert sheet["attacks"][0]["damage"] == "d4"


def test_parse_troll_2d6():
    text = (
        "Arbint, Troll\n"
        "HP 32 Morale special Thick hide -d2 Fist 2d6\n"
        "Special: Easy to hit; attacks are DR10.\n"
    )
    sheet = parse_creature_sheet(text)
    assert sheet is not None
    assert sheet["hp"] == 32
    assert sheet["morale"]["none"] is True
    assert sheet["armor"]["reduce"] == "-d2"
    assert sheet["attacks"] == [{"name": "Fist", "damage": "2d6"}]


def test_parse_or_attacks():
    text = (
        "Belze, blood-drenched skeleton\n"
        "HP 7 Morale 8 No armor\n"
        "Shortsword d4 or Knife d4\n"
        "Bony knuckles d2\n"
        "Special: Skulks about.\n"
    )
    sheet = parse_creature_sheet(text)
    assert sheet is not None
    names = {a["name"] for a in sheet["attacks"]}
    assert "Shortsword" in names
    assert "Knife" in names
    assert "Bony knuckles" in names


def test_parse_missing_hp_returns_none():
    assert parse_creature_sheet("Just lore about goblins with no stats.") is None
