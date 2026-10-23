"""Project self-check. Run from the repository root:  python scripts/doctor.py [--live]

Checks the Python environment, dependencies, API key presence, source documents,
syntax of the backend and the knowledge-base index. With --live it also calls the
Gemini API once for embeddings and once for generation.
"""
import importlib
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def main():
    check("Python in project venv", ".venv" in sys.executable.replace("\\", "/"), sys.executable)

    for module in ("fastapi", "uvicorn", "chromadb", "langgraph", "google.genai", "rank_bm25", "dotenv"):
        try:
            importlib.import_module(module)
            check(f"import {module}", True)
        except Exception as exc:
            check(f"import {module}", False, str(exc))

    env_file = BACKEND / ".env"
    key = ""
    if env_file.exists():
        from dotenv import dotenv_values

        key = dotenv_values(env_file).get("GOOGLE_API_KEY", "") or ""
    check("GOOGLE_API_KEY in backend/.env", bool(key), f"length {len(key)}, starts with {key[:4]!r}" if key else "missing")

    for path in sorted(list((BACKEND / "app").glob("*.py")) + list((BACKEND / "tests").glob("*.py"))):
        try:
            py_compile.compile(str(path), doraise=True)
            check(f"syntax {path.relative_to(ROOT).as_posix()}", True)
        except py_compile.PyCompileError as exc:
            check(f"syntax {path.relative_to(ROOT).as_posix()}", False, str(exc).splitlines()[-1])

    for name in ("agent.py", "ingest.py", "search.py"):
        text = (BACKEND / "app" / name).read_text(encoding="utf-8") if (BACKEND / "app" / name).exists() else ""
        check(f"entry point in {name}", 'if __name__ == "__main__":' in text)

    try:
        from app.ingest import chunk_text, parse_doc

        files = sorted((ROOT / "data" / "sources").rglob("*.md"))
        bad, chunks, services = [], 0, {}
        for path in files:
            try:
                meta, body = parse_doc(path)
                if "\ufffd" in body:
                    bad.append(f"{path.name}: replacement character")
                chunks += len(chunk_text(body))
                services[meta["service"]] = services.get(meta["service"], 0) + 1
            except Exception as exc:
                bad.append(f"{path.name}: {exc}")
        check("source documents valid", bool(files) and not bad, f"{len(files)} files, {chunks} chunks" + (f"; {bad}" if bad else ""))
        print("      services:", ", ".join(f"{k}={v}" for k, v in sorted(services.items())))
    except Exception as exc:
        check("source documents valid", False, str(exc))

    try:
        from app.search import index_ready

        check("vector index built", index_ready(), "run: python -m app.ingest" if not index_ready() else "")
    except Exception as exc:
        check("vector index built", False, str(exc))

    if "--live" in sys.argv:
        try:
            from app.embeddings import embed

            check("live embedding call", len(embed(["test"], "RETRIEVAL_QUERY")[0]) == 768)
        except Exception as exc:
            check("live embedding call", False, str(exc)[:200])
        try:
            from app.agent import _call_model

            reply = _call_model("Reply with one word.", "Say: ready")
            check("live generation call", bool(reply), reply[:40])
        except Exception as exc:
            check("live generation call", False, str(exc)[:200])

    print(f"\n{sum(results)} of {len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
