import json
import unittest

from src.table_materialization import DR_TABLE_INDEX_VALUES, is_dr_table


DR_TABLE = {
    "title": "DR",
    "columns": ["DR", "label"],
    "rows": [
        [6, "so simple people laugh at you for failing"],
        [8, "routine"],
        [10, "pretty simple"],
        [12, "normal"],
        [14, "difficult"],
        [16, "really hard"],
        [18, "should not be possible"],
    ],
}


class TestDrTableMatching(unittest.TestCase):
    def test_accepts_canonical_dr_table(self):
        self.assertTrue(is_dr_table(DR_TABLE))

    def test_rejects_wrong_columns(self):
        bad = dict(DR_TABLE, columns=["d12", "Trap"])
        self.assertFalse(is_dr_table(bad))

    def test_rejects_incomplete_rows(self):
        bad = dict(DR_TABLE, rows=[[6, "x"], [8, "y"]])
        self.assertFalse(is_dr_table(bad))

    def test_accepts_extra_rows_if_all_dr_values_present(self):
        extra = dict(
            DR_TABLE,
            rows=DR_TABLE["rows"] + [[99, "ignored"]],
        )
        self.assertTrue(is_dr_table(extra))

    def test_parsed_from_json_string_metadata_shape(self):
        table = json.loads(json.dumps(DR_TABLE))
        self.assertEqual(len([r for r in table["rows"] if r[0] in DR_TABLE_INDEX_VALUES]), 7)


if __name__ == "__main__":
    unittest.main()
