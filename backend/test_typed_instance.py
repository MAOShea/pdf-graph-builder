"""Unit tests for generic typed-instance helpers + row_typing strategies."""

from __future__ import annotations

import unittest

from src.typed_instance import (
    entity_id,
    normalize_name_key,
    resolve_field,
    skip_row,
    slug_title,
)


class TestTypedInstanceIds(unittest.TestCase):
    def test_slug_and_normalize_merge_diacritics(self):
        self.assertEqual(normalize_name_key("Zweihänder"), normalize_name_key("Zweihander"))
        self.assertEqual(
            entity_id("mork-borg.pdf", "weapon", "Zweihänder"),
            entity_id("mork-borg.pdf", "weapon", "Zweihander"),
        )

    def test_slug_title_stable(self):
        self.assertEqual(slug_title("Battle axe"), "battle-axe")


class TestRowTypingStrategies(unittest.TestCase):
    def test_leading_count_before_weapon_name(self):
        cells = {"result": "10 Zweihänder d10"}
        self.assertEqual(
            resolve_field(cells, {"column": "result", "strategy": "text_before_die"}),
            "Zweihänder",
        )

    def test_plain_and_skip_empty_damage(self):
        ammo = {"item": "20 arrows", "damage": ""}
        weapon = {"item": "Femur", "damage": "d4"}
        typing = {
            "skip_when": [{"column": "damage", "empty": True}],
            "name": {"column": "item", "strategy": "plain"},
        }
        self.assertTrue(skip_row(ammo, typing))
        self.assertFalse(skip_row(weapon, typing))
        self.assertEqual(resolve_field(weapon, typing["name"]), "Femur")

    def test_match_when_selective_faces(self):
        typing = {
            "match_when": [{"column": "d12", "in": [3, 4]}],
            "name": {"column": "result", "strategy": "text_before_paren"},
        }
        dog = {
            "d12": 3,
            "result": "small but vicious dog (d6+2 HP, bite d4, only obeys you)",
        }
        elixir = {
            "d12": 1,
            "result": "1 life elixir d4 doses (heals d6 HP and removes infection)",
        }
        self.assertFalse(skip_row(dog, typing))
        self.assertTrue(skip_row(elixir, typing))
        self.assertEqual(resolve_field(dog, typing["name"]), "small but vicious dog")

    def test_paren_hp_attack_parse(self):
        from src.creature_sheet_materialization import parse_paren_hp_attack

        dog = parse_paren_hp_attack(
            "small but vicious dog (d6+2 HP, bite d4, only obeys you)"
        )
        self.assertEqual(dog["hp"], "d6+2")
        self.assertEqual(dog["attacks"][0]["name"], "bite")
        self.assertEqual(dog["attacks"][0]["damage"], "d4")
        monkeys = parse_paren_hp_attack(
            "d4 monkeys that ignore but love you (d4+2 HP, punch/bite d4)"
        )
        self.assertEqual(monkeys["hp"], "d4+2")
        self.assertEqual(monkeys["attacks"][0]["name"], "punch/bite")
        self.assertEqual(monkeys["attacks"][0]["damage"], "d4")

    def test_armor_before_paren_and_tier(self):
        cells = {
            "result": "light (fur, padded cloth, leather etc, −d2 damage, tier 1) 20s"
        }
        self.assertEqual(
            resolve_field(cells, {"column": "result", "strategy": "text_before_paren"}),
            "light",
        )
        self.assertEqual(
            resolve_field(cells, {"column": "result", "strategy": "tier_in_text"}),
            1,
        )


if __name__ == "__main__":
    unittest.main()
