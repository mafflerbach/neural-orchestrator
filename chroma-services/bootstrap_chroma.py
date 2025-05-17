
import os
import json
import argparse
from uuid import uuid4
import chromadb

def bootstrap_documents(source_dir, chroma_host, chroma_port, collection_name):
    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

    try:
        collection = client.get_or_create_collection(name=collection_name)
        print(f"✔️ Using collection: {collection.name}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to ChromaDB: {e}")
        return

    for file in os.listdir(source_dir):
        if not file.endswith(".json"):
            continue
        print(f"[DEBUG2] loading File: {f}")


        path = os.path.join(source_dir, file)
        with open(path, "r") as f:
            doc = json.load(f)

        doc_id = doc.get("id", str(uuid4()))
        content = doc.get("document", "")
        metadata = doc.get("metadata", {})

        try:
            collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id]
            )
            print(f"[OK] Inserted {doc_id}")
        except Exception as e:
            print(f"[WARN] Failed to insert doc {doc_id}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--collection", required=True)

    args = parser.parse_args()
    bootstrap_documents(args.source, args.host, args.port, args.collection)
