"""Hybrid retrieval: dense Gemini embeddings (Chroma) plus BM25, fused with reciprocal rank fusion."""
import re
import sys
from functools import lru_cache
import chromadb
from rank_bm25 import BM25Okapi

from app.config import CHROMA_DIR, COLLECTION

TOKEN_RE = re.compile(r"[^\s\u0964,.;:!?()\[\]{}\"'/\\|-]+")


def tokenize(text):
    return TOKEN_RE.findall(text.lower())


def _client():
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


@lru_cache(maxsize=1)
def _state():
    col = _client().get_collection(COLLECTION)
    data = col.get(include=["documents", "metadatas"])
    bm25 = BM25Okapi([tokenize(d) or ["_"] for d in docs])
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
    }


def search(query, k=5):
    col, ids, docs, metas, bm25 = _state()
    n = len(ids)
    emb = embed([query], "RETRIEVAL_QUERY")
    res = col.query(query_embeddings=emb, n_results=n)
    dense_score = {i: 1 - d for i, d in zip(dense_ids, res["distances"][0])}
    dense_rank = {i: r for r, i in enumerate(dense_ids)}

    scores = bm25.get_scores(tokenize(query))
    order = sorted(range(n), key=lambda x: scores[x], reverse=True)
    bm_rank = {ids[x]: r for r, x in enumerate(order) if scores[x] > 0}
    fused = {}
    for i in ids:
        if i in bm_rank:
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

cat > backend/app/agent.py << 'EOF'
import re
import sys
import time
from typing import List, TypedDict

from dotenv import load_dotenv
from google.genai import types
from langgraph.graph import END, START, StateGraph

from app.config import ENV_PATH, GEN_MODEL, SCORE_THRESHOLD, TOP_K
from app.search import search

load_dotenv(ENV_PATH)

FALLBACK = {
    "en": (
        "I'm not sure about this based on the official sources I have. "
    ),
    "bn": (
        "আমি এ বিষয়ে নিশ্চিত নই। অনুগ্রহ করে সংশ্লিষ্ট অফিসিয়াল সরকারি পোর্টাল "
        "দেখুন অথবা স্থানীয় অফিসে যোগাযোগ করুন।"
}

SYSTEM_PROMPT = """You are ESBC-AI, an assistant that explains Bangladeshi government services.
Rules:
1. Answer ONLY from the numbered context below. Never use outside knowledge.
2. If the context does not contain the answer, say you are not sure. Never guess fees, deadlines or requirements.
4. Cite sources inline like [1] or [2] after the facts they support. Only use numbers that exist in the context.
5. Be clear and practical. Use short numbered steps for procedures.
6. If a figure comes from an older notice, say which year or date the context gives for it.
7. If the context mentions a closure, maintenance or deadline with dates that affects the answer, mention it clearly.
{plain_rule}"""

PLAIN_RULE = (
    "9. PLAIN MODE: use very simple words and very short sentences, "
    "as if explaining to someone with little formal education."


class State(TypedDict, total=False):
    question: str
    plain: bool
    language: str
    hits: List[dict]
    confident: bool
    sources: List[dict]


    text = state["question"]
    bn = len(re.findall(r"[\u0980-\u09FF]", text))
    letters = len(re.findall(r"[A-Za-z\u0980-\u09FF]", text)) or 1
    return {"language": "bn" if bn / letters > 0.3 else "en"}


def retrieve(state: State) -> State:


def gate(state: State) -> State:
    hits = state.get("hits", [])
    best = max((h["score"] for h in hits), default=0.0)
    return {"confident": best >= SCORE_THRESHOLD}


def route(state: State) -> str:
    return "generate" if state["confident"] else "fallback"


def _call_model(system: str, user: str) -> str:
    for attempt in range(4):
        try:
            res = get_client().models.generate_content(
                model=GEN_MODEL,
                contents=user,
            )
            return (res.text or "").strip()
        except Exception as exc:
            if attempt == 3:
                raise
            time.sleep(4 * (attempt + 1))
            print(f"Generation retry ({exc})")
    return ""


def generate(state: State) -> State:
    hits = [h for h in state["hits"] if h["score"] >= SCORE_THRESHOLD * 0.8]
    groups = {}
    for h in hits:
        key = (h["url"], h["title"])
        group["texts"].append(h["text"])
        group["best"] = max(group["best"], h["score"])

    context = "\n\n".join(
        f"[{i}] ({g['meta']['title']} | {g['meta']['url']} | checked {g['meta']['date_checked']})\n"
        for i, g in enumerate(ordered, 1)
    )
    system = SYSTEM_PROMPT.format(
        lang_name="Bangla (Bengali script)" if state["language"] == "bn" else "English",
        plain_rule=PLAIN_RULE if state.get("plain") else "",
    )
    user = f"Context:\n{context}\n\nQuestion: {state['question']}"
    answer = _call_model(system, user) or FALLBACK[state["language"]]
    sources = [
        {
            "id": i,
            "title": g["meta"]["title"],
            "url": g["meta"]["url"],
            "date_checked": g["meta"]["date_checked"],
            "service": g["meta"]["service"],
            "score": g["best"],
        for i, g in enumerate(ordered, 1)
    ]
    return {"answer": answer, "sources": sources}


def fallback(state: State) -> State:
    return {"answer": FALLBACK[state["language"]], "sources": []}


def build_graph():
    g = StateGraph(State)
    g.add_node("detect_language", detect_language)
    g.add_node("gate", gate)
    g.add_node("generate", generate)
    g.add_node("fallback", fallback)
    g.add_edge(START, "detect_language")
    g.add_edge("retrieve", "gate")
    g.add_conditional_edges("gate", route, {"generate": "generate", "fallback": "fallback"})
    g.add_edge("fallback", END)
    return g.compile()


_graph = None


def ask(question: str, plain: bool = False) -> dict:
    global _graph
    if _graph is None:
        _graph = build_graph()
    hits = out.get("hits", [])
    return {
        "answer": out["answer"],
        "language": out["language"],
        "confident": out["confident"],
        "sources": out.get("sources", []),
        "top_score": max((h["score"] for h in hits), default=None),
    }


if __name__ == "__main__":
    result = ask(" ".join(sys.argv[1:]) or "What documents are needed for death registration?")
    print(f"[lang={result['language']} confident={result['confident']} top={result['top_score']}]")
    print(result["answer"])
    for s in result["sources"]:
        print(f"  [{s['id']}] {s['title']} - {s['url']} ({s['date_checked']})")
