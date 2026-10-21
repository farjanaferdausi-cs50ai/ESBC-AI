"""LangGraph agent: language detection -> hybrid retrieval -> confidence gate -> grounded answer."""
import re

from google.genai import types
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
    return {"language": "bn" if bn / letters > 0.3 else "en"}

def retrieve(state: State) -> State:
    return {"hits": search(state["question"], k=TOP_K)}

def gate(state: State) -> State:
    hits = state.get("hits", [])
    return {"confident": best >= SCORE_THRESHOLD}

def route(state: State) -> str:


def _call_model(system: str, user: str) -> str:
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
    answer = _call_model(system, user) or FALLBACK[state["language"]]
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
    return {"answer": answer, "sources": sources}

def fallback(state: State) -> State:
    return {"answer": FALLBACK[state["language"]], "sources": []}

def build_graph():
    g = StateGraph(State)
    g.add_node("detect_language", detect_language)
    g.add_node("retrieve", retrieve)
    g.add_node("gate", gate)
    g.add_node("generate", generate)
    g.add_edge(START, "detect_language")
    g.add_edge("detect_language", "retrieve")
    g.add_edge("retrieve", "gate")
    return g.compile()



    global _graph
    if _graph is None:
        _graph = build_graph()
    out = _graph.invoke({"question": question, "plain": plain})
    hits = out.get("hits", [])
    return {
        "answer": out["answer"],
        "language": out["language"],
        "sources": out.get("sources", []),
        "top_score": max((h["score"] for h in hits), default=None),
    }


if __name__ == "__main__":
    result = ask(" ".join(sys.argv[1:]) or "What documents are needed for death registration?")
    print(result["answer"])
    for s in result["sources"]:
        print(f"  [{s['id']}] {s['title']} - {s['url']} ({s['date_checked']})")
