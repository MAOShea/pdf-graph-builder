"""Verify Phase 1 narrow ingest (Briefing 4)."""
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"),
    auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD")),
)
db = os.getenv("NEO4J_DATABASE", "morkborg")

with driver.session(database=db) as s:
    print("=== Counts ===")
    print("SeedNodes:", s.run("MATCH (n:SeedNode) RETURN count(n) AS c").single()["c"])
    print("IngestNodes:", s.run("MATCH (n:IngestNode) RETURN count(n) AS c").single()["c"])
    pages = s.run(
        """
        MATCH (c:Chunk)-[:PART_OF]->(:Document {fileName: $fn})
        RETURN c.page_number AS p ORDER BY p
        """,
        {"fn": "mork-borg.pdf"},
    ).value()
    print("Chunk pages:", pages)

    print("\n=== DRTable ===")
    row = s.run(
        """
        MATCH (t:DRTable:IngestNode)-[:INSTANCE_OF]->(:LookupTable)
        OPTIONAL MATCH (t)-[:HAS_ENTRY]->(r:TableEntry)
        OPTIONAL MATCH (t)-[:APPLIES_TO]->(dr)
        RETURN t.name AS table, count(r) AS rows, dr.name AS applies_to
        """
    ).single()
    print(dict(row) if row else "MISSING")

    print("\n=== AbilityTest ===")
    for r in s.run(
        """
        MATCH (at:AbilityTest)
        OPTIONAL MATCH (at)-[:USES]->(t)
        OPTIONAL MATCH (at)-[:DOCUMENTED_BY]->(rp:RulePassage)
        RETURN at.name AS name, t.name AS uses, count(rp) AS passages
        """
    ):
        print(dict(r))

    print("\n=== Tables with rows ===")
    for r in s.run(
        """
        MATCH (t:IngestNode)-[:INSTANCE_OF]->(:LookupTable)
        WHERE (t)-[:HAS_ENTRY]->()
        MATCH (t)-[:HAS_ENTRY]->(row:TableEntry)
        RETURN t.name AS table, count(row) AS rows ORDER BY table
        """
    ):
        print(dict(r))

driver.close()
