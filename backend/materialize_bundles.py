"""One-off: run pass-2 bundle wiring without re-parsing PDF tables."""
import os
import sys

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

from src.bundle_materialization import materialize_character_creation_bundles
from src.graphDB_dataAccess import graphDBdataAccess

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
    stats = materialize_character_creation_bundles(graph, file_name, scaffold_map)
    print("bundle_materialization:", stats)

    verify = graph.query(
        """
        MATCH (b:OptionalClass:IngestNode)
        OPTIONAL MATCH (b)-[:CONTAINS]->(t:IngestNode)
        RETURN b.id AS bundle, collect(t.name) AS nested
        ORDER BY bundle
        """
    )
    print("bundles:", verify)


if __name__ == "__main__":
    main()
