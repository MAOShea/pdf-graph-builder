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

    def test_table_matches_spec_columns(self):
        from src.table_materialization import _table_matches_spec

        spec = spec_by_name(self.manifest, "TrapsTable")
        table = {"columns": ["d12", "Trap"], "rows": [[1, "x"]]}
        self.assertTrue(_table_matches_spec(table, spec))


if __name__ == "__main__":
    unittest.main()
