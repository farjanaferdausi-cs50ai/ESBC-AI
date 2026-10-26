"""Hybrid retrieval: dense Gemini embeddings (Chroma) plus BM25, fused with reciprocal rank fusion."""
import re
import sys
from functools import lru_cache

import chromadb
from rank_bm25 import BM25Okapi

from app.config import CHROMA_DIR, COLLECTION
from app.embeddings import embed

TOKEN_RE = re.compile(r"[^\s\u0964,.;:!?()\[\]{}\"'/\\|-]+")
RRF_K = 60


def tokenize(text):
    return TOKEN_RE.findall(text.lower())


def _client():
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


@lru_cache(maxsize=1)
def _state():
    col = _client().get_collection(COLLECTION)
    data = col.get(include=["documents", "metadatas"])
    ids, docs, metas = data["ids"], data["documents"], data["metadatas"]
    bm25 = BM25Okapi(
        [tokenize(f"{d} {(m or {}).get('keywords', '')}") or ["_"] for d, m in zip(docs, metas)]
    )
    return col, ids, docs, metas, bm25


def reset_cache():
    _state.cache_clear()


def index_ready():
    try:
        return _client().get_collection(COLLECTION).count() > 0
    except Exception:
        return False


def ensure_index():
    """Build the vector index on a fresh host if it does not exist yet."""
    if index_ready():
        return
    from app.ingest import main as ingest_main

    ingest_main()
    reset_cache()


def knowledge_stats():
    try:
        _, _, _, metas, _ = _state()
    except Exception:
        return {"ready": False, "documents": 0, "chunks": 0, "services": [], "last_checked": None}
    documents = {(m["url"], m["title"]) for m in metas}
    return {
        "ready": True,
        "documents": len(documents),
        "chunks": len(metas),
        "services": sorted({m["service"] for m in metas}),
        "last_checked": max(m["date_checked"] for m in metas),
    }


def search(query, k=5):
    col, ids, docs, metas, bm25 = _state()
    n = len(ids)
    emb = embed([query], "RETRIEVAL_QUERY")
    res = col.query(query_embeddings=emb, n_results=n)
    dense_ids = res["ids"][0]
    dense_score = {i: 1 - d for i, d in zip(dense_ids, res["distances"][0])}
    dense_rank = {i: r for r, i in enumerate(dense_ids)}

    scores = bm25.get_scores(tokenize(query))
    order = sorted(range(n), key=lambda x: scores[x], reverse=True)
    bm_rank = {ids[x]: r for r, x in enumerate(order) if scores[x] > 0}

    fused = {}
    for i in ids:
        value = 1 / (RRF_K + dense_rank[i] + 1) if i in dense_rank else 0.0
        if i in bm_rank:
            value += 1 / (RRF_K + bm_rank[i] + 1)
        fused[i] = value

    by_id = {i: (docs[x], metas[x]) for x, i in enumerate(ids)}
    top = sorted(ids, key=lambda i: fused[i], reverse=True)[:k]
    return [
        {"text": by_id[i][0], "score": round(dense_score.get(i, 0.0), 3), **by_id[i][1]}
        for i in top
    ]


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "death certificate documents"
    for h in search(q):
        print(f"[{h['score']}] {h['service']} | {h['title']} | {h['date_checked']}")
        print(f"    {h['url']}")
        print(f"    {h['text'][:150]}...\n")
