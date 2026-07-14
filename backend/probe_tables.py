"""Probe PDF table extraction against Neo4j chunks."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_neo4j import Neo4jGraph

from src.ingest_manifest import load_ingest_manifest
from src.pdf_table_parser import extract_table_from_text

load_dotenv()

FILE = sys.argv[1] if len(sys.argv) > 1 else "mork-borg.pdf"
GAME = "mork-borg"

graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"),
    username=os.getenv("NEO4J_USERNAME", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "69696969"),
    database=os.getenv("NEO4J_DATABASE", "morkborg"),
)

load_ingest_manifest(GAME)
manifest = load_ingest_manifest(GAME)
specs = manifest.get("lookup_tables") or []
results: list[str] = []

rows = graph.query(
    """
    MATCH (c:Chunk)-[:PART_OF]->(d:Document {fileName: $file_name})
    RETURN c.page_number AS page, c.text AS text
    ORDER BY c.position
    """,
    {"file_name": FILE},
)

by_page = {r["page"]: r["text"] or "" for r in rows}

# Temporarily treat todo as extractable for probing
for spec in specs:
    name = spec["name"]
    pdf = dict(spec.get("pdf_extract") or {})
    if pdf.get("status") == "hand-authored":
        continue
    pdf["status"] = "verified"
    spec = {**spec, "pdf_extract": pdf}

    found = None
    for page, text in by_page.items():
        table = extract_table_from_text(text, spec, page_number=page)
        if table:
            found = (page, table)
            break
    if found:
        page, table = found
        results.append(f"OK  {name:28} page={page:3} rows={len(table['rows'])}")
    else:
        pages = (spec.get("pdf_extract") or {}).get("prefer_page") or spec.get("pages", "?")
        results.append(f"MISS {name:28} expected~{pages}")

out = Path(__file__).resolve().parent / "probe_tables_result.txt"
out.write_text("\n".join(results) + "\n", encoding="utf-8")
print(out.read_text(encoding="utf-8"))
