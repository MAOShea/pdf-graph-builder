import json
import unittest

from src.ingest_manifest import load_ingest_manifest, spec_by_name
from src.table_materialization import _table_matches_spec


class TestTableMaterializationMatching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_ingest_manifest()

    def test_matches_dr_by_manifest_name(self):
        spec = spec_by_name(self.manifest, "DRTable")
        table = {
            "manifest_name": "DRTable",
            "columns": ["DR", "label"],
            "rows": [[6, "x"], [8, "y"], [10, "a"], [12, "b"], [14, "c"], [16, "d"], [18, "e"]],
        }
        self.assertTrue(_table_matches_spec(table, spec))

    def test_matches_by_column_shape(self):
        spec = spec_by_name(self.manifest, "WeatherTable")
        table = {"columns": ["d12", "Weather"], "rows": [[1, "rain"]]}
        self.assertTrue(_table_matches_spec(table, spec))

    def test_rejects_wrong_columns(self):
        spec = spec_by_name(self.manifest, "DRTable")
        table = {"columns": ["d12", "Trap"], "rows": []}
        self.assertFalse(_table_matches_spec(table, spec))


if __name__ == "__main__":
    unittest.main()
