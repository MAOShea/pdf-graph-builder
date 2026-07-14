"""One-off: parse PDF tables from existing chunks and materialize DRTable.

Use when the graph already has PDF chunks but predates pdf_table_parser.
Does not re-run LLM extraction.
"""
import os
import sys

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_neo4j import Neo4jGraph

from src.graphDB_dataAccess import graphDBdataAccess
from src.pdf_table_parser import enrich_pdf_chunks_with_tables, persist_chunk_table_metadata
from src.table_materialization import materialize_lookup_tables_from_chunks

load_dotenv()


def main():
    file_name = sys.argv[1] if len(sys.argv) > 1 else "mork-borg.pdf"
    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE", "morkborg"),
    )
    gdb = graphDBdataAccess(graph)
    scaffold_map = gdb.fetch_scaffold_node_map()

    rows = graph.query(
        """
        MATCH (c:Chunk)-[:PART_OF]->(d:Document {fileName: $file_name})
        RETURN c.id AS chunk_id, c.text AS text, c.page_number AS page_number
        ORDER BY c.position
        """,
        {"file_name": file_name},
    )
    chunk_list = [
        {
            "chunk_id": r["chunk_id"],
            "chunk_doc": Document(
                page_content=r["text"] or "",
                metadata={"page_number": r["page_number"]},
            ),
        }
        for r in rows
    ]

    pdf_stats = enrich_pdf_chunks_with_tables(chunk_list)
    persisted = persist_chunk_table_metadata(graph, chunk_list)
    mat_stats = materialize_lookup_tables_from_chunks(
        graph, file_name, chunk_list, scaffold_map
    )

    print("pdf_table_parser:", pdf_stats)
    print("persisted_chunks:", persisted)
    print("materialization:", mat_stats)

    verify = graph.query(
        """
        MATCH (t:DRTable:IngestNode)
        OPTIONAL MATCH (t)-[:HAS_COLUMN]->(col:TableColumn)
        OPTIONAL MATCH (t)-[:HAS_ENTRY]->(row:TableEntry)
        RETURN t.name, collect(DISTINCT col.column_name) AS cols, count(DISTINCT row) AS rows
        """
    )
    print("dr_table:", verify)


if __name__ == "__main__":
    main()
