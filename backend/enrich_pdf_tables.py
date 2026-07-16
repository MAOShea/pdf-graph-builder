"""Materialize manifest lookup tables from PDF → Neo4j (CLI wrapper).

Deprecated one-off scripts (materialize_pdf_tables.py, materialize_weapon_armor.py,
add_npc_location_tables materialize path) delegate here.
"""
import os
import sys

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

from src.graphDB_dataAccess import graphDBdataAccess
from src.table_pipeline import run_lookup_table_pipeline

load_dotenv()


def main():
    file_name = sys.argv[1] if len(sys.argv) > 1 else "mork-borg.pdf"
    pdf_path = sys.argv[2] if len(sys.argv) > 2 else None
    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE", "morkborg"),
    )
    scaffold_map = graphDBdataAccess(graph).fetch_scaffold_node_map()
    stats = run_lookup_table_pipeline(
        graph,
        file_name,
        scaffold_map,
        pdf_path=pdf_path,
    )
    print("lookup_table_pipeline:", stats)

    rows = graph.query(
        """
        MATCH (t:IngestNode)-[:HAS_ENTRY]->(r:TableEntry)
        WITH t, count(DISTINCT r) AS rows
        RETURN t.name AS table, rows
        ORDER BY table
        """
    )
    print("materialized_tables:", rows)


if __name__ == "__main__":
    main()
