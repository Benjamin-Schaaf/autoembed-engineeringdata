#!/usr/bin/env python3
"""
Script 1 — Load sample simulation data into MongoDB.

Two schema layouts are supported:
  v1  Flat documents (fields at the root level)
  v2  All simulation fields nested under a top-level ``data`` object

Usage:
  python script_01_create_sample_data.py --version v1
  python script_01_create_sample_data.py --version v2
  python script_01_create_sample_data.py --version v1 --drop
"""

from __future__ import annotations

import argparse
import sys

from pymongo import MongoClient

from config import validate_mongodb_config
from sample_data import sample_simulations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load sample simulation data into MongoDB.")
    parser.add_argument(
        "--version",
        choices=["v1", "v2"],
        default=None,
        help="Schema version (default: SCHEMA_VERSION from .env)",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop the target collection before inserting sample data",
    )
    return parser.parse_args()


def main() -> int:
    from config import DATABASE_NAME, MONGODB_URI, schema_settings

    args = parse_args()
    validate_mongodb_config()

    settings = schema_settings(args.version)
    version = settings["version"]
    collection_name = settings["collection"]

    documents = sample_simulations(version)
    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    collection = db[collection_name]

    if args.drop:
        collection.drop()
        print(f"Dropped collection {db.name}.{collection_name}")

    result = collection.insert_many(documents)
    print(f"Inserted {len(result.inserted_ids)} documents into {db.name}.{collection_name}")
    print(f"Schema version: {version}")
    print(f"Auto-embed text field path: {settings['embed_path']}")

    for doc_id, doc in zip(result.inserted_ids, documents, strict=True):
        sim_id = doc.get("simulation_id") or doc.get("data", {}).get("simulation_id")
        name = doc.get("name") or doc.get("data", {}).get("name")
        print(f"  - {sim_id}: {name} (_id={doc_id})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
