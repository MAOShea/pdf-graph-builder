from src.ingest_cleanup import ingest_rel_delete_cypher
from src.shared.constants import INGEST_REL_TYPES


def test_ingest_rel_delete_includes_all_ingest_types():
    query = ingest_rel_delete_cypher()
    for rel in INGEST_REL_TYPES:
        assert rel in query
    assert "SELECTS" in query
    assert "CONTAINS" in query
    assert "APPLIES_DURING" in query
