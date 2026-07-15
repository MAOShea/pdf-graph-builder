"""Probe missing table headers on ingested chunk text."""
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

from src.ingest_manifest import load_ingest_manifest, spec_by_name
from src.pdf_table_parser import extract_table_from_text

load_dotenv()
g = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE", "morkborg"),
)
m = load_ingest_manifest()

for page in (53, 54):
    rows = g.query(
        "MATCH (c:Chunk)-[:PART_OF]->(:Document {fileName: 'mork-borg.pdf'}) "
        "WHERE c.page_number=$p RETURN c.text AS t",
        {"p": page},
    )
    text = rows[0]["t"] if rows else ""
    Path(f"page_{page}.txt").write_text(text, encoding="utf-8")
    print(f"=== page {page} len={len(text)} ===")
    print(text[:800])
    print()

for name in ("WretchedRoyaltyEquipmentTable", "HereticalPriestOriginsTable"):
    spec = dict(spec_by_name(m, name))
    pe = dict(spec.get("pdf_extract") or {})
    if not pe:
        # trial headers
        page = int(str(spec.get("pages", "0")).split("-")[0])
        text = Path(f"page_{page}.txt").read_text(encoding="utf-8")
        for hdr in [
            r"begin with two of the following\s*\(d6\)",
            r"You begin with two of the following\s*\(d6\)",
            r"Where.*\(d6\)",
            r"ORIGINS\s*\(d6\)",
            r"origins\s*\(d6\)",
            r"Heretical priest",
        ]:
            trial = {
                **spec,
                "pdf_extract": {
                    "status": "verified",
                    "header_patterns": [hdr],
                    "index": {"type": "d6"},
                    "min_rows": 6,
                    "max_rows": 6,
                },
            }
            t = extract_table_from_text(text, trial)
            if t:
                print(name, "OK hdr=", hdr, "rows=", len(t["rows"]))
                break
        else:
            print(name, "no hdr matched")
    else:
        t = extract_table_from_text(
            Path(f"page_{int(str(spec.get('pages')).split('-')[0])}.txt").read_text(encoding="utf-8"),
            spec,
        )
        print(name, len(t["rows"]) if t else "MISS")
