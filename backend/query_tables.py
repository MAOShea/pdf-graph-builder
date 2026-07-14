"""One-off: list materialized lookup tables in Neo4j."""
from neo4j import GraphDatabase

URI = "neo4j://127.0.0.1:7687"
AUTH = ("neo4j", "69696969")
DB = "morkborg"

driver = GraphDatabase.driver(URI, auth=AUTH)

with driver.session(database=DB) as s:
    print("=== Materialized lookup tables ===")
    rows = s.run(
        """
        MATCH (t:IngestNode)-[:INSTANCE_OF]->(:LookupTable)
        WHERE (t)-[:HAS_ENTRY]->()
        OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:TableColumn)
        OPTIONAL MATCH (t)-[:HAS_ENTRY]->(r:TableEntry)
        RETURN labels(t) AS labels, t.name AS name,
               count(DISTINCT c) AS columns, count(DISTINCT r) AS row_count
        ORDER BY name
        """
    )
    for rec in rows:
        skip = {"IngestNode", "LookupTable", "TableColumn", "TableEntry"}
        extra = [l for l in rec["labels"] if l not in skip]
        tag = next((l for l in extra if "Table" in l or l == "DR"), extra[0] if extra else "?")
        print(f"  {tag:24} rows={rec['row_count']:3}  cols={rec['columns']}")

    print("\n=== All rows (ordered) ===")
    current = None
    for rec in s.run(
        """
        MATCH (t:IngestNode)-[:INSTANCE_OF]->(:LookupTable)
        WHERE (t)-[:HAS_ENTRY]->()
        MATCH (t)-[:HAS_ENTRY]->(r:TableEntry)
        WITH t, r ORDER BY t.name, r.name
        RETURN t.name AS table, r.name AS row_name, r.cells AS cells
        """
    ):
        if rec["table"] != current:
            current = rec["table"]
            print(f"\n{current}")
        print(f"  {rec['row_name']}: {rec['cells']}")

driver.close()
