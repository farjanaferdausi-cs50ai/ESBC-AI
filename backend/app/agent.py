"""LangGraph agent: language detection -> hybrid retrieval -> confidence gate -> grounded answer."""
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
        "\u0986\u09ae\u09bf \u098f \u09ac\u09bf\u09b7\u09af\u09bc\u09c7 \u09a8\u09bf\u09b6\u09cd\u099a\u09bf\u09a4 \u09a8\u0987\u0964 "
        "\u0985\u09a8\u09c1\u0997\u09cd\u09b0\u09b9 \u0995\u09b0\u09c7 \u09b8\u0982\u09b6\u09cd\u09b2\u09bf\u09b7\u09cd\u099f "
        "\u0985\u09ab\u09bf\u09b8\u09bf\u09af\u09bc\u09be\u09b2 \u09b8\u09b0\u0995\u09be\u09b0\u09bf \u09aa\u09cb\u09b0\u09cd\u099f\u09be\u09b2 "
        "\u09a6\u09c7\u0996\u09c1\u09a8 \u0985\u09a5\u09ac\u09be \u09b8\u09cd\u09a5\u09be\u09a8\u09c0\u09af\u09bc "
        "\u0985\u09ab\u09bf\u09b8\u09c7 \u09af\u09cb\u0997\u09be\u09af\u09cb\u0997 \u0995\u09b0\u09c1\u09a8\u0964"
    ),
}

SYSTEM_PROMPT = """You are ESBC-AI, an assistant that explains Bangladeshi government services.
Rules:
1. Answer ONLY from the numbered context below. Never use outside knowledge.
2. If the context does not contain the answer, reply with exactly NO_ANSWER and nothing else. Never guess fees, deadlines or requirements.
3. Reply in {lang_name}. Match the language of the user's question exactly.
4. Cite sources inline like [1] or [2] after the facts they support. Only use numbers that exist in the context.
5. Be clear and practical. Use short numbered steps for procedures.
6. If a figure comes from an older notice, say which year or date the context gives for it.
7. If the context mentions a closure, maintenance or deadline with dates that affects the answer, mention it clearly.
8. If sources disagree, prefer the newest one and say that they differ.
{plain_rule}"""

PLAIN_RULE = (
    "9. PLAIN MODE: use very simple words and very short sentences, "
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
    hits = [h for h in state["hits"] if h["score"] >= SCORE_THRESHOLD * 0.8]
    groups = {}
    for h in hits:
        key = (h["url"], h["title"])
        group = groups.setdefault(key, {"meta": h, "texts": [], "best": 0.0})
        group["texts"].append(h["text"])
        group["best"] = max(group["best"], h["score"])
    ordered = list(groups.values())

    context = "\n\n".join(
        f"[{i}] ({g['meta']['title']} | {g['meta']['url']} | checked {g['meta']['date_checked']})\n"
        + "\n".join(g["texts"])
        for i, g in enumerate(ordered, 1)
    )
    system = SYSTEM_PROMPT.format(
        lang_name="Bangla (Bengali script)" if state["language"] == "bn" else "English",
        plain_rule=PLAIN_RULE if state.get("plain") else "",
    )
    user = f"Context:\n{context}\n\nQuestion: {state['question']}"
    answer = _call_model(system, user)
    if not answer or answer.strip().upper().startswith("NO_ANSWER"):
        return {"answer": FALLBACK[state["language"]], "sources": [], "confident": False}
    sources = [
        {
            "id": i,
            "title": g["meta"]["title"],
            "url": g["meta"]["url"],
            "date_checked": g["meta"]["date_checked"],
            "service": g["meta"]["service"],
            "score": g["best"],
        }
        for i, g in enumerate(ordered, 1)
    ]
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
    sources = [s for s in sources if s["id"] in cited] or sources[:1]
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
