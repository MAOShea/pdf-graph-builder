import json
import unittest

from src.ingest_manifest import load_ingest_manifest, spec_by_name
from src.pdf_table_parser import extract_all_tables_from_text, extract_table_from_text

DR_SAMPLE = (
    "Difficulty Ratings (DR) 6\t so simple people laugh at you for failing "
    "8\t routine but some chance of failure 10\t pretty simple but not simple enough to not roll "
    "12\t normal 14\t difficult 16\t really hard 18\t should not be possible "
    "Carrying Capacity You can carry Strength+8"
)

PAGE4_SAMPLE = (
    "Traps and Devilry (d12) 1 Well dressed corpse, booby trapped "
    "2 Wall-holes shoot poisonous arrows 3 Bells and marbles on the floor "
    "4 Scorpion-filled basket poised to fall 5 Fish hooks hanging at eye level "
    "6 Chest marked with explosive runes 7 Lock trapped with vial of poison gas "
    "8 Jewel removal leads to roof collapse 9 Slanted floor, translucent oil, pit "
    "10 Snake-cages on collapsing ceiling tiles 11 Evil urns release cold ghosts "
    "12 Coins coated in grime and poison weather (d12) 1 Lifeless grey "
    "2 Hammering rain 3 Piercing wind 4 Deafening storm 5 Black as night "
    "6 Dead quiet 7 Cloudburst 8 Soup-thick mist 9 Crackling frost "
    "10 Irritating drizzle 11 Roaring thunder 12 Gravelike cold "
    "Corpse plundering (d66) 11–16 The remains of something worthless"
)


class TestManifestPdfParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_ingest_manifest()

    def test_dr_table_from_manifest(self):
        spec = spec_by_name(self.manifest, "DRTable")
        table = extract_table_from_text(DR_SAMPLE, spec, page_number=28)
        self.assertIsNotNone(table)
        self.assertEqual(table["manifest_name"], "DRTable")
        self.assertEqual(len(table["rows"]), 7)

    def test_dr_skips_wrong_page_when_prefer_page_set(self):
        spec = spec_by_name(self.manifest, "DRTable")
        self.assertIsNone(extract_table_from_text(DR_SAMPLE, spec, page_number=76))

    def test_page4_extracts_traps_and_weather(self):
        tables = extract_all_tables_from_text(PAGE4_SAMPLE, page_number=4)
        names = {t["manifest_name"] for t in tables}
        self.assertIn("TrapsTable", names)
        self.assertIn("WeatherTable", names)
        traps = next(t for t in tables if t["manifest_name"] == "TrapsTable")
        self.assertEqual(len(traps["rows"]), 12)

    def test_advancement_debris_mixed_range_list(self):
        spec = spec_by_name(self.manifest, "AdvancementDebrisTable")
        sample = (
            "Left in the debris you find\n"
            "d6\n"
            "1-3\n"
            "nothing\n"
            "4\n"
            "3d10 silver\n"
            "5\n"
            "an unclean scroll\n"
            "6\n"
            "a sacred scroll\n"
            "Ability changes\n"
            "Roll a d6 against every ability.\n"
        )
        table = extract_table_from_text(sample, spec, page_number=33)
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 4)
        by_key = {str(r[0]): r[1] for r in table["rows"]}
        self.assertEqual(by_key["1-3"], "nothing")
        self.assertIn("silver", by_key["4"].lower())
        self.assertIn("unclean", by_key["5"].lower())
        self.assertIn("sacred", by_key["6"].lower())

    def test_starting_possessions_sentence_plus_d6(self):
        """p.21 d6 has no heading; preceding sentence is lead_in, title is Starting equipment #1."""
        spec = spec_by_name(self.manifest, "StartingPossessionsTable")
        sample = (
            "Your soul and your silver are your own and equally easy to lose. "
            "To begin with, you are what you own:\n"
            "d6\n"
            "1–2\n"
            "nothing\n"
            "3\n"
            "backpack for 7 normal-sized items\n"
            "4\n"
            "sack for 10 normal-sized items\n"
            "5\n"
            "small wagon or one item above of your choice\n"
            "6\n"
            "donkey, not bad. Or one of the above of your choice\n"
            "d12\n"
            "1\n"
            "rope 30 feet\n"
        )
        table = extract_table_from_text(sample, spec, page_number=21)
        self.assertIsNotNone(table)
        self.assertEqual(table["title"], "Starting equipment #1")
        self.assertEqual(table["lead_in"], "To begin with, you are what you own:")
        self.assertEqual(len(table["rows"]), 5)
        by_key = {str(r[0]): r[1] for r in table["rows"]}
        self.assertEqual(by_key["1-2"], "nothing")
        self.assertIn("backpack", by_key["3"].lower())
        self.assertIn("donkey", by_key["6"].lower())
        self.assertNotIn("rope", " ".join(by_key.values()).lower())

    def test_starting_equipment_two_d12s_joined_by_and(self):
        """p.22 has two untitled d12 lists separated by 'and'; titles are contracted."""
        sample = (
            "donkey, not bad. Or one of the above of your choice\n"
            "d12\n"
            "1\n"
            "rope 30 feet\n"
            "2\n"
            "Presence + 4 torches\n"
            "3\n"
            "lantern with oil for Presence + 6 hours\n"
            "4\n"
            "magnesium strip\n"
            "5\n"
            "random unclean scroll\n"
            "6\n"
            "sharp needle\n"
            "7\n"
            "medicine chest Presence+4 uses (stops bleeding/infection and heals d6 HP)\n"
            "8\n"
            "metal file and lockpicks\n"
            "9\n"
            "bear trap (Presence DR14 to spot, d8 damage)\n"
            "10\n"
            "bomb (sealed bottle, d10 damage)\n"
            "11\n"
            "a bottle of red poison d4 doses (Toughness DR12 or d10 damage)\n"
            "12\n"
            "silver crucifix\n"
            "and\n"
            "d12\n"
            "1\n"
            "1 life elixir d4 doses (heals d6 HP and removes infection)\n"
            "2\n"
            "random sacred scroll\n"
            "3\n"
            "small but vicious dog (d6+2 HP, bite d4, only obeys you)\n"
            "4\n"
            "d4 monkeys that ignore but love you (d4+2 HP, punch/bite d4)\n"
            "5\n"
            "exquisite perfume worth 25s\n"
            "6\n"
            "toolbox 10 nails, tongs, hammer, small saw and drill\n"
            "7\n"
            "heavy chain 15 feet\n"
            "8\n"
            "grappling hook\n"
            "9\n"
            "shield (-1 HP damage or have the shield break to ignore one attack)\n"
            "10\n"
            "crowbar (d4 damage)\n"
            "11\n"
            "lard (may function as 5 meals in a pinch)\n"
            "12\n"
            "tent\n"
            "Scrolls are the twisted magic of MÖRK BORG. Read more on page 34.\n"
        )
        first = extract_table_from_text(
            sample, spec_by_name(self.manifest, "StartingEquipmentTable"), page_number=22
        )
        second = extract_table_from_text(
            sample, spec_by_name(self.manifest, "StartingEquipmentTable2"), page_number=22
        )
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first["title"], "Starting equipment #2")
        self.assertEqual(second["title"], "Starting equipment #3")
        self.assertEqual(len(first["rows"]), 12)
        self.assertEqual(len(second["rows"]), 12)
        by1 = {int(r[0]): r[1] for r in first["rows"]}
        by2 = {int(r[0]): r[1] for r in second["rows"]}
        self.assertEqual(by1[1], "rope 30 feet")
        self.assertEqual(by1[12], "silver crucifix")
        self.assertNotIn("elixir", " ".join(by1.values()).lower())
        self.assertIn("elixir", by2[1].lower())
        self.assertEqual(by2[12], "tent")
        self.assertNotIn("crucifix", " ".join(by2.values()).lower())

    def test_unclean_sacred_and_nested_foul_psychopomp(self):
        """Unclean d10 row 8 is a nested d6; Sacred is its own d10 heading."""
        sample = (
            "Unclean Scrolls d10\n"
            "1 Palms Open the Southern Gate: A ball of fire hits d2 creatures dealing d8 damage per creature.\n"
            "2 Tongue of Eris: A creature of your choice is confused for 10 minutes.\n"
            "3 Te-le-kin-esis: Move an object up to d10×10 feet for d6 minutes.\n"
            "4 Lucy-fires Levitation: Hover for Presence + d10 rounds.\n"
            "5 Daemon of Capillaries: One creature suffocates for d6 rounds, losing d4 HP per round.\n"
            "6 Nine Violet Signs Unknot the Storm: Produce d2 lightning bolts dealing d6 damage each.\n"
            "7 Metzhuotl Blind Your Eye: A creature becomes invisible for d6 rounds or until it is damaged, attacking/defending with DR6.\n"
            "8 Foul Psychompomp: Summon (d6): 1–3 d4 skeletons 4–6 d4 zombies\n"
            "9 Eyelid Blinds the Mind: d4 creatures fall asleep for one hour unless they succeed a DR14 test.\n"
            "10 Death: All creatures within 30 feet lose a total of 4d10 HP.\n"
            "Sacred Scrolls d10\n"
            "1 Grace of a Dead Saint: d2 creatures regain d10 HP each.\n"
            "2 Grace for a Sinner: A creature of your choice gets +d6 on one roll (damage, tests etc.)\n"
            "3 Whispers Pass the Gate: Ask three questions to a deceased creature.\n"
            "4 Aegis of Sorrow: A creature of your choice gains 2d6 extra HP for 10 rounds.\n"
            "5 Unmet Fate: One creature, dead for no more than a week, is awakened with terrible memories.\n"
            "6 Bestial Speech: You may speak with animals for d20 minutes.\n"
            "7 False Dawn/Night’s Chariot: Light or pitch black for 3d10 minutes.\n"
            "8 Hermetic Step: You find all traps in your path for 2d10 minutes.\n"
            "9 Roskoe’s consuming Glare: d4 creatures lose d8 HP each.\n"
            "10 Enochian Syntax: One creature blindly obeys a single command.\n"
            "The Basilisks Demand (d20)\n"
            "1 A sword that has killed exactly one dozen times\n"
        )
        unclean = extract_table_from_text(
            sample,
            spec_by_name(self.manifest, "UncleanScrollsTable"),
            page_number=34,
            allow_multi_page=True,
        )
        self.assertIsNotNone(unclean)
        self.assertEqual(len(unclean["rows"]), 10)
        by_u = {str(r[0]): r[1] for r in unclean["rows"]}
        self.assertIn("Foul Psychompomp", by_u["8"])
        self.assertIn("1–3", by_u["8"])
        self.assertNotIn("Grace of a Dead Saint", by_u["8"])

        sacred = extract_table_from_text(
            sample, spec_by_name(self.manifest, "SacredScrollsTable"), page_number=35
        )
        self.assertIsNotNone(sacred)
        self.assertEqual(len(sacred["rows"]), 10)
        by_s = {str(r[0]): r[1] for r in sacred["rows"]}
        self.assertIn("Grace of a Dead Saint", by_s["1"])
        self.assertIn("Enochian Syntax", by_s["10"])

        foul = extract_table_from_text(
            sample, spec_by_name(self.manifest, "FoulPsychopompSummonTable"), page_number=35
        )
        self.assertIsNotNone(foul)
        self.assertEqual(len(foul["rows"]), 2)
        by_f = {str(r[0]): r[1] for r in foul["rows"]}
        self.assertEqual(by_f["1-3"], "d4 skeletons")
        self.assertEqual(by_f["4-6"], "d4 zombies")
        self.assertNotIn("Grace", by_f["1-3"])
        self.assertNotIn("Eyelid", by_f["4-6"])

    def test_find_header_line_anchor_in_multiline_span(self):
        from src.pdf_table_parser import _find_header

        span = "Equipment\nBackpack\n6s\nHolds 7 normal-sized items\n"
        match = _find_header(span, [r"^\s*Equipment\s*$"])
        self.assertIsNotNone(match)
        self.assertEqual(match.group(0).strip(), "Equipment")
        self.assertIsNone(_find_header("Backpack\n6s\n", [r"^\s*Equipment\s*$"]))

    def test_table_matches_spec_columns(self):
        from src.table_materialization import _table_matches_spec

        spec = spec_by_name(self.manifest, "TrapsTable")
        table = {"columns": ["d12", "Trap"], "rows": [[1, "x"]]}
        self.assertTrue(_table_matches_spec(table, spec))

    def test_aligned_three_column_split_and_wrap(self):
        from src.pdf_table_parser import (
            cells_from_aligned_words,
            is_aligned_continuation_row,
        )

        cuts = [139.0, 170.0]
        backpack = cells_from_aligned_words(
            [(45.0, "Backpack"), (139.3, "6s"), (170.3, "Holds"), (199.8, "7"), (207.7, "normal-sized"), (272.6, "items")],
            cuts,
            3,
        )
        self.assertEqual(backpack, ["Backpack", "6s", "Holds 7 normal-sized items"])

        blanket = cells_from_aligned_words(
            [(45.3, "Blanket"), (139.3, "4s")],
            cuts,
            3,
        )
        self.assertEqual(blanket, ["Blanket", "4s", ""])
        self.assertFalse(is_aligned_continuation_row(blanket))

        wrap = cells_from_aligned_words(
            [(170.3, "Presence"), (215.4, "+"), (223.3, "4"), (231.4, "uses")],
            cuts,
            3,
        )
        self.assertEqual(wrap, ["", "", "Presence + 4 uses"])
        self.assertTrue(is_aligned_continuation_row(wrap))

        indented_ammo = cells_from_aligned_words(
            [(76.4, "20"), (90.0, "arrows"), (153.0, "10s")],
            [76.0, 153.0],
            3,
        )
        self.assertEqual(indented_ammo[0], "")
        self.assertIn("arrows", indented_ammo[1])
        self.assertEqual(indented_ammo[2], "10s")
        self.assertFalse(is_aligned_continuation_row(indented_ammo))

    def test_equipment_table_aligned_columns_from_pdf(self):
        from pathlib import Path

        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        spec = spec_by_name(self.manifest, "EquipmentTable")
        self.assertIsNotNone(spec)
        filters = (load_passage_sections() or {}).get("text_filters")
        table = extract_lookup_table(spec, pdf_path=pdf, text_filters=filters)
        self.assertIsNotNone(table)
        self.assertEqual(table["manifest_name"], "EquipmentTable")
        self.assertEqual(table["columns"], ["item", "silver", "notes"])
        by_item = {str(r[0]): r for r in table["rows"]}
        self.assertGreaterEqual(len(by_item), 45)
        self.assertEqual(len(table["rows"]), 45)
        self.assertNotIn("24", by_item)
        self.assertTrue(
            all("BORG" not in " ".join(str(c) for c in r).upper() for r in table["rows"])
        )
        self.assertEqual(by_item["Backpack"][1], "6s")
        self.assertIn("7", by_item["Backpack"][2])
        self.assertEqual(by_item["Crowbar"][1], "8s")
        self.assertEqual(by_item["Crucifix, silver"][1], "60s")
        self.assertIn("backpack", " ".join(by_item.keys()).lower())
        self.assertNotIn("Services", by_item)
        self.assertNotIn("Night in hospice", by_item)
        sack = by_item.get("Sack")
        self.assertIsNotNone(sack)
        self.assertEqual(sack[1], "3s")
        self.assertIn("10", sack[2])
        medicine = by_item.get("Medicine box")
        self.assertIsNotNone(medicine)
        self.assertIn("Presence", medicine[2])
        self.assertIn("uses", medicine[2])

    def _aligned_from_pdf(self, name):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        spec = spec_by_name(self.manifest, name)
        self.assertIsNotNone(spec)
        filters = (load_passage_sections() or {}).get("text_filters")
        table = extract_lookup_table(spec, pdf_path=pdf, text_filters=filters)
        self.assertIsNotNone(table)
        return table

    def test_services_table_two_columns_from_pdf(self):
        table = self._aligned_from_pdf("ServicesTable")
        self.assertEqual(table["columns"], ["item", "silver"])
        self.assertEqual(len(table["rows"]), 6)
        by_item = {str(r[0]): r[1] for r in table["rows"]}
        self.assertEqual(by_item["Night in hospice"], "3s")
        self.assertIn("40", by_item["Bribe, guard"])
        self.assertNotIn("Tier 1 to 2", by_item)
        self.assertNotIn("Repair Armor*", by_item)

    def test_weapon_shop_table_damage_item_silver_from_pdf(self):
        table = self._aligned_from_pdf("WeaponShopTable")
        self.assertEqual(table["columns"], ["damage", "item", "silver"])
        self.assertEqual(len(table["rows"]), 19)
        by_item = {str(r[1]): r for r in table["rows"]}
        self.assertEqual(by_item["Battle axe"][0], "d8")
        self.assertEqual(by_item["Battle axe"][2], "35s")
        self.assertEqual(by_item["Femur"][2], "worthless")
        self.assertEqual(by_item["20 arrows"][0], "")
        self.assertEqual(by_item["20 arrows"][2], "10s")
        self.assertEqual(by_item["10 bolts"][2], "10s")
        self.assertNotIn("Dog (trained)", by_item)
        self.assertNotIn("Bow d6", " ".join(by_item.keys()))

    def test_beasts_table_two_columns_from_pdf(self):
        table = self._aligned_from_pdf("BeastsTable")
        self.assertEqual(table["columns"], ["item", "silver"])
        self.assertEqual(len(table["rows"]), 5)
        by_item = {str(r[0]): r[1] for r in table["rows"]}
        self.assertEqual(by_item["Dog (trained)"], "25s")
        self.assertEqual(by_item["Dog (wild)"], "10s")
        self.assertEqual(by_item["Rat (tame)"], "8s")
        self.assertNotIn("Battle axe", by_item)
        self.assertNotIn("10 bolts", by_item)


class TestSplitItalic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_ingest_manifest()

    def test_sandwich_die_token_inherits_italic(self):
        from src.pdf_table_parser import _fill_italic_sandwich, _split_immediate_unrealized

        pieces = [
            ("You feel fine. It's fine. ", False),
            ("You pustulate within ", True),
            ("d4", False),
            (" days then rise.", True),
        ]
        filled = _fill_italic_sandwich(pieces)
        self.assertFalse(filled[0][1])
        self.assertTrue(filled[2][1])
        immediate, unrealized = _split_immediate_unrealized(pieces)
        self.assertIn("feel fine", immediate)
        self.assertNotIn("d4", immediate)
        self.assertIn("d4", unrealized)
        self.assertIn("pustulate", unrealized)

    def test_text_only_extract_skips_split_italic_mode(self):
        spec = spec_by_name(self.manifest, "ArcaneCatastrophesTable")
        self.assertIsNotNone(spec)
        self.assertEqual((spec.get("pdf_extract") or {}).get("mode"), "split_italic")
        sample = (
            "Arcane catastrophes (d20) 1 One by one your teeth fall out. "
            "2 You feel fine. 7 Your skin tatters like paper "
            "Optional Classes (d6)"
        )
        self.assertIsNone(extract_table_from_text(sample, spec, page_number=43))

    def test_arcane_catastrophes_split_italic_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        spec = spec_by_name(self.manifest, "ArcaneCatastrophesTable")
        self.assertIsNotNone(spec)
        filters = (load_passage_sections() or {}).get("text_filters")
        table = extract_lookup_table(spec, pdf_path=pdf, text_filters=filters)
        self.assertIsNotNone(table)
        self.assertEqual(table["columns"], ["d20", "immediate", "unrealized"])
        self.assertEqual(table.get("italic_columns"), ["unrealized"])
        self.assertEqual(len(table["rows"]), 20)
        by_face = {str(r[0]): r for r in table["rows"]}
        row7 = by_face["7"]
        self.assertIn("tatters", row7[1].lower())
        self.assertEqual(row7[2], "")
        row1 = by_face["1"]
        self.assertIn("teeth", row1[1].lower())
        self.assertIn("smile", row1[2].lower())
        self.assertNotIn("teeth", row1[2].lower())
        row2 = by_face["2"]
        self.assertIn("d4", row2[2].lower())
        self.assertNotIn("d4", row2[1].lower())
        row11 = by_face["11"]
        self.assertEqual(row11[1], "")
        self.assertIn("d4", row11[2].lower())
        row18 = by_face["18"]
        self.assertIn("hp", row18[2].lower())
        row6 = by_face["6"]
        self.assertIn("No armor Bite/pinch", row6[1])
        blob = " ".join(" ".join(str(c) for c in r) for r in table["rows"])
        self.assertNotIn("cont.", blob.lower())
        self.assertNotIn("BORG", blob.upper())


if __name__ == "__main__":
    unittest.main()
