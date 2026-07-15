"""Verify Phase 2 optional-class ingest."""
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
)
db = os.getenv("NEO4J_DATABASE", "morkborg")

with driver.session(database=db) as s:
    print("=== Chunks ===")
    r = s.run(
        """
        MATCH (c:Chunk)-[:PART_OF]->(:Document {fileName: 'mork-borg.pdf'})
        RETURN count(c) AS n, min(c.page_number) AS min_p, max(c.page_number) AS max_p
        """
    ).single()
    print(dict(r))

    print("\n=== Materialized tables ===")
    for row in s.run(
        """
        MATCH (t:IngestNode)-[:HAS_ENTRY]->(r)
        WITH t, count(r) AS rows RETURN t.name AS table, rows ORDER BY table
        """
    ):
        print(f"  {row['table']}: {row['rows']}")

    print("\n=== Bundles + CONTAINS ===")
    for row in s.run(
        """
        MATCH (b:OptionalClass:IngestNode)
        OPTIONAL MATCH (b)-[:CONTAINS]->(t:IngestNode)
        RETURN b.id AS bundle, collect(t.name) AS nested ORDER BY bundle
        """
    ):
        print(dict(row))

    print("\n=== SELECTS ===")
    for row in s.run(
        """
        MATCH (row:TableEntry)-[:SELECTS]->(b:IngestNode)
        RETURN row.id AS row_id, b.id AS bundle ORDER BY row_id
        """
    ):
        print(dict(row))

    print("\n=== APPLIES_DURING ===")
    for row in s.run(
        """
        MATCH (b:IngestNode)-[:APPLIES_DURING]->(cc)
        RETURN b.id AS bundle, labels(cc) AS cc_labels
        ORDER BY bundle
        """
    ):
        print(dict(row))

driver.close()
