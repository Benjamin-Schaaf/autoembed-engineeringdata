#!/usr/bin/env python3
"""
Script 2 — Create a MongoDB Vector Search index with Automated Embedding (autoEmbed).

This enables Atlas to automatically generate Voyage AI embeddings for the
simulation description field at index-time and query-time.

Prerequisite: Configure your Voyage AI API key in Atlas under Model API Keys.

Usage:
  python script_02_create_auto_embed_index.py
  python script_02_create_auto_embed_index.py --version v2
"""

from __future__ import annotations

import argparse
import sys

from pymongo import MongoClient
from pymongo.operations import SearchIndexModel

from config import (
    DATABASE_NAME,
    EMBEDDING_MODEL,
    MONGODB_URI,
    VECTOR_INDEX_NAME,
    validate_mongodb_config,
    validate_voyage_key_present,
)
from embeddings import wait_for_search_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an autoEmbed Vector Search index for simulation descriptions."
    )
    parser.add_argument(
        "--version",
        choices=["v1", "v2"],
        default=None,
        help="Schema version (default: SCHEMA_VERSION from .env)",
    )
    parser.add_argument(
        "--skip-wait",
        action="store_true",
        help="Create the index but do not wait for READY status",
    )
    return parser.parse_args()


def main() -> int:
    from config import schema_settings

    args = parse_args()
    validate_mongodb_config()
    validate_voyage_key_present()

    settings = schema_settings(args.version)
    embed_path = settings["embed_path"]
    collection_name = settings["collection"]

    index_definition = {
        "fields": [
            {
                "type": "autoEmbed",
                "modality": "text",
                "path": embed_path,
                "model": EMBEDDING_MODEL,
            },
            {
                "type": "filter",
                "path": "simulation_id" if settings["version"] == "v1" else "data.simulation_id",
            },
            {
                "type": "filter",
                "path": "status" if settings["version"] == "v1" else "data.status",
            },
        ]
    }

    client = MongoClient(MONGODB_URI)
    collection = client[DATABASE_NAME][collection_name]

    existing = list(
        collection.aggregate([{"$listSearchIndexes": {"name": VECTOR_INDEX_NAME}}])
    )
    if existing:
        status = existing[0].get("status")
        print(f"Index {VECTOR_INDEX_NAME!r} already exists (status={status}).")
        if status != "READY" and not args.skip_wait:
            print("Waiting for index to become READY...")
            index = wait_for_search_index(collection, VECTOR_INDEX_NAME)
            print(f"Index is READY (id={index['id']}).")
        return 0

    print(f"Creating autoEmbed index {VECTOR_INDEX_NAME!r} on {DATABASE_NAME}.{collection_name}")
    print(f"  embed path : {embed_path}")
    print(f"  model      : {EMBEDDING_MODEL}")

    model = SearchIndexModel(
        definition=index_definition,
        name=VECTOR_INDEX_NAME,
        type="vectorSearch",
    )
    collection.create_search_index(model=model)
    print("Index creation initiated.")

    if args.skip_wait:
        print("Skipping wait (--skip-wait). Check Atlas UI for build progress.")
        return 0

    print("Waiting for index to become READY (initial sync may take several minutes)...")
    index = wait_for_search_index(collection, VECTOR_INDEX_NAME)
    print(f"Index is READY (id={index['id']}, numDocs={index.get('numDocs', 'n/a')}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
