"""Clear ingest-created Neo4j data while preserving the bootstrap scaffold."""

from __future__ import annotations

from neo4j import Driver, Session

from src.shared.constants import INGEST_REL_TYPES


def ingest_rel_delete_cypher() -> str:
    rel_types = "|".join(sorted(INGEST_REL_TYPES))
    return f"MATCH ()-[r:{rel_types}]->() DELETE r"


def cleanup_ingest_graph(
    session: Session,
    *,
    file_name: str | None = None,
    start_page: int | None = None,
    end_page: int | None = None,
) -> None:
    """Remove ingest nodes, flags, and document chunks; keep scaffold seed nodes."""
    session.run(ingest_rel_delete_cypher())
    session.run("MATCH (n:IngestNode) DETACH DELETE n")
    session.run("MATCH (n:FlaggedRelationship) DETACH DELETE n")
    session.run("MATCH (n:FlaggedConcept) DETACH DELETE n")
    session.run("MATCH (n:RulePassage) DETACH DELETE n")

    if not file_name:
        return

    page_filter = bool(start_page or end_page)
    if page_filter:
        session.run(
            """
            MATCH (d:Document {fileName: $file_name})<-[:PART_OF|FIRST_CHUNK]-(c:Chunk)
            WHERE c.page_number >= coalesce($start_page, c.page_number)
              AND c.page_number <= coalesce($end_page, c.page_number)
            DETACH DELETE c
            """,
            {
                "file_name": file_name,
                "start_page": start_page,
                "end_page": end_page,
            },
        )
    else:
        session.run(
            """
            MATCH (d:Document {fileName: $file_name})
            OPTIONAL MATCH (d)<-[:PART_OF|FIRST_CHUNK]-(c:Chunk)
            DETACH DELETE c, d
            """,
            {"file_name": file_name},
        )


def cleanup_ingest_driver(
    driver: Driver,
    database: str,
    *,
    file_name: str | None = None,
    start_page: int | None = None,
    end_page: int | None = None,
) -> None:
    with driver.session(database=database) as session:
        cleanup_ingest_graph(
            session,
            file_name=file_name,
            start_page=start_page,
            end_page=end_page,
        )
