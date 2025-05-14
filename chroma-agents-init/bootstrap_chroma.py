
import chromadb
import os
import json
import argparse
from uuid import uuid4

def bootstrap_documents(source_dir: str, chroma_host: str, chroma_port: int, collection_name: str):
    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

    try:
        collection = client.get_or_create_collection(collection_name)
    except Exception as e:
        print(f"[ERROR] Failed to connect or create collection: {e}")
        return

    for file in os.listdir(source_dir):
        if not file.endswith(".json"):
            continue

        with open(os.path.join(source_dir, file), "r") as f:
            doc = json.load(f)

        doc_id = doc.get("id", str(uuid4()))
        content = doc.get("document", "")
        metadata = doc.get("metadata", {})

        collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id]
        )

        print(f"✔️ Inserted {doc_id} into {collection_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap documents into ChromaDB")
    parser.add_argument("--source", required=True, help="Path to directory with .json documents")
    parser.add_argument("--host", default="localhost", help="ChromaDB host (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="ChromaDB port (default: 8000)")
    parser.add_argument("--collection", required=True, help="Collection name to use")

    args = parser.parse_args()

    bootstrap_documents(args.source, args.host, args.port, args.collection)
