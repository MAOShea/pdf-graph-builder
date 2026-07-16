import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
d = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
)
db = os.getenv("NEO4J_DATABASE", "morkborg")
with d.session(database=db) as s:
    print("bundle sample:", s.run("MATCH (b:OptionalClass:IngestNode) RETURN b.id, labels(b) LIMIT 1").data())
    print("selector:", s.run("MATCH (t:OptionalClassesTable) RETURN labels(t) LIMIT 1").data())
    print(
        "chunk->table:",
        s.run(
            """
            MATCH (c:Chunk)-[:DOCUMENTED_BY]->(t:IngestNode)
            WHERE c.page_number >= 46 AND c.page_number <= 57
            RETURN t.name, count(c) AS chunks ORDER BY t.name
            """
        ).data(),
    )
d.close()
