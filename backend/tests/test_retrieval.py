"""Retrieval and agent tests that run offline with a deterministic fake embedding."""
import zlib

import pytest

import app.agent as agent
import app.ingest as ingest
import app.search as search_mod

DIM = 128


@pytest.fixture(autouse=True)
def clear_answer_cache():
    agent._cache.clear()
    yield
    agent._cache.clear()


def fake_embed(texts, task_type, batch_size=20):
    vectors = []
    for text in texts:
        vec = [0.001] * DIM
        for token in search_mod.tokenize(text):
            vec[zlib.crc32(token.encode("utf-8")) % DIM] += 1.0
        vectors.append(vec)
    return vectors


DOCS = {
    "passport.md": (
        "passport", "e-Passport fees", "en",
        "e-Passport with 64 pages and 10 years validity: Regular delivery TK 8,050.",
    ),
    "dss.md": (
        "dss", "Old age allowance", "bn",
        "\u09ac\u09af\u09bc\u09b8\u09cd\u0995 \u09ad\u09be\u09a4\u09be \u09aa\u09c7\u09a4\u09c7 "
        "\u09aa\u09c1\u09b0\u09c1\u09b7\u09c7\u09b0 \u09ac\u09af\u09bc\u09b8 \u09ec\u09eb \u09ac\u099b\u09b0\u0964",
    ),
    "tax.md": ("tax", "Tax contacts", "en", "Income tax contact center number 333 for questions."),
}


def build_index(tmp_path, monkeypatch):
    sources = tmp_path / "sources"
    sources.mkdir()
    for name, (service, title, lang, body) in DOCS.items():
        (sources / name).write_text(
            f"---\nservice: {service}\ntitle: {title}\nurl: https://x.gov.bd/{service}\n"
            f"date_checked: 2026-10-21\nlanguage: {lang}\n---\n\n{body}\n",
            encoding="utf-8",
        )
    chroma = tmp_path / "chroma"
    for module in (ingest, search_mod):
        monkeypatch.setattr(module, "CHROMA_DIR", chroma)
        monkeypatch.setattr(module, "embed", fake_embed)
    monkeypatch.setattr(ingest, "SOURCES_DIR", sources)
    search_mod.reset_cache()
    ingest.main()
    search_mod.reset_cache()


def test_hybrid_search_finds_right_document(tmp_path, monkeypatch):
    build_index(tmp_path, monkeypatch)
    assert search_mod.index_ready()
    hits = search_mod.search("passport fee 8,050 regular delivery", k=3)
    assert hits[0]["service"] == "passport"
    hits_bn = search_mod.search("\u09ac\u09af\u09bc\u09b8\u09cd\u0995 \u09ad\u09be\u09a4\u09be", k=3)
    assert hits_bn[0]["service"] == "dss"


def test_knowledge_stats(tmp_path, monkeypatch):
    build_index(tmp_path, monkeypatch)
    stats = search_mod.knowledge_stats()
    assert stats["ready"] and stats["documents"] == 3
    assert stats["services"] == ["dss", "passport", "tax"]


def test_agent_answers_and_groups_sources(monkeypatch):
    hits = [
        {"text": "a", "score": 0.8, "title": "T1", "url": "u1", "date_checked": "d", "service": "s"},
        {"text": "b", "score": 0.7, "title": "T1", "url": "u1", "date_checked": "d", "service": "s"},
        {"text": "c", "score": 0.6, "title": "T2", "url": "u2", "date_checked": "d", "service": "s"},
    ]
    monkeypatch.setattr(agent, "search", lambda q, k=5: hits)
    monkeypatch.setattr(agent, "_call_model", lambda system, user: "answer [1] and [2]")
    out = agent.ask("What is the fee?")
    assert out["confident"] and out["answer"] == "answer [1] and [2]"
    assert [s["id"] for s in out["sources"]] == [1, 2]
    assert out["top_score"] == 0.8


def test_agent_refuses_when_not_confident(monkeypatch):
    low = [{"text": "a", "score": 0.1, "title": "T", "url": "u", "date_checked": "d", "service": "s"}]
    monkeypatch.setattr(agent, "search", lambda q, k=5: low)

    def must_not_run(system, user):
        raise AssertionError("model should not be called")

    monkeypatch.setattr(agent, "_call_model", must_not_run)
    out = agent.ask("driving licence fee")
    assert not out["confident"] and out["sources"] == []
    assert out["answer"] == agent.FALLBACK["en"]


def test_agent_shows_only_cited_sources(monkeypatch):
    hits = [
        {"text": "a", "score": 0.8, "title": "T1", "url": "u1", "date_checked": "d", "service": "s"},
        {"text": "c", "score": 0.7, "title": "T2", "url": "u2", "date_checked": "d", "service": "s"},
    ]
    monkeypatch.setattr(agent, "search", lambda q, k=5: hits)
    monkeypatch.setattr(agent, "_call_model", lambda system, user: "only the first [1]")
    out = agent.ask("What is the fee?")
    assert [s["id"] for s in out["sources"]] == [1]


def test_agent_declines_when_model_returns_no_answer(monkeypatch):
    hits = [{"text": "a", "score": 0.8, "title": "T", "url": "u", "date_checked": "d", "service": "s"}]
    monkeypatch.setattr(agent, "search", lambda q, k=5: hits)
    monkeypatch.setattr(agent, "_call_model", lambda system, user: "NO_ANSWER")
    out = agent.ask("How much is the driving licence fee?")
    assert out["confident"] is False and out["sources"] == []
    assert out["answer"] == agent.FALLBACK["en"]


class _FakeModels:
    def __init__(self, fail_first):
        self.fail_first = fail_first
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        if len(self.calls) <= self.fail_first:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

        class Reply:
            text = "ok from " + model

        return Reply()


class _FakeClient:
    def __init__(self, fail_first):
        self.models = _FakeModels(fail_first)


def test_model_fallback_uses_next_model(monkeypatch):
    client = _FakeClient(fail_first=1)
    monkeypatch.setattr(agent, "get_client", lambda: client)
    monkeypatch.setattr(agent, "GEN_MODELS", ["model-a", "model-b"])
    monkeypatch.setattr(agent.time, "sleep", lambda s: None)
    assert agent._call_model("sys", "user") == "ok from model-b"
    assert client.models.calls == ["model-a", "model-b"]


def test_model_failure_raises_after_all_attempts(monkeypatch):
    client = _FakeClient(fail_first=99)
    monkeypatch.setattr(agent, "get_client", lambda: client)
    monkeypatch.setattr(agent, "GEN_MODELS", ["model-a"])
    monkeypatch.setattr(agent.time, "sleep", lambda s: None)
    try:
        agent._call_model("sys", "user")
        raise AssertionError("expected an error")
    except RuntimeError:
        pass


def test_repeated_questions_are_cached(monkeypatch):
    agent._cache.clear()
    calls = {"n": 0}
    hits = [{"text": "a", "score": 0.8, "title": "T", "url": "u", "date_checked": "d", "service": "s"}]

    def counting_search(q, k=5):
        calls["n"] += 1
        return hits

    monkeypatch.setattr(agent, "search", counting_search)
    monkeypatch.setattr(agent, "_call_model", lambda system, user: "fee is 50 [1]")
    first = agent.ask("What is the fee?")
    second = agent.ask("  what is the FEE? ")
    assert first == second and calls["n"] == 1
    agent._cache.clear()
