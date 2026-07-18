from src.ingest_coverage import expected_materialized_specs, expected_row_count
from src.ingest_manifest import load_ingest_manifest


def test_mork_borg_expected_tables_non_empty():
    manifest = load_ingest_manifest("mork-borg")
    specs = expected_materialized_specs(manifest, game="mork-borg")
    names = {s["name"] for s in specs}
    assert "DRTable" in names
    assert "WeaponTable" in names
    assert "CorpsePlunderTable" in names
    assert "OptionalClassesTable" in names
    assert len(specs) >= 45


def test_dr_table_expected_rows():
    manifest = load_ingest_manifest("mork-borg")
    dr = next(s for s in manifest["lookup_tables"] if s["name"] == "DRTable")
    assert expected_row_count(dr) == 7
