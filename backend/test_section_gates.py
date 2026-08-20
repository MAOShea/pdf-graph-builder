"""Unit tests for section ingest-gate helpers (no Neo4j)."""
from src.ingest_manifest import load_passage_sections
from src.section_gates import gated_sections, split_heading_needles, unescape_heading_fragment


def test_split_heading_needles_getting_better():
    needles = split_heading_needles(
        r"^\s*(More HP|Left in the debris you find|Ability changes)\s*$"
    )
    assert needles == [
        "More HP",
        "Left in the debris you find",
        "Ability changes",
    ]


def test_split_heading_needles_crit_fumble():
    needles = split_heading_needles(
        r"^\s*(Fumble\s*\(natural 1\)|How long is a round\?)\s*$"
    )
    assert needles == ["Fumble (natural 1)", "How long is a round?"]


def test_unescape_heading_fragment():
    assert unescape_heading_fragment(r"Fumble\s*\(natural 1\)") == "Fumble (natural 1)"


def test_contract_omits_retired_reaction_morale():
    load_passage_sections.cache_clear()
    contract = load_passage_sections("mork-borg")
    ids = {s["id"] for s in contract["sections"]}
    assert "reaction-morale" not in ids
    assert {"rest", "reaction", "morale", "getting-better-or-worse"} <= ids


def test_gated_rules_phase2_includes_siblings():
    load_passage_sections.cache_clear()
    contract = load_passage_sections("mork-borg")
    gated = gated_sections(contract, phase=2, column="RULES")
    ids = {s["id"] for s in gated}
    assert {"rest", "reaction", "morale", "getting-better-or-worse", "crit-fumble-rest"} <= ids
    assert "what-was-written" not in ids
    assert "optional-rules-omens" not in ids


def test_powers_and_scrolls_map_to_power_seed():
    load_passage_sections.cache_clear()
    contract = load_passage_sections("mork-borg")
    section = next(s for s in contract["sections"] if s["id"] == "powers-and-scrolls")
    assert section["links_to_seed_labels"] == ["Power"]
    by_title = {r["title"]: r for r in contract["index_source"]["rules_index"]}
    assert by_title["Powers"]["maps_to_seed"] == ["Power"]
    assert by_title["Scrolls"]["maps_to_seed"] == ["Power"]
    assert by_title["Create a character"]["maps_to_seed"] == ["CharacterCreation"]
    assert by_title["Weapons"]["uses_tables"] == ["WeaponTable"]
    assert by_title["Armor"]["uses_tables"] == ["ArmorTable"]
    assert by_title["Starting equipment"]["uses_tables"] == [
        "StartingPossessionsTable",
        "StartingEquipmentTable",
        "StartingEquipmentTable2",
    ]
    assert by_title["Equipment"]["uses_tables"] == [
        "EquipmentTable",
        "ServicesTable",
        "WeaponShopTable",
        "BeastsTable",
    ]
    assert by_title["Fanged deserter"]["uses_tables"] == [
        "EarliestMemoriesTable",
        "FangedDeserterEquipmentTable",
    ]
