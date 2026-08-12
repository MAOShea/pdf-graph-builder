"""Unit tests for altitude-D spine contract loading (Briefings 17–18)."""

from src.spine_materialization import load_operational_spines


def test_load_d1_and_d2_spines():
    load_operational_spines.cache_clear()
    contract = load_operational_spines("mork-borg")
    spines = contract.get("spines") or []
    by_id = {s["id"]: s for s in spines}

    assert len(spines) == 7
    assert {
        "if:melee-hit-default",
        "if:ranged-hit-default",
        "if:defence-default",
        "if:crit-attack",
        "if:fumble-defence",
        "if:rest-catch-breath",
        "if:infection-blocks-rest",
    } <= set(by_id)

    for sid in (
        "if:melee-hit-default",
        "if:ranged-hit-default",
        "if:defence-default",
    ):
        s = by_id[sid]
        atom = s.get("atom") or {}
        assert atom.get("kind") == "compare_dr"
        assert int(atom.get("threshold")) == 12
        assert s["combinator"] == "LEAF"
        assert s["evidence"]["section_id"] == "violence-combat"

    crit = by_id["if:crit-attack"]
    assert set(crit["for_procedures"]) == {"MeleeAttack", "RangedAttack"}
    assert crit["atom"]["kind"] == "compare_face"
    assert int(crit["atom"]["threshold"]) == 20
    assert len(crit["then"]) == 2
    assert "else" not in crit
    assert crit["evidence"]["section_id"] == "crit-fumble-rest"

    fumble = by_id["if:fumble-defence"]
    assert fumble["for_procedure"] == "DefenseRoll"
    assert int(fumble["atom"]["threshold"]) == 1

    rest = by_id["if:rest-catch-breath"]
    assert rest["for_procedure"] == "Downtime"
    assert rest["atom"]["kind"] == "circumstance"

    infection = by_id["if:infection-blocks-rest"]
    assert infection["combinator"] == "AND"
    assert len(infection["atoms"]) == 2
    assert all(a["kind"] == "circumstance" for a in infection["atoms"])
