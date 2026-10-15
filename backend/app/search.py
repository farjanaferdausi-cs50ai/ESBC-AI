"""Semantic search over the knowledge base (used for testing now, by the agent later)."""
import sys
from functools import lru_cache

import chromadb

from app.config import CHROMA_DIR, COLLECTION
from app.embeddings import embed


@lru_cache(maxsize=1)
def _collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION)


def search(query, k=5, service=None):
    emb = embed([query], "RETRIEVAL_QUERY")
    res = _collection().query(
        query_embeddings=emb,
        n_results=k,
        where={"service": service} if service else None,
    )
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        hits.append({"text": doc, "score": round(1 - dist, 3), **meta})
    return hits


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "death certificate documents"
    for h in search(q):
        print(f"[{h['score']}] {h['service']} | {h['title']} | {h['date_checked']}")
        print(f"    {h['url']}")
        print(f"    {h['text'][:150]}...\n")