import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

load_dotenv()
graph = Neo4jGraph(
    url="neo4j://127.0.0.1:7687",
    username="neo4j",
    password="69696969",
    database="morkborg",
)
for page in [44, 47, 48, 70, 56]:
    r = graph.query(
        "MATCH (c:Chunk)-[:PART_OF]->(:Document {fileName:'mork-borg.pdf'}) "
        "WHERE c.page_number=$p RETURN c.text AS t",
        {"p": page},
    )[0]["t"]
    Path(f"page_{page}.txt").write_text(r or "", encoding="utf-8")
    print(page, len(r or ""))
