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

    def test_table_matches_spec_columns(self):
        from src.table_materialization import _table_matches_spec

        spec = spec_by_name(self.manifest, "TrapsTable")
        table = {"columns": ["d12", "Trap"], "rows": [[1, "x"]]}
        self.assertTrue(_table_matches_spec(table, spec))


if __name__ == "__main__":
    unittest.main()
