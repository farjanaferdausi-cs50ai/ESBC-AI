from app.ingest import chunk_text, parse_doc

def test_detects_english():
    assert detect_language({"question": "What documents are needed?"})["language"] == "en"


def test_detects_bangla():
    text = "\u09ae\u09c3\u09a4\u09cd\u09af\u09c1 \u09a8\u09bf\u09ac\u09a8\u09cd\u09a7\u09a8"


def test_chunking_splits_long_text():
    text = "\n\n".join(f"Sentence number {i} is here." for i in range(60))
    chunks = chunk_text(text, max_chars=200, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 260 for c in chunks)

def test_parse_doc_reads_front_matter(tmp_path):
    path = tmp_path / "doc.md"
    path.write_text(
        "---\nservice: x\ntitle: T\nurl: https://a.gov.bd\ndate_checked: 2026-10-21\nlanguage: en\n---\n\nBody",
        encoding="utf-8",
    )
    meta, body = parse_doc(path)
    assert meta["service"] == "x" and body == "Body"

def test_parse_doc_rejects_missing_fields(tmp_path):
    path = tmp_path / "bad.md"
    path.write_text("---\nservice: x\n---\n\nBody", encoding="utf-8")
    try:
        parse_doc(path)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_health_endpoint():
    from app.main import app

    assert TestClient(app).get("/health").json() == {"status": "ok"}


def test_chat_validates_input():
    from app.main import app

    assert TestClient(app).post("/api/chat", json={"message": "a"}).status_code == 422


def test_chat_returns_answer(monkeypatch):
    import app.main as m

    monkeypatch.setattr(
        m, "ask",
        lambda q, plain=False: {"answer": "ok", "language": "en", "confident": True, "sources": [], "top_score": 0.9},
    res = TestClient(m.app).post("/api/chat", json={"message": "hello there"})
    assert res.status_code == 200 and res.json()["answer"] == "ok"


def test_chat_failure_returns_503(monkeypatch):

    def boom(q, plain=False):
        raise RuntimeError("boom")

    monkeypatch.setattr(m, "ask", boom)
    assert TestClient(m.app).post("/api/chat", json={"message": "hello there"}).status_code == 503
