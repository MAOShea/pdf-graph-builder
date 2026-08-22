"""Place-relation contract load and operator preview (no Neo4j)."""

from src.place_relation_materialization import (
    load_place_relations,
    place_relation_operator_preview,
    place_relations_for_section,
)


def test_galgenbeck_contract_titles_match_index():
    load_place_relations.cache_clear()
    contract = load_place_relations("mork-borg")
    part = contract["part_of"]
    assert part[0]["child_title"] == "Galgenbeck"
    assert part[0]["parent_title"] == "Tveland"
    occ = contract["occurs_in_place"]
    assert occ[0]["faction_title"] == "Two-Headed Basilisks, the"
    assert occ[0]["place_title"] == "Galgenbeck"


def test_place_relations_for_galgenbeck_section():
    load_place_relations.cache_clear()
    grouped = place_relations_for_section("mork-borg", "galgenbeck")
    assert len(grouped["part_of"]) == 1
    assert len(grouped["occurs_in_place"]) == 1
    empty = place_relations_for_section("mork-borg", "equipment")
    assert empty["part_of"] == []
    assert empty["occurs_in_place"] == []


def test_preview_needles_hit_p12_wording():
    load_place_relations.cache_clear()
    span = (
        "Galgenbeck in the land of Tveland is the greatest city that ever was. "
        "Deep beneath the Cathedral of the\nTwo-Headed Basilisks"
    )
    grouped = place_relations_for_section("mork-borg", "galgenbeck")
    part = place_relation_operator_preview(
        grouped["part_of"][0], span, kind="part_of"
    )
    occ = place_relation_operator_preview(
        grouped["occurs_in_place"][0], span, kind="occurs_in_place"
    )
    assert part["label"] == "Galgenbeck PART_OF Tveland"
    assert all(ok for _, ok in part["evidence"])
    assert occ["label"] == "Two-Headed Basilisks, the OCCURS_IN Galgenbeck"
    assert all(ok for _, ok in occ["evidence"])


def test_sarkash_contract_titles_and_section_grouping():
    load_place_relations.cache_clear()
    contract = load_place_relations("mork-borg")
    sarkash_rows = [
        row for row in contract["part_of"] if row.get("section_id") == "sarkash"
    ]
    assert len(sarkash_rows) == 2
    assert sarkash_rows[0]["child_title"] == "Graven-Tosk"
    assert sarkash_rows[0]["parent_title"] == "Sarkash"
    assert sarkash_rows[1]["child_title"] == "Shadow King's Palace, the"
    assert sarkash_rows[1]["parent_title"] == "Graven-Tosk"
    grouped = place_relations_for_section("mork-borg", "sarkash")
    assert len(grouped["part_of"]) == 2
    assert grouped["occurs_in_place"] == []


def test_preview_needles_hit_sarkash_wording():
    load_place_relations.cache_clear()
    span = (
        "Far in the depths of Sarkash, always where one least expects to find it, "
        "in a halo of dying trees, is Graven-Tosk. A truly ancient cemetery "
        "Rising over Graven-Tosk like rage rising over pain is the"
    )
    grouped = place_relations_for_section("mork-borg", "sarkash")
    previews = [
        place_relation_operator_preview(row, span, kind="part_of")
        for row in grouped["part_of"]
    ]
    assert previews[0]["label"] == "Graven-Tosk PART_OF Sarkash"
    assert previews[1]["label"] == "Shadow King's Palace, the PART_OF Graven-Tosk"
    assert all(ok for _, ok in previews[0]["evidence"])
    assert all(ok for _, ok in previews[1]["evidence"])


def test_palace_section_has_no_local_place_relations():
    """PART_OF Graven-Tosk is authored on Sarkash bridge span, not palace section."""
    load_place_relations.cache_clear()
    grouped = place_relations_for_section("mork-borg", "palace-of-the-shadow-king")
    assert grouped["part_of"] == []
    assert grouped["occurs_in_place"] == []


def test_grift_contract_and_preview():
    load_place_relations.cache_clear()
    grouped = place_relations_for_section("mork-borg", "grift")
    assert len(grouped["part_of"]) == 1
    assert grouped["occurs_in_place"] == []
    assert grouped["part_of"][0]["child_title"] == "Grift"
    assert grouped["part_of"][0]["parent_title"] == "Endless Sea, the"
    span = (
        "From ages past, Grift grew upon an eastern peninsula of the "
        "Endless Sea. Cut from the world by the bottomless Mur"
    )
    preview = place_relation_operator_preview(
        grouped["part_of"][0], span, kind="part_of"
    )
    assert preview["label"] == "Grift PART_OF Endless Sea, the"
    assert all(ok for _, ok in preview["evidence"])


def test_kergus_section_has_no_local_place_relations():
    """Alliáns unindexed; Anthelia is SupportingCharacter — no PART_OF / OCCURS_IN."""
    load_place_relations.cache_clear()
    grouped = place_relations_for_section("mork-borg", "kergus")
    assert grouped["part_of"] == []
    assert grouped["occurs_in_place"] == []
