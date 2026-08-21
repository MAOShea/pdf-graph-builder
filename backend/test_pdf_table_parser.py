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

    def test_wander_table_stops_before_who_contacts(self):
        spec = spec_by_name(self.manifest, "WanderTable")
        sample = (
            "Where do you wander? (d12)\n"
            "1\tOn the barren fields of Kergüs\n"
            "2\tIn the centre of Alliáns\n"
            "3\tOn a beach not distant from Grift\n"
            "4\tOn a dirty Schleswig street\n"
            "5\tIn the poor Wästland countryside\n"
            "6\tAt the city wall of Galgenbeck\n"
            "7\tIn the untamed wilds of Tveland\n"
            "8\tNear the Valley of the Unfortunate Undead\n"
            "9\tPretty much lost in Sarkash\n"
            "10\tAt the Bergen Chrypt tree line\n"
            "11\tOnboard a ship on the Endless Sea\n"
            "12\tIn a forgotten part of Graven-Tosk\n"
            "WHO (or what) contacts you?\n"
            "1\tOne-eyed woman who rules the thieves\n"
            "2\tBureaucrat with enemies and no honor\n"
        )
        table = extract_table_from_text(sample, spec, page_number=68, allow_multi_page=True)
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 12)
        by_face = {str(r[0]): r[1] for r in table["rows"]}
        self.assertIn("Tveland", by_face["7"])
        self.assertIn("Graven-Tosk", by_face["12"])
        self.assertNotIn("One-eyed", by_face["12"])
        self.assertNotIn("contacts", by_face["12"].lower())

    def test_wander_table_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        spec = spec_by_name(self.manifest, "WanderTable")
        self.assertIsNotNone(spec)
        by_page = load_pdf_text_by_page(pdf)
        span = page_span(spec)
        text = "\n".join(by_page.get(p, "") for p in span)
        table = extract_lookup_table(
            spec,
            text=text,
            pdf_path=pdf,
            page_number=span[0],
            allow_multi_page=len(span) > 1,
            text_filters=(load_passage_sections() or {}).get("text_filters"),
        )
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 12)
        by_face = {str(r[0]): r[1] for r in table["rows"]}
        self.assertIn("Tveland", by_face["7"])
        self.assertIn("Graven-Tosk", by_face["12"])
        self.assertNotIn("One-eyed", by_face["12"])
        self.assertNotIn("contacts", by_face["12"].lower())
        blob = " ".join(by_face.values()).lower()
        self.assertNotIn("one-eyed", blob)

    def test_who_contacts_stops_before_adventure_spark(self):
        spec = spec_by_name(self.manifest, "WhoContactsYouTable")
        body_rows = "\n".join(
            f"{i}\tcontact-{i}" if i != 13 else "13\tMonk who was bitten at night"
            for i in range(1, 21)
        )
        sample = (
            "WHO (or what) contacts you?\n"
            f"{body_rows}\n"
            "Adventure spark (d100)\n"
            "1–2\tThe undead-riddled Valley awaits\n"
        )
        table = extract_table_from_text(sample, spec, page_number=68, allow_multi_page=True)
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 20)
        by_face = {str(r[0]): r[1] for r in table["rows"]}
        self.assertIn("bitten", by_face["13"].lower())
        self.assertNotIn("Valley", by_face["20"])
        blob = " ".join(by_face.values()).lower()
        self.assertNotIn("adventure spark", blob)
        self.assertNotIn("undead-riddled", blob)

    def test_who_contacts_table_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.section_chunking import filter_page_texts
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        spec = spec_by_name(self.manifest, "WhoContactsYouTable")
        self.assertIsNotNone(spec)
        contract = load_passage_sections() or {}
        by_page = filter_page_texts(
            load_pdf_text_by_page(pdf),
            contract.get("text_filters"),
            normalize_whitespace=True,
        )
        span = page_span(spec)
        text = "\n".join(by_page.get(p, "") for p in span)
        table = extract_lookup_table(
            spec,
            text=text,
            pdf_path=pdf,
            page_number=span[0],
            allow_multi_page=len(span) > 1,
            text_filters=contract.get("text_filters"),
        )
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 20)
        by_face = {str(r[0]): r[1] for r in table["rows"]}
        self.assertIn("One-eyed", by_face["1"])
        self.assertIn("bitten", by_face["13"].lower())
        self.assertIn("Terrified soldier", by_face["20"])
        blob = " ".join(by_face.values()).lower()
        self.assertNotIn("undead-riddled", blob)
        self.assertNotIn("adventure spark", blob)
        self.assertNotIn("cont.", blob)

    def test_adventure_spark_stops_before_bedeviled(self):
        spec = spec_by_name(self.manifest, "AdventureSparkTable")
        pairs = [(i, i + 1) for i in range(1, 99, 2)] + [(99, 0)]
        lines = ["Adventure spark (d100)"]
        for lo, hi in pairs:
            key = f"{lo}-{hi:02d}" if hi == 0 else f"{lo}-{hi}"
            result = "Find the way to Cube-Violet" if lo == 55 else f"spark-{lo}"
            lines.append(f"{key}\t{result}")
        lines.append("One of the many")
        lines.append("Bedeviled Dungeons")
        sample = "\n".join(lines) + "\n"
        table = extract_table_from_text(sample, spec, page_number=69, allow_multi_page=True)
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 50)
        by_face = {str(r[0]): r[1] for r in table["rows"]}
        self.assertIn("Cube-Violet", by_face["55-56"])
        blob = " ".join(by_face.values()).lower()
        self.assertNotIn("bedeviled", blob)
        self.assertNotIn("one of the many", blob)

    def test_adventure_spark_table_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.section_chunking import filter_page_texts
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        spec = spec_by_name(self.manifest, "AdventureSparkTable")
        self.assertIsNotNone(spec)
        contract = load_passage_sections() or {}
        by_page = filter_page_texts(
            load_pdf_text_by_page(pdf),
            contract.get("text_filters"),
            normalize_whitespace=True,
        )
        span = page_span(spec)
        text = "\n".join(by_page.get(p, "") for p in span)
        table = extract_lookup_table(
            spec,
            text=text,
            pdf_path=pdf,
            page_number=span[0],
            allow_multi_page=len(span) > 1,
            text_filters=contract.get("text_filters"),
        )
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 50)
        by_face = {str(r[0]): r[1] for r in table["rows"]}
        self.assertIn("Cube-Violet", by_face["55-56"])
        self.assertIn("Sarkash", by_face["99-00"])
        blob = " ".join(by_face.values()).lower()
        self.assertNotIn("bedeviled", blob)
        self.assertNotIn("cont.", blob)

    def test_bedeviled_name_lists_keep_one_column_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        filters = (load_passage_sections() or {}).get("text_filters")
        first = extract_lookup_table(
            spec_by_name(self.manifest, "BedeviledDungeonFirstTable"),
            pdf_path=pdf,
            text_filters=filters,
        )
        second = extract_lookup_table(
            spec_by_name(self.manifest, "BedeviledDungeonSecondTable"),
            pdf_path=pdf,
            text_filters=filters,
        )
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(len(first["rows"]), 12)
        self.assertEqual(len(second["rows"]), 12)
        first_by = {str(r[0]): r[1] for r in first["rows"]}
        second_by = {str(r[0]): r[1] for r in second["rows"]}
        self.assertEqual(first_by["1"], "Slaughter")
        self.assertEqual(first_by["7"], "Sin")
        self.assertEqual(first_by["12"], "Slave")
        self.assertEqual(second_by["1"], "pit")
        self.assertEqual(second_by["3"], "temple")
        self.assertEqual(second_by["12"], "waste")
        first_blob = " ".join(first_by.values()).lower()
        second_blob = " ".join(second_by.values()).lower()
        self.assertNotIn("pit", first_blob)
        self.assertNotIn("temple", first_blob)
        self.assertNotIn("slaughter", second_blob)
        self.assertNotIn("sin", second_blob)
        self.assertNotIn("still active", first_blob)
        self.assertNotIn("still active", second_blob)
        self.assertNotIn("the", first_by["1"].lower())

    def test_status_table_does_not_pack_inactive_because(self):
        spec = spec_by_name(self.manifest, "StatusTable")
        sample = (
            "Status (d6)\n"
            "1–2\tStill active\n"
            "3–6\tInactive, because (d4)\n"
            "1\t\n\x07The place was invaded\n"
            "2\tEverything ended in disaster\n"
            "3\tIt was no longer needed\n"
            "4\tA Misery was fulfilled, roll to see which one (p. 10)\n"
            "Imminent danger (d10)\n"
        )
        table = extract_table_from_text(sample, spec, page_number=71)
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 2)
        by_key = {str(r[0]): r[1] for r in table["rows"]}
        self.assertEqual(by_key["1-2"], "Still active")
        self.assertIn("Inactive", by_key["3-6"])
        self.assertNotIn("invaded", by_key["3-6"].lower())
        self.assertNotIn("disaster", by_key["3-6"].lower())
        self.assertNotIn("Misery", by_key["3-6"])

    def test_status_and_inactive_because_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        filters = (load_passage_sections() or {}).get("text_filters")
        by_page = load_pdf_text_by_page(pdf)
        status_spec = spec_by_name(self.manifest, "StatusTable")
        nested_spec = spec_by_name(self.manifest, "InactiveBecauseTable")
        status_span = page_span(status_spec)
        nested_span = page_span(nested_spec)
        status_text = "\n".join(by_page.get(p, "") for p in status_span)
        nested_text = "\n".join(by_page.get(p, "") for p in nested_span)
        status = extract_lookup_table(
            status_spec,
            text=status_text,
            pdf_path=pdf,
            page_number=status_span[0],
            allow_multi_page=len(status_span) > 1,
            text_filters=filters,
        )
        nested = extract_lookup_table(
            nested_spec,
            text=nested_text,
            pdf_path=pdf,
            page_number=nested_span[0],
            allow_multi_page=len(nested_span) > 1,
            text_filters=filters,
        )
        self.assertIsNotNone(status)
        self.assertIsNotNone(nested)
        self.assertEqual(len(status["rows"]), 2)
        self.assertEqual(len(nested["rows"]), 4)
        status_by = {str(r[0]): r[1] for r in status["rows"]}
        nested_by = {str(r[0]): r[1] for r in nested["rows"]}
        self.assertEqual(status_by["1-2"], "Still active")
        self.assertIn("Inactive", status_by["3-6"])
        self.assertNotIn("invaded", status_by["3-6"].lower())
        self.assertNotIn("disaster", status_by["3-6"].lower())
        self.assertIn("invaded", nested_by["1"].lower())
        self.assertIn("disaster", nested_by["2"].lower())
        self.assertIn("needed", nested_by["3"].lower())
        self.assertIn("Misery", nested_by["4"])
        self.assertNotIn("Imminent", nested_by["4"])
        self.assertNotIn("flooding", nested_by["4"].lower())

    def test_abilities_table_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        filters = (load_passage_sections() or {}).get("text_filters")
        spec = spec_by_name(self.manifest, "AbilitiesTable")
        span = page_span(spec)
        by_page = load_pdf_text_by_page(pdf)
        text = "\n".join(by_page.get(p, "") for p in span)
        table = extract_lookup_table(
            spec,
            text=text,
            pdf_path=pdf,
            page_number=span[0],
            allow_multi_page=len(span) > 1,
            text_filters=filters,
        )
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 7)
        by_key = {str(r[0]): r[1] for r in table["rows"]}
        self.assertIn("0", by_key["9-12"].replace("±", "").replace("+", ""))
        self.assertNotIn("Defend", by_key["1-4"])
        self.assertNotIn("Tests", " ".join(by_key.values()))

    def test_imminent_danger_does_not_pack_flooding_bands(self):
        spec = spec_by_name(self.manifest, "ImminentDangerTable")
        sample = (
            "Imminent danger (d10)\n"
            "1\tIs slowly flooding with (d4): 1–2 oil, 3–4 water\n"
            "2\tBerserkers are appearing\n"
            "3\tIs about to collapse\n"
            "4\tSenses are being distorted\n"
            "5\tUnderworld emissions of poisonous spores\n"
            "6\tA hunted cult intends it to be their new hideout\n"
            "7\tA terrible, dormant curse about to be unleashed\n"
            "8\tFire is spreading from the deepest chamber\n"
            "9\tThe gate will shut and seal, and not open again until seven days have passed\n"
            "10\tA lethal mechanism is about to activate\n"
            "Who or what dwells here now? (d12)\n"
        )
        table = extract_table_from_text(sample, spec, page_number=72)
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 10)
        by_key = {str(r[0]): r[1] for r in table["rows"]}
        self.assertIn("flooding", by_key["1"].lower())
        self.assertNotIn("oil", by_key["1"].lower())
        self.assertNotIn("water", by_key["1"].lower())
        self.assertIn("Berserkers", by_key["2"])
        blob = " ".join(by_key.values()).lower()
        self.assertNotIn("dwells", blob)

    def test_flooding_bands_stop_before_parent_row_2(self):
        spec = spec_by_name(self.manifest, "FloodingWithTable")
        sample = (
            "Imminent danger (d10)\n"
            "1\tIs slowly flooding with (d4): 1–2 oil, 3–4 water\n"
            "2\tBerserkers are appearing\n"
            "3\tIs about to collapse\n"
        )
        table = extract_table_from_text(sample, spec, page_number=72)
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 2)
        by_key = {str(r[0]): r[1] for r in table["rows"]}
        self.assertTrue(by_key["1-2"].lower().startswith("oil"))
        self.assertNotIn("water", by_key["1-2"].lower())
        self.assertEqual(by_key["3-4"].lower(), "water")
        self.assertNotIn("2", by_key["3-4"])
        self.assertNotIn("Berserkers", by_key["3-4"])

    def test_imminent_danger_and_flooding_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        filters = (load_passage_sections() or {}).get("text_filters")
        by_page = load_pdf_text_by_page(pdf)
        danger_spec = spec_by_name(self.manifest, "ImminentDangerTable")
        flood_spec = spec_by_name(self.manifest, "FloodingWithTable")
        span = page_span(danger_spec)
        text = "\n".join(by_page.get(p, "") for p in span)
        danger = extract_lookup_table(
            danger_spec,
            text=text,
            pdf_path=pdf,
            page_number=span[0],
            allow_multi_page=len(span) > 1,
            text_filters=filters,
        )
        flood = extract_lookup_table(
            flood_spec,
            text=text,
            pdf_path=pdf,
            page_number=span[0],
            allow_multi_page=len(span) > 1,
            text_filters=filters,
        )
        self.assertIsNotNone(danger)
        self.assertIsNotNone(flood)
        self.assertEqual(len(danger["rows"]), 10)
        self.assertEqual(len(flood["rows"]), 2)
        danger_by = {str(r[0]): r[1] for r in danger["rows"]}
        flood_by = {str(r[0]): r[1] for r in flood["rows"]}
        self.assertIn("flooding", danger_by["1"].lower())
        self.assertNotIn("oil", danger_by["1"].lower())
        self.assertNotIn("water", danger_by["1"].lower())
        self.assertIn("Berserkers", danger_by["2"])
        self.assertIn("activate", danger_by["10"].lower())
        self.assertNotIn("dwells", danger_by["10"].lower())
        self.assertTrue(flood_by["1-2"].lower().startswith("oil"))
        self.assertNotIn("water", flood_by["1-2"].lower())
        self.assertEqual(flood_by["3-4"].lower(), "water")
        self.assertNotIn("Berserkers", " ".join(flood_by.values()))

    def test_dwells_here_table_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        spec = spec_by_name(self.manifest, "DwellsHereTable")
        self.assertIsNotNone(spec)
        by_page = load_pdf_text_by_page(pdf)
        span = page_span(spec)
        text = "\n".join(by_page.get(p, "") for p in span)
        table = extract_lookup_table(
            spec,
            text=text,
            pdf_path=pdf,
            page_number=span[0],
            allow_multi_page=len(span) > 1,
            text_filters=(load_passage_sections() or {}).get("text_filters"),
        )
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 12)
        by_face = {str(r[0]): r[1] for r in table["rows"]}
        self.assertIn("armor", by_face["1"].lower())
        self.assertIn("Wickheads", by_face["7"])
        self.assertIn("courtiers", by_face["12"].lower())
        blob = " ".join(by_face.values()).lower()
        self.assertNotIn("distinctive", blob)
        self.assertNotIn("portal", blob)
        self.assertNotIn("berserkers", blob)

    def test_distinctive_feature_table_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        spec = spec_by_name(self.manifest, "DistinctiveFeatureTable")
        self.assertIsNotNone(spec)
        by_page = load_pdf_text_by_page(pdf)
        span = page_span(spec)
        text = "\n".join(by_page.get(p, "") for p in span)
        table = extract_lookup_table(
            spec,
            text=text,
            pdf_path=pdf,
            page_number=span[0],
            allow_multi_page=len(span) > 1,
            text_filters=(load_passage_sections() or {}).get("text_filters"),
        )
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 12)
        by_face = {str(r[0]): r[1] for r in table["rows"]}
        self.assertIn("Portal", by_face["1"])
        self.assertIn("Obelisk", by_face["7"])
        self.assertIn("tar", by_face["12"].lower())
        blob = " ".join(by_face.values()).lower()
        self.assertNotIn("sample rooms", blob)
        self.assertNotIn("inscription", blob)
        self.assertNotIn("vomit", blob)
        self.assertNotIn("wickheads", blob)

    def test_sample_rooms_matrix_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        spec = spec_by_name(self.manifest, "SampleRoomsTable")
        self.assertIsNotNone(spec)
        by_page = load_pdf_text_by_page(pdf)
        span = page_span(spec)
        text = "\n".join(by_page.get(p, "") for p in span)
        table = extract_lookup_table(
            spec,
            text=text,
            pdf_path=pdf,
            page_number=span[0],
            allow_multi_page=len(span) > 1,
            text_filters=(load_passage_sections() or {}).get("text_filters"),
        )
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 24)
        by_cell = {(str(r[0]), str(r[1])): r[2] for r in table["rows"]}
        self.assertIn("Inscriptions", by_cell[("1", "1")])
        self.assertNotIn("vomit", by_cell[("1", "1")].lower())
        self.assertNotIn("hypnotic", by_cell[("1", "1")].lower())
        self.assertIn("Bloodied", by_cell[("1", "2")])
        self.assertIn("Fire", by_cell[("1", "6")])
        self.assertIn("Obvious", by_cell[("2", "1")])
        self.assertIn("Freezing", by_cell[("2", "5")])
        self.assertIn("Creaking", by_cell[("2", "6")])
        self.assertIn("Shelves", by_cell[("3", "3")])
        self.assertNotIn("literature", by_cell[("3", "3")].lower())
        self.assertNotIn("rotting", by_cell[("3", "3")].lower())
        self.assertIn("altar", by_cell[("4", "3")].lower())
        self.assertNotIn("cracked", by_cell[("4", "3")].lower())
        self.assertNotIn("blood", by_cell[("4", "3")].lower())
        self.assertIn("Bonfire", by_cell[("4", "6")])
        blob = " ".join(by_cell.values()).lower()
        self.assertNotIn("obelisk", blob)
        self.assertNotIn("anthelia", blob)

    def test_inscription_motifs_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        spec = spec_by_name(self.manifest, "InscriptionMotifsTable")
        self.assertIsNotNone(spec)
        by_page = load_pdf_text_by_page(pdf)
        span = page_span(spec)
        text = "\n".join(by_page.get(p, "") for p in span)
        table = extract_lookup_table(
            spec,
            text=text,
            pdf_path=pdf,
            page_number=span[0],
            allow_multi_page=len(span) > 1,
            text_filters=(load_passage_sections() or {}).get("text_filters"),
        )
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 6)
        by_face = {str(r[0]): r[1] for r in table["rows"]}
        self.assertIn("Vomit", by_face["1"])
        self.assertEqual(by_face["3"], "Hypnotic")
        self.assertIn("pointless", by_face["6"].lower())
        self.assertNotIn("2", by_face["6"])
        blob = " ".join(by_face.values()).lower()
        self.assertNotIn("bloodied", blob)
        self.assertNotIn("flooded", blob)
        self.assertNotIn("obelisk", blob)

    def test_shelves_and_altar_bands_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        shelves_spec = spec_by_name(self.manifest, "ShelvesWithTable")
        altar_spec = spec_by_name(self.manifest, "SacrificialAltarTable")
        self.assertIsNotNone(shelves_spec)
        self.assertIsNotNone(altar_spec)
        by_page = load_pdf_text_by_page(pdf)
        filters = (load_passage_sections() or {}).get("text_filters")
        shelves_span = page_span(shelves_spec)
        altar_span = page_span(altar_spec)
        shelves_text = "\n".join(by_page.get(p, "") for p in shelves_span)
        altar_text = "\n".join(by_page.get(p, "") for p in altar_span)
        shelves = extract_lookup_table(
            shelves_spec,
            text=shelves_text,
            pdf_path=pdf,
            page_number=shelves_span[0],
            allow_multi_page=len(shelves_span) > 1,
            text_filters=filters,
        )
        altar = extract_lookup_table(
            altar_spec,
            text=altar_text,
            pdf_path=pdf,
            page_number=altar_span[0],
            allow_multi_page=len(altar_span) > 1,
            text_filters=filters,
        )
        self.assertIsNotNone(shelves)
        self.assertIsNotNone(altar)
        self.assertEqual(len(shelves["rows"]), 2)
        self.assertEqual(len(altar["rows"]), 2)
        shelves_by = {str(r[0]): r[1] for r in shelves["rows"]}
        altar_by = {str(r[0]): r[1] for r in altar["rows"]}
        self.assertIn("literature", shelves_by["1-2"].lower())
        self.assertNotIn("food", shelves_by["1-2"].lower())
        self.assertIn("food", shelves_by["3-4"].lower())
        self.assertNotIn("literature", shelves_by["3-4"].lower())
        self.assertNotIn("abyssal", " ".join(shelves_by.values()).lower())
        self.assertIn("cracked", altar_by["1-2"].lower())
        self.assertNotIn("blood", altar_by["1-2"].lower())
        self.assertIn("blood", altar_by["3-4"].lower())
        self.assertNotIn("cracked", altar_by["3-4"].lower())
        self.assertNotIn("throne", " ".join(altar_by.values()).lower())
        self.assertNotIn("literature", " ".join(altar_by.values()).lower())

    def test_wields_table_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        spec = spec_by_name(self.manifest, "WieldsTable")
        self.assertIsNotNone(spec)
        by_page = load_pdf_text_by_page(pdf)
        span = page_span(spec)
        text = "\n".join(by_page.get(p, "") for p in span)
        table = extract_lookup_table(
            spec,
            text=text,
            pdf_path=pdf,
            page_number=span[0],
            allow_multi_page=len(span) > 1,
            text_filters=(load_passage_sections() or {}).get("text_filters"),
        )
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 4)
        by_face = {str(r[0]): r[1] for r in table["rows"]}
        self.assertIn("flail", by_face["1"].lower())
        self.assertIn("Chained", by_face["3"])
        self.assertIn("warhammer", by_face["4"].lower())
        blob = " ".join(by_face.values()).lower()
        self.assertNotIn("ambush", blob)
        self.assertNotIn("wraith", blob)
        self.assertNotIn("zukuma", blob)

    def test_earthbound_tables_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        by_page = load_pdf_text_by_page(pdf)
        filters = (load_passage_sections() or {}).get("text_filters")
        expected = {
            "EarthboundTraitTable": ("3", "Joking", 4),
            "EarthboundSpecialtyTable": ("3", "Senses danger", 4),
            "EarthboundValuesTable": ("3", "Endless tasks", 6),
        }
        for name, (face, needle, n_rows) in expected.items():
            spec = spec_by_name(self.manifest, name)
            self.assertIsNotNone(spec, name)
            span = page_span(spec)
            text = "\n".join(by_page.get(p, "") for p in span)
            table = extract_lookup_table(
                spec,
                text=text,
                pdf_path=pdf,
                page_number=span[0],
                allow_multi_page=len(span) > 1,
                text_filters=filters,
            )
            self.assertIsNotNone(table, name)
            self.assertEqual(len(table["rows"]), n_rows, name)
            by_face = {str(r[0]): r[1] for r in table["rows"]}
            self.assertIn(needle, by_face[face], name)
            blob = " ".join(by_face.values()).lower()
            self.assertNotIn("hp 8", blob)
            self.assertNotIn("morale", blob)
            self.assertNotIn("wickhead", blob)
            self.assertNotIn("grumpy", blob)

    def test_wild_wickhead_tables_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        by_page = load_pdf_text_by_page(pdf)
        filters = (load_passage_sections() or {}).get("text_filters")
        spec_t = spec_by_name(self.manifest, "WildWickheadTraitTable")
        spec_s = spec_by_name(self.manifest, "WildWickheadSpecialtyTable")
        spec_v = spec_by_name(self.manifest, "WildWickheadValuesTable")
        span = page_span(spec_t)
        text = "\n".join(by_page.get(p, "") for p in span)

        trait = extract_lookup_table(
            spec_t, text=text, pdf_path=pdf, page_number=span[0],
            allow_multi_page=False, text_filters=filters,
        )
        self.assertIsNotNone(trait)
        self.assertEqual(len(trait["rows"]), 4)
        by_face = {str(r[0]): r[1] for r in trait["rows"]}
        self.assertIn("Careless", by_face["3"])
        blob_t = " ".join(by_face.values()).lower()
        self.assertIn("grumpy", blob_t)
        self.assertNotIn("hp 10", blob_t)
        self.assertNotIn("morale", blob_t)

        spec = extract_lookup_table(
            spec_s, text=text, pdf_path=pdf, page_number=span[0],
            allow_multi_page=False, text_filters=filters,
        )
        self.assertIsNotNone(spec)
        self.assertEqual(len(spec["rows"]), 3)
        by_s = {str(r[0]): r[1] for r in spec["rows"]}
        self.assertIn("Walking", by_s["1-2"])
        self.assertIn("knife", by_s["3"].lower())
        self.assertIn("Backstab", by_s["4"])
        blob_s = " ".join(by_s.values()).lower()
        self.assertNotIn("five items", blob_s)
        self.assertNotIn("values", blob_s)

        values = extract_lookup_table(
            spec_v, text=text, pdf_path=pdf, page_number=span[0],
            allow_multi_page=False, text_filters=filters,
        )
        self.assertIsNotNone(values)
        self.assertEqual(len(values["rows"]), 6)
        by_v = {str(r[0]): r[1] for r in values["rows"]}
        self.assertIn("sharp weapons", by_v["3"].lower())
        blob_v = " ".join(by_v.values()).lower()
        self.assertNotIn("pale", blob_v)
        self.assertNotIn("bitter", blob_v)

    def test_pale_one_tables_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        by_page = load_pdf_text_by_page(pdf)
        filters = (load_passage_sections() or {}).get("text_filters")
        spec_t = spec_by_name(self.manifest, "PaleOneTraitTable")
        spec_s = spec_by_name(self.manifest, "PaleOneSpecialtyTable")
        spec_v = spec_by_name(self.manifest, "PaleOneValuesTable")
        span = page_span(spec_t)
        text = "\n".join(by_page.get(p, "") for p in span)

        trait = extract_lookup_table(
            spec_t, text=text, pdf_path=pdf, page_number=span[0],
            allow_multi_page=False, text_filters=filters,
        )
        self.assertIsNotNone(trait)
        self.assertEqual(len(trait["rows"]), 4)
        by_face = {str(r[0]): r[1] for r in trait["rows"]}
        self.assertIn("Mute", by_face["3"])
        blob_t = " ".join(by_face.values()).lower()
        self.assertIn("bitter", blob_t)
        self.assertNotIn("hp 5", blob_t)
        self.assertNotIn("morale", blob_t)
        self.assertNotIn("once per day", blob_t)

        spec = extract_lookup_table(
            spec_s, text=text, pdf_path=pdf, page_number=span[0],
            allow_multi_page=False, text_filters=filters,
        )
        self.assertIsNotNone(spec)
        self.assertEqual(len(spec["rows"]), 4)
        by_s = {str(r[0]): r[1] for r in spec["rows"]}
        self.assertIn("decoction", by_s["1"].lower())
        self.assertIn("elixir vitalis", by_s["2"].lower())
        self.assertIn("unclean", by_s["3"].lower())
        self.assertIn("sacred", by_s["4"].lower())
        blob_s = " ".join(by_s.values()).lower()
        self.assertNotIn("once per day", blob_s)
        self.assertNotIn("values", blob_s)
        self.assertNotIn("mute", blob_s)

        values = extract_lookup_table(
            spec_v, text=text, pdf_path=pdf, page_number=span[0],
            allow_multi_page=False, text_filters=filters,
        )
        self.assertIsNotNone(values)
        self.assertEqual(len(values["rows"]), 6)
        by_v = {str(r[0]): r[1] for r in values["rows"]}
        self.assertIn("melancholic", by_v["3"].lower())
        blob_v = " ".join(by_v.values()).lower()
        self.assertNotIn("prowler", blob_v)
        self.assertNotIn("hp 5", blob_v)

    def test_prowler_tables_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        by_page = load_pdf_text_by_page(pdf)
        filters = (load_passage_sections() or {}).get("text_filters")
        spec_t = spec_by_name(self.manifest, "ProwlerTraitTable")
        spec_s = spec_by_name(self.manifest, "ProwlerSpecialtyTable")
        spec_v = spec_by_name(self.manifest, "ProwlerValuesTable")
        span = page_span(spec_t)
        text = "\n".join(by_page.get(p, "") for p in span)

        trait = extract_lookup_table(
            spec_t, text=text, pdf_path=pdf, page_number=span[0],
            allow_multi_page=False, text_filters=filters,
        )
        self.assertIsNotNone(trait)
        self.assertEqual(len(trait["rows"]), 4)
        by_face = {str(r[0]): r[1] for r in trait["rows"]}
        self.assertIn("Liar", by_face["3"])
        blob_t = " ".join(by_face.values()).lower()
        self.assertIn("lazy", blob_t)
        self.assertNotIn("hp 8", blob_t)
        self.assertNotIn("morale", blob_t)
        self.assertNotIn("shortsword", blob_t)

        spec = extract_lookup_table(
            spec_s, text=text, pdf_path=pdf, page_number=span[0],
            allow_multi_page=False, text_filters=filters,
        )
        self.assertIsNotNone(spec)
        self.assertEqual(len(spec["rows"]), 4)
        by_s = {str(r[0]): r[1] for r in spec["rows"]}
        self.assertIn("traps", by_s["1"].lower())
        self.assertIn("steal", by_s["2"].lower())
        self.assertIn("climb", by_s["3"].lower())
        self.assertIn("hidden", by_s["4"].lower())
        blob_s = " ".join(by_s.values()).lower()
        self.assertNotIn("dr8", blob_s)
        self.assertNotIn("gossip", blob_s)
        self.assertNotIn("liar", blob_s)

        values = extract_lookup_table(
            spec_v, text=text, pdf_path=pdf, page_number=span[0],
            allow_multi_page=False, text_filters=filters,
        )
        self.assertIsNotNone(values)
        self.assertEqual(len(values["rows"]), 6)
        by_v = {str(r[0]): r[1] for r in values["rows"]}
        self.assertIn("Gossip", by_v["3"])
        blob_v = " ".join(by_v.values()).lower()
        self.assertNotIn("wander", blob_v)
        self.assertNotIn("kerg", blob_v)
        self.assertNotIn("hp 8", blob_v)


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
        row19 = by_face["19"]
        self.assertIn("Cube-Violet", row19[1])
        self.assertNotIn("Kulvan", row19[1])
        self.assertNotIn("To leave", row19[1])
        row20 = by_face["20"]
        self.assertIn("basilisk", row20[1].lower())

    def test_to_leave_table_from_pdf(self):
        from src.ingest_manifest import _project_root, load_passage_sections
        from src.pdf_table_parser import extract_lookup_table, page_span
        from src.table_pipeline import load_pdf_text_by_page

        pdf = _project_root() / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        spec = spec_by_name(self.manifest, "ToLeaveTable")
        self.assertIsNotNone(spec)
        self.assertEqual((spec.get("pdf_extract") or {}).get("index", {}).get("type"), "d4")
        by_page = load_pdf_text_by_page(pdf)
        span = page_span(spec)
        text = "\n".join(by_page.get(p, "") for p in span)
        table = extract_lookup_table(
            spec,
            text=text,
            pdf_path=pdf,
            page_number=span[0],
            allow_multi_page=len(span) > 1,
            text_filters=(load_passage_sections() or {}).get("text_filters"),
        )
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 4)
        by_face = {str(r[0]): r[1] for r in table["rows"]}
        self.assertIn("Kulvan", by_face["1"])
        self.assertIn("Sict-Shroom", by_face["2"])
        self.assertIn("golden key", by_face["3"].lower())
        self.assertIn("empty", by_face["4"].lower())
        self.assertNotIn("basilisk", by_face["4"].lower())
        self.assertNotIn("Perhaps", by_face["4"])

    def test_to_leave_stops_before_catastrophe_20_with_bel_bullet(self):
        spec = spec_by_name(self.manifest, "ToLeaveTable")
        sample = (
            "To leave (d4):\n"
            "1. Slay riddling Kulvan (strong goblin, page 58) who holds three colorless pearls.\n"
            "2. Poison a close friend with crumbled Sict-Shroom.\n"
            "3. Reach up through the fire to the golden key above.\n"
            "4. The cube is perfect, and empty. You can only wait.\n"
            "20\t\n\x07Perhaps it's for the best. HE emerges from the shadows.\n"
            "Optional Classes (d6)\n"
        )
        table = extract_table_from_text(sample, spec, page_number=45, allow_multi_page=True)
        self.assertIsNotNone(table)
        self.assertEqual(len(table["rows"]), 4)
        self.assertNotIn("Perhaps", table["rows"][3][1])
        self.assertNotIn("basilisk", table["rows"][3][1].lower())

    def test_to_leave_span_covers_catastrophe_20_prose(self):
        from src.document_extract import resolve_tables_in_span

        sample = (
            "To leave (d4):\n"
            "1. Slay riddling Kulvan (strong goblin, page 58) who holds three colorless pearls.\n"
            "2. Poison a close friend with crumbled Sict-Shroom.\n"
            "3. Reach up through the fire to the golden key above.\n"
            "4. The cube is perfect, and empty. You can only wait.\n"
            "20\t\n\x07Perhaps it's for the best. HE emerges from the shadows.\n"
            "as the two-headed basilisk devour you.\n"
            "Optional Classes (d6)\n"
        )
        hits, warnings = resolve_tables_in_span(
            sample, names_filter=["ToLeaveTable"]
        )
        self.assertEqual(warnings, [])
        self.assertEqual(len(hits), 1)
        hit = hits[0]
        self.assertNotIn("Perhaps", hit.table["rows"][3][1])
        self.assertNotIn("basilisk", hit.table["rows"][3][1].lower())
        covered = sample[hit.start : hit.end]
        self.assertIn("Perhaps", covered)
        leftover = sample[hit.end :]
        self.assertNotIn("Perhaps", leftover)
        self.assertNotIn("basilisk", leftover.lower())


if __name__ == "__main__":
    unittest.main()
