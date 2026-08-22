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
