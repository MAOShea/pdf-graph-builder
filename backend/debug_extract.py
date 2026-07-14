from pathlib import Path

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

from src.ingest_manifest import load_ingest_manifest, spec_by_name
from src.pdf_table_parser import (
    _find_header,
    _index_keys,
    _parse_rows_sequential,
    _slice_body,
    extract_table_from_text,
)

load_dotenv()
m = load_ingest_manifest()
g = Neo4jGraph(
    url="neo4j://127.0.0.1:7687",
    username="neo4j",
    password="69696969",
    database="morkborg",
)

cases = [
    ("ImminentDangerTable", 72, "page_72.txt"),
    ("OptionalClassesTable", 46, "page_46.txt"),
    ("RaisedInTable", 56, None),
    ("AdventureSparkTable", 69, "page_69.txt"),
    ("ArcaneCatastrophesTable", 43, "page_43.txt"),
]

for name, page, f in cases:
    spec = dict(spec_by_name(m, name))
    pe = dict(spec["pdf_extract"])
    pe["status"] = "verified"
    spec["pdf_extract"] = pe
    if f:
        text = Path(f).read_text(encoding="utf-8")
    else:
        text = g.query(
            "MATCH (c:Chunk)-[:PART_OF]->(:Document {fileName: $fn}) "
            "WHERE c.page_number=$p RETURN c.text AS t",
            {"fn": "mork-borg.pdf", "p": page},
        )[0]["t"]
    t = extract_table_from_text(text, spec, page_number=page)
    print(f"{name}: {len(t['rows']) if t else 'MISS'}")
    if not t and name == "RaisedInTable":
        pe = spec["pdf_extract"]
        h = _find_header(text, pe["header_patterns"])
        body = _slice_body(text, h.end(), pe.get("stop_before") or [])
        keys = _index_keys(pe["index"]["type"], pe["index"])
        rows = _parse_rows_sequential(body, keys, pe["index"]["type"])
        print("  header", bool(h), "keys", keys, "raw", len(rows))
        for r in rows:
            print("   ", r)
    if t:
        for r in t["rows"][:3]:
            print(f"  {r[0]}: {str(r[1])[:60]}")
        if len(t["rows"]) > 3:
            print(f"  ... +{len(t['rows'])-3} more")
