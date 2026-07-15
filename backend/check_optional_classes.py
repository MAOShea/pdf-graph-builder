"""Check Optional Classes / bundle content in Neo4j."""
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
    r = s.run(
        """
        MATCH (c:Chunk)-[:PART_OF]->(:Document {fileName: 'mork-borg.pdf'})
        RETURN count(c) AS chunks, min(c.page_number) AS min_p, max(c.page_number) AS max_p,
               collect(DISTINCT c.page_number) AS pages
        """
    ).single()
    print("Chunks:", dict(r))

    print("\nLookup tables:")
    for row in s.run(
        """
        MATCH (t:IngestNode)-[:INSTANCE_OF]->(:LookupTable)
        WHERE (t)-[:HAS_ENTRY]->()
        MATCH (t)-[:HAS_ENTRY]->(r:TableEntry)
        RETURN t.name AS table, count(r) AS rows ORDER BY table
        """
    ):
        print(f"  {row['table']}: {row['rows']}")

    oc_tables = [
        "OptionalClassesTable",
        "EarliestMemoriesTable",
        "BadBirthTable",
        "EldritchOriginsTable",
        "RaisedInTable",
        "HerbmasterDecoctionsTable",
    ]
    print("\nOptional-class tables present?")
    for name in oc_tables:
        c = s.run(
            "MATCH (t:IngestNode {name: $n}) RETURN count(t) AS c", {"n": name}
        ).single()["c"]
        print(f"  {name}: {'yes' if c else 'no'}")

    print("\nBundle relationships:")
    for row in s.run(
        """
        OPTIONAL MATCH ()-[s:SELECTS]->()
        OPTIONAL MATCH ()-[c:CONTAINS]->()
        RETURN count(s) AS selects, count(c) AS contains
        """
    ):
        print(dict(row))

    print("\nOptionalClass bundles:")
    for row in s.run(
        "MATCH (b) WHERE 'OptionalClass' IN labels(b) RETURN b.name AS name LIMIT 10"
    ):
        print(f"  {row['name']}")

driver.close()
