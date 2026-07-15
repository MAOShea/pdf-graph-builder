import unittest
from unittest.mock import MagicMock

from src.bundle_materialization import (
    BundleWiringPlan,
    _selector_row_id,
    apply_bundle_wiring_plan,
    build_character_creation_wiring,
    bundles_schema_path,
    load_bundles_schema,
    materialize_character_creation_bundles,
)
from src.ingest_manifest import load_ingest_manifest


class TestBundleWiringPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_ingest_manifest()
        cls.bundles_data = load_bundles_schema()

    def test_bundles_schema_path_exists(self):
        self.assertTrue(bundles_schema_path().is_file())

    def test_selector_row_id_uses_d6_index(self):
        row_id = _selector_row_id(
            "OptionalClassesTable",
            {"d6": 1, "result": "Fanged deserter"},
            [{"name": "d6", "role": "index", "position": 0}],
        )
        self.assertEqual(row_id, "OptionalClassesTable:row:1")

    def test_build_plan_has_six_bundles_and_selects(self):
        plan = build_character_creation_wiring(self.manifest, self.bundles_data)
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.bundles), 6)
        self.assertEqual(len(plan.selects), 6)
        self.assertEqual(plan.selects[0], ("OptionalClassesTable:row:1", "FangedDeserter"))

    def test_build_plan_contains_nested_tables(self):
        plan = build_character_creation_wiring(self.manifest, self.bundles_data)
        fanged_contains = [t for b, t in plan.contains if b == "FangedDeserter"]
        self.assertIn("EarliestMemoriesTable", fanged_contains)
        self.assertIn("FangedDeserterEquipmentTable", fanged_contains)

    def test_build_plan_uses_external_tables(self):
        plan = build_character_creation_wiring(self.manifest, self.bundles_data)
        gutterborn_uses = {t for b, t in plan.uses if b == "GutterbornScum"}
        self.assertEqual(gutterborn_uses, {"WeaponTable", "ArmorTable"})

    def test_apply_plan_merges_edges(self):
        plan = BundleWiringPlan(
            bundles=[{"id": "FangedDeserter", "name": "Fanged deserter", "pages": "46-47"}],
            selector_table="OptionalClassesTable",
            selects=[("OptionalClassesTable:row:1", "FangedDeserter")],
            contains=[("FangedDeserter", "EarliestMemoriesTable")],
            applies_during_links=["FangedDeserter"],
        )
        graph = MagicMock()
        graph.query.side_effect = [
            [{"linked": 1}],  # bundle INSTANCE_OF
            [{"linked": 1}],  # CharacterCreation USES selector
            [{"linked": 1}],  # APPLIES_DURING
            [{"linked": 1}],  # SELECTS
            [{"linked": 1}],  # CONTAINS
        ]
        scaffold_map = {
            "seed_nodes": {
                "optionalclass": {"labels": ["OptionalClass"], "seed_id": "OptionalClass"},
            }
        }
        stats = apply_bundle_wiring_plan(
            graph,
            plan,
            "mork-borg.pdf",
            scaffold_map,
            cc_config={"materialization": {"bundle_instance_of": "OptionalClass"}},
        )
        self.assertEqual(stats["bundles_created"], 1)
        self.assertEqual(stats["selects_linked"], 1)
        self.assertEqual(stats["contains_linked"], 1)
        self.assertEqual(stats["applies_during_linked"], 1)
        self.assertGreaterEqual(graph.query.call_count, 5)

    def test_missing_nested_table_warns_not_raises(self):
        plan = BundleWiringPlan(
            bundles=[{"id": "FangedDeserter", "name": "Fanged deserter"}],
            contains=[("FangedDeserter", "MissingTable")],
            applies_during_links=["FangedDeserter"],
            character_creation_uses_selector=False,
        )
        graph = MagicMock()
        graph.query.side_effect = [
            [{"linked": 1}],  # bundle
            [{"linked": 1}],  # APPLIES_DURING
            [{"linked": 0}],  # CONTAINS — table missing
        ]
        scaffold_map = {
            "seed_nodes": {
                "optionalclass": {"labels": ["OptionalClass"], "seed_id": "OptionalClass"},
            }
        }
        stats = apply_bundle_wiring_plan(
            graph,
            plan,
            "mork-borg.pdf",
            scaffold_map,
            cc_config={"materialization": {"bundle_instance_of": "OptionalClass"}},
        )
        self.assertEqual(stats["contains_linked"], 0)
        self.assertGreater(stats["warnings"], 0)

    def test_materialize_skips_without_character_creation(self):
        graph = MagicMock()
        stats = materialize_character_creation_bundles(
            graph,
            "mork-borg.pdf",
            {},
            game="nonexistent-game-xyz",
        )
        self.assertEqual(stats["bundles_created"], 0)
        graph.query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
