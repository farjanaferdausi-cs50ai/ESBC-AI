"""LangGraph agent: language detection -> retrieval -> confidence gate -> grounded answer."""
import re
import sys
import time
from typing import List, TypedDict

from dotenv import load_dotenv
from google.genai import types
from langgraph.graph import END, START, StateGraph

from app.config import ENV_PATH, GEN_MODEL, SCORE_THRESHOLD, TOP_K
from app.embeddings import _get_client as get_client
from app.search import search

load_dotenv(ENV_PATH)

FALLBACK = {
    "en": (
        "I'm not sure about this based on the official sources I have. "
        "Please check the official government portal or visit your local office."
    ),
    "bn": (
        "আমি এ বিষয়ে নিশ্চিত নই। অনুগ্রহ করে সংশ্লিষ্ট অফিসিয়াল সরকারি পোর্টাল "
        "দেখুন অথবা স্থানীয় অফিসে যোগাযোগ করুন।"
    ),
}

SYSTEM_PROMPT = """You are ESBC-AI, an assistant that explains Bangladeshi government services.
Rules:
1. Answer ONLY from the numbered context below. Never use outside knowledge.
2. If the context does not contain the answer, say you are not sure. Never guess fees, deadlines or requirements.
3. Reply in {lang_name}. Match the language of the user's question exactly.
4. Cite sources inline like [1] or [2] after the facts they support.
5. Be clear and practical. Use short numbered steps for procedures.
{plain_rule}"""

PLAIN_RULE = (
    "6. PLAIN MODE: use very simple words and very short sentences, "
    "as if explaining to someone with little formal education."
)


class State(TypedDict, total=False):
    question: str
    plain: bool
    language: str
    hits: List[dict]
    confident: bool
    answer: str
    sources: List[dict]


def detect_language(state: State) -> State:
    text = state["question"]
    bn = len(re.findall(r"[\u0980-\u09FF]", text))
    letters = len(re.findall(r"[A-Za-z\u0980-\u09FF]", text)) or 1
    return {"language": "bn" if bn / letters > 0.3 else "en"}


def retrieve(state: State) -> State:
    return {"hits": search(state["question"], k=TOP_K)}


def gate(state: State) -> State:
    hits = state.get("hits", [])
    return {"confident": bool(hits) and hits[0]["score"] >= SCORE_THRESHOLD}


def route(state: State) -> str:
    return "generate" if state["confident"] else "fallback"


def _call_model(system: str, user: str) -> str:
    for attempt in range(4):
        try:
            res = get_client().models.generate_content(
                model=GEN_MODEL,
                contents=user,
                config=types.GenerateContentConfig(system_instruction=system, temperature=0.2),
            )
            return (res.text or "").strip()
        except Exception as exc:
            if attempt == 3:
                raise
            time.sleep(4 * (attempt + 1))
            print(f"Generation retry ({exc})")
    return ""


def generate(state: State) -> State:
    hits = [h for h in state["hits"] if h["score"] >= SCORE_THRESHOLD * 0.9]
    context = "\n\n".join(
        f"[{i}] ({h['title']} | {h['url']} | checked {h['date_checked']})\n{h['text']}"
        for i, h in enumerate(hits, 1)
    )
    system = SYSTEM_PROMPT.format(
        lang_name="Bangla (Bengali script)" if state["language"] == "bn" else "English",
        plain_rule=PLAIN_RULE if state.get("plain") else "",
    )
    user = f"Context:\n{context}\n\nQuestion: {state['question']}"
    answer = _call_model(system, user) or FALLBACK[state["language"]]
    sources = [
        {"id": i, "title": h["title"], "url": h["url"],
         "date_checked": h["date_checked"], "service": h["service"], "score": h["score"]}
        for i, h in enumerate(hits, 1)
    ]
    return {"answer": answer, "sources": sources}


def fallback(state: State) -> State:
    return {"answer": FALLBACK[state["language"]], "sources": []}


def build_graph():
    g = StateGraph(State)
    g.add_node("detect_language", detect_language)
    g.add_node("retrieve", retrieve)
    g.add_node("gate", gate)
    g.add_node("generate", generate)
    g.add_node("fallback", fallback)
    g.add_edge(START, "detect_language")
    g.add_edge("detect_language", "retrieve")
    g.add_edge("retrieve", "gate")
    g.add_conditional_edges("gate", route, {"generate": "generate", "fallback": "fallback"})
    g.add_edge("generate", END)
    g.add_edge("fallback", END)
    return g.compile()


_graph = None


def ask(question: str, plain: bool = False) -> dict:
    global _graph
    if _graph is None:
        _graph = build_graph()
    out = _graph.invoke({"question": question, "plain": plain})
    return {
        "answer": out["answer"],
        "language": out["language"],
        "confident": out["confident"],
        "sources": out.get("sources", []),
        "top_score": out["hits"][0]["score"] if out.get("hits") else None,
    }


if __name__ == "__main__":
    result = ask(" ".join(sys.argv[1:]) or "What documents are needed for death registration?")
    print(f"[lang={result['language']} confident={result['confident']} top={result['top_score']}]")
    print(result["answer"])
    for s in result["sources"]:
        print(f"  [{s['id']}] {s['title']} - {s['url']} ({s['date_checked']})")
