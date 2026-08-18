"""Unit tests for altitude-D spine contract loading (Briefings 17–19)."""

from src.spine_materialization import (
    extract_creature_combat_dr,
    load_operational_spines,
    _opaque_id,
)


def test_load_d1_and_d2_spines():
    load_operational_spines.cache_clear()
    contract = load_operational_spines("mork-borg")
    spines = contract.get("spines") or []
    by_id = {s["id"]: s for s in spines}

    assert contract.get("version") == "0.4.1"
    assert len(spines) == 10
    assert {
        "if:melee-hit-default",
        "if:ranged-hit-default",
        "if:defence-default",
        "if:crit-attack",
        "if:fumble-defence",
        "if:rest-catch-breath",
        "if:infection-blocks-rest",
        "if:morale-trigger",
        "if:morale-demoralized",
        "if:morale-flee-or-surrender",
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

    trigger = by_id["if:morale-trigger"]
    assert trigger["for_procedure"] == "MoraleCheck"
    assert trigger["combinator"] == "OR"
    assert len(trigger["atoms"]) == 3
    assert trigger["evidence"]["section_id"] == "reaction-morale"

    demoralized = by_id["if:morale-demoralized"]
    atom = demoralized["atom"]
    assert demoralized["for_procedure"] == "MoraleCheck"
    assert atom["kind"] == "compare"
    assert atom["op"] == ">"
    assert atom["left"] == "2d6"
    assert atom["compared_to"] == "Morale"
    assert "threshold" not in atom

    flee = by_id["if:morale-flee-or-surrender"]
    assert flee["for_procedure"] == "MoraleCheck"
    assert flee["combinator"] == "AND"
    assert flee["else"]["name"] == "surrenders"

    d3 = contract.get("creature_dr_overrides") or {}
    assert d3.get("enabled") is True
    assert d3.get("circumstance_role") == "fighting"
    assert len(d3.get("extract_rules") or []) >= 3


def test_extract_creature_combat_dr_rules():
    load_operational_spines.cache_clear()
    rules = (load_operational_spines("mork-borg").get("creature_dr_overrides") or {})[
        "extract_rules"
    ]

    goblin = extract_creature_combat_dr(
        "Special: Quick, attacks and defence are DR14.", rules
    )
    assert goblin is not None
    assert goblin[0] == 14
    assert set(goblin[1]) == {"MeleeAttack", "RangedAttack", "DefenseRoll"}

    troll = extract_creature_combat_dr(
        "Special: Easy to hit; attacks are DR10. Cowards despite their size.", rules
    )
    assert troll is not None
    assert troll[0] == 10
    assert set(troll[1]) == {"MeleeAttack", "RangedAttack"}

    berserker = extract_creature_combat_dr(
        "Attacks twice per round but doesn’t have time for defence (DR10 to hit them).",
        rules,
    )
    assert berserker is not None
    assert berserker[0] == 10

    wraith = extract_creature_combat_dr(
        "Special: Swift, elusive and difficult to hit (DR14).", rules
    )
    assert wraith is not None
    assert wraith[0] == 14

    # Ability-test / specialized lines must not yield combat overrides.
    assert (
        extract_creature_combat_dr(
            "Poisoned knife. Test Toughness DR10 or become infected.", rules
        )
        is None
    )
    assert (
        extract_creature_combat_dr(
            "Attacks on them with piercing weapons are DR14.", rules
        )
        is None
    )
    assert (
        extract_creature_combat_dr(
            "Paralyzing touch (Presence DR14 every round to break free).", rules
        )
        is None
    )


def test_opaque_if_id_has_no_creature_name():
    if_id = _opaque_id(
        "if:d3-",
        "MeleeAttack",
        "mork-borg.pdf#entity:creature:goblin",
        "14",
    )
    assert if_id.startswith("if:d3-")
    assert "goblin" not in if_id.lower()
    assert "-vs-" not in if_id


def test_proc_default_if_map():
    from src.spine_materialization import _PROC_DEFAULT_IF

    assert _PROC_DEFAULT_IF["MeleeAttack"] == "if:melee-hit-default"
    assert _PROC_DEFAULT_IF["RangedAttack"] == "if:ranged-hit-default"
    assert _PROC_DEFAULT_IF["DefenseRoll"] == "if:defence-default"
