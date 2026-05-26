#!/usr/bin/env python3
"""
Script 3 — Insert a simulation and verify Automated Embedding + vector search.

Demonstrates:
  - Inserting a new simulation (embeddings are generated automatically)
  - Checking whether an embedding exists in the internal store
  - Running a sample auto-embedding vector search query

Usage:
  python script_03_insert_and_search.py
  python script_03_insert_and_search.py --query "hypersonic heat shield re-entry"
"""

from __future__ import annotations

import argparse
import sys
import uuid

from pymongo import MongoClient

from config import (
    DATABASE_NAME,
    EMBEDDING_MODEL,
    VECTOR_INDEX_NAME,
    validate_mongodb_config,
    validate_voyage_key_present,
)
from embeddings import has_embedding, vector_search, wait_for_embedding
from sample_data import new_simulation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Insert a simulation, verify auto-embedding, and run vector search."
    )
    parser.add_argument(
        "--version",
        choices=["v1", "v2"],
        default=None,
        help="Schema version (default: SCHEMA_VERSION from .env)",
    )
    parser.add_argument(
        "--query",
        default="Which simulation models hypersonic re-entry and heat shield ablation?",
        help="Natural-language query for the vector search demo",
    )
    parser.add_argument(
        "--embedding-timeout",
        type=int,
        default=120,
        help="Seconds to wait for embedding generation after insert",
    )
    return parser.parse_args()


def _display_name(doc: dict) -> str:
    return doc.get("name") or doc.get("data", {}).get("name", "<unknown>")


def _display_description(doc: dict) -> str:
    return doc.get("description") or doc.get("data", {}).get("description", "")


def main() -> int:
    from config import MONGODB_URI, schema_settings

    args = parse_args()
    validate_mongodb_config()
    validate_voyage_key_present()

    settings = schema_settings(args.version)
    collection_name = settings["collection"]
    embed_path = settings["embed_path"]

    client = MongoClient(MONGODB_URI)
    collection = client[DATABASE_NAME][collection_name]

    sim_id = f"SIM-NEW-{uuid.uuid4().hex[:8].upper()}"
    document = new_simulation(settings["version"], simulation_id=sim_id)

    print(f"Inserting simulation {sim_id} into {DATABASE_NAME}.{collection_name}...")
    insert_result = collection.insert_one(document)
    doc_id = insert_result.inserted_id
    print(f"Inserted _id={doc_id}")

    print(f"Waiting up to {args.embedding_timeout}s for auto-generated embedding...")
    ready = wait_for_embedding(
        client,
        DATABASE_NAME,
        collection_name,
        VECTOR_INDEX_NAME,
        embed_path,
        doc_id,
        timeout_seconds=args.embedding_timeout,
    )

    if ready:
        print("Embedding found in generated-embeddings collection.")
    else:
        print(
            "Embedding not found yet. The index may still be building or rate-limited. "
            "Vector search may still work if initial sync completed for other documents."
        )

    exists = has_embedding(
        client,
        DATABASE_NAME,
        collection_name,
        VECTOR_INDEX_NAME,
        embed_path,
        doc_id,
    )
    print(f"has_embedding() => {exists}")

    print(f"\nRunning vector search: {args.query!r}")
    results = vector_search(
        collection,
        index_name=VECTOR_INDEX_NAME,
        embed_path=embed_path,
        query_text=args.query,
        embedding_model=EMBEDDING_MODEL,
        limit=5,
    )

    if not results:
        print("No results returned. Ensure script 2 created the index and it is READY.")
        return 1

    print(f"Top {len(results)} matches:")
    for rank, hit in enumerate(results, start=1):
        full_doc = collection.find_one({"_id": hit["_id"]})
        name = _display_name(full_doc or {})
        description = _display_description(full_doc or {})
        snippet = description[:120] + ("..." if len(description) > 120 else "")
        print(f"  {rank}. score={hit['score']:.4f}  {name}")
        print(f"     {snippet}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
