"""Dump chunk text around table headers for debugging."""
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

load_dotenv()

graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"),
    username=os.getenv("NEO4J_USERNAME", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "69696969"),
    database=os.getenv("NEO4J_DATABASE", "morkborg"),
)

PAGES = [46, 56, 69, 72, 43]
PATTERNS = [
    "Optional Classes",
    "raised in",
    "Adventure spark",
    "Imminent danger",
    "Arcane catastrophes",
]

rows = graph.query(
    """
    MATCH (c:Chunk)-[:PART_OF]->(d:Document {fileName: $file_name})
    WHERE c.page_number IN $pages
    RETURN c.page_number AS page, c.text AS text
    ORDER BY c.page_number
    """,
    {"pages": PAGES, "file_name": "mork-borg.pdf"},
)

out = []
for r in rows:
    text = r["text"] or ""
    out.append(f"\n===== PAGE {r['page']} (len={len(text)}) =====")
    for pat in PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 800)
            snippet = text[start:end].replace("\n", " ")
            out.append(f"\n-- match {pat!r} --\n{snippet}")

Path(__file__).resolve().parent.joinpath("page_snippets.txt").write_text(
    "\n".join(out), encoding="utf-8"
)
print("wrote page_snippets.txt")
