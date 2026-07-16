#!/usr/bin/env python3
"""Upload and extract a PDF via the backend API (no curl).

Requires the backend running (e.g. .\\start.ps1) and Neo4j credentials in backend/.env.

Examples (from workspace root):
  backend\\venv\\Scripts\\python.exe backend\\ingest_pdf.py mork-borg.pdf --ingest-mode scaffold-diff --cleanup
  backend\\venv\\Scripts\\python.exe backend\\ingest_pdf.py mork-borg.pdf --start-page 27 --end-page 31 --ingest-mode scaffold-diff --cleanup
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from neo4j import GraphDatabase

_BACKEND = Path(__file__).resolve().parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from src.ingest_cleanup import cleanup_ingest_driver

load_dotenv()


def _cleanup_neo4j(
    uri: str,
    user: str,
    password: str,
    database: str,
    *,
    file_name: str | None = None,
    start_page: int | None = None,
    end_page: int | None = None,
) -> None:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    cleanup_ingest_driver(
        driver,
        database,
        file_name=file_name,
        start_page=start_page,
        end_page=end_page,
    )
    driver.close()
    scope = ""
    if file_name:
        if start_page or end_page:
            scope = f" for {file_name} pages {start_page or '…'}-{end_page or '…'}"
        else:
            scope = f" for {file_name} (document + chunks)"
    print(f"cleanup: ingest data cleared{scope} (scaffold preserved)")


def _upload(client: httpx.Client, pdf_path: Path, file_name: str, model: str, creds: dict) -> dict:
    with pdf_path.open("rb") as handle:
        response = client.post(
            "/upload",
            data={
                "chunkNumber": "1",
                "totalChunks": "1",
                "originalname": file_name,
                "model": model,
                **creds,
            },
            files={"file": (file_name, handle, "application/pdf")},
            timeout=None,
        )
    response.raise_for_status()
    body = response.json()
    if body.get("status") != "Success":
        raise RuntimeError(f"upload failed: {body}")
    return body


def _extract(client: httpx.Client, file_name: str, model: str, creds: dict, opts: dict) -> dict:
    data = {
        "file_name": file_name,
        "source_type": "local file",
        "model": model,
        **creds,
        **{k: v for k, v in opts.items() if v is not None and v != ""},
    }
    response = client.post("/extract", data=data, timeout=None)
    response.raise_for_status()
    body = response.json()
    if body.get("status") != "Success":
        raise RuntimeError(f"extract failed: {body}")
    return body


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Ingest a PDF via backend upload + extract (no curl)")
    parser.add_argument("pdf", type=Path, help="Path to PDF file")
    parser.add_argument("--backend-url", default=os.getenv("BACKEND_URL", "http://localhost:8000"))
    parser.add_argument("--file-name", help="Document fileName in Neo4j (default: PDF basename)")
    parser.add_argument("--model", default=os.getenv("INGEST_MODEL", "ollama_llama3"))
    parser.add_argument("--uri", default=os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"))
    parser.add_argument("--user", default=os.getenv("NEO4J_USERNAME", "neo4j"))
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD"))
    parser.add_argument("--database", default=os.getenv("NEO4J_DATABASE", "morkborg"))
    parser.add_argument("--ingest-mode", default="scaffold-diff")
    parser.add_argument("--start-page", type=int, default=None, help="First PDF page (1-based, inclusive)")
    parser.add_argument("--end-page", type=int, default=None, help="Last PDF page (1-based, inclusive)")
    parser.add_argument("--token-chunk-size", type=int, default=512)
    parser.add_argument("--chunk-overlap", type=int, default=100)
    parser.add_argument("--chunks-to-combine", type=int, default=1)
    parser.add_argument("--allowed-nodes", default=None)
    parser.add_argument("--allowed-relationship", default=None)
    parser.add_argument("--additional-instructions", default=None)
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clear ingest nodes, flags, and document chunks before upload (keeps scaffold)",
    )
    args = parser.parse_args()

    pdf_path = args.pdf if args.pdf.is_absolute() else root / args.pdf
    if not pdf_path.is_file():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    if not args.password:
        print("NEO4J_PASSWORD not set (env or --password)", file=sys.stderr)
        sys.exit(1)

    file_name = args.file_name or pdf_path.name
    creds = {
        "uri": args.uri,
        "userName": args.user,
        "password": args.password,
        "database": args.database,
    }

    if args.cleanup:
        _cleanup_neo4j(
            args.uri,
            args.user,
            args.password,
            args.database,
            file_name=file_name,
            start_page=args.start_page,
            end_page=args.end_page,
        )

    extract_opts = {
        "ingest_mode": args.ingest_mode,
        "start_page": args.start_page,
        "end_page": args.end_page,
        "token_chunk_size": args.token_chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "chunks_to_combine": args.chunks_to_combine,
        "allowedNodes": args.allowed_nodes,
        "allowedRelationship": args.allowed_relationship,
        "additional_instructions": args.additional_instructions,
    }

    page_note = ""
    if args.start_page or args.end_page:
        page_note = f" pages {args.start_page or '…'}-{args.end_page or '…'}"

    print(f"ingest_pdf: {pdf_path.name}{page_note} -> {args.backend_url} ({args.database})")

    with httpx.Client(base_url=args.backend_url.rstrip("/")) as client:
        upload_body = _upload(client, pdf_path, file_name, args.model, creds)
        print("upload:", json.dumps(upload_body.get("data") or upload_body, indent=2)[:500])

        extract_body = _extract(client, file_name, args.model, creds, extract_opts)
        data = extract_body.get("data") or {}
        print(
            "extract:",
            f"nodes={data.get('nodeCount')} rels={data.get('relationshipCount')} "
            f"chunks={data.get('chunkNodeCount') or data.get('total_chunks')}",
        )
        if data.get("table_materialization"):
            print("table_materialization:", data["table_materialization"])


if __name__ == "__main__":
    main()
