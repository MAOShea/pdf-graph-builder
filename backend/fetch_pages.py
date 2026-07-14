from pathlib import Path

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

load_dotenv()
g = Neo4jGraph(
    url="neo4j://127.0.0.1:7687",
    username="neo4j",
    password="69696969",
    database="morkborg",
)
for p in [45, 70]:
    t = g.query(
        "MATCH (c:Chunk)-[:PART_OF]->(:Document {fileName: $fn}) "
        "WHERE c.page_number=$p RETURN c.text AS t",
        {"fn": "mork-borg.pdf", "p": p},
    )[0]["t"]
    Path(f"page_{p}.txt").write_text(t or "", encoding="utf-8")
    print(p, len(t or ""))
