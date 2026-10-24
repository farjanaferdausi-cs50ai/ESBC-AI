"""Refresh the generated blocks of README.md. Run from the repository root:

    python scripts/update_readme.py --app https://your-app.vercel.app --api https://your-api.onrender.com

The links are remembered in docs/links.json, so later runs need no arguments.
Updates: the link bar, the evaluation table (from docs/evaluation.json) and the
screenshots table (from the images that exist in docs/screenshots).
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
LINKS = ROOT / "docs" / "links.json"
PROPOSAL = "https://farjanaferdausi-cs50ai.github.io/ESBC-AI-Proposal/"


def replace_block(text, name, content):
    pattern = re.compile(rf"(<!-- {name}:start -->)(.*?)(<!-- {name}:end -->)", re.S)
    if not pattern.search(text):
        raise SystemExit(f"README.md is missing the <!-- {name}:start --> marker")
    return pattern.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text)


def links_block(app, api):
    parts = []
    if app:
        parts.append(f"**[Live app]({app})**")
    if api:
        parts.append(f"**[API docs]({api.rstrip('/')}/docs)**")
    parts.append(f"**[Proposal]({PROPOSAL})**")
    if (ROOT / "docs" / "evaluation.md").exists():
        parts.append("**[Evaluation](docs/evaluation.md)**")
    if (ROOT / "docs" / "REPORT.md").exists():
        parts.append("**[Final report](docs/REPORT.md)**")
    line = " | ".join(parts)
    if not (app or api):
        line += "\n\n*Live links are added after deployment.*"
    return line


def pct(value):
    return "n/a" if value is None or value != value else f"{value:.0f}%"


def eval_block():
    path = ROOT / "docs" / "evaluation.json"
    if not path.exists():
        return "Run `python eval/run_eval.py` to generate the results. They are written to `docs/evaluation.md`."
    s = json.loads(path.read_text(encoding="utf-8"))["stats"]
    return "\n".join([
        f"Fixed set of {s['questions']} questions (answerable and out of scope, Bangla and English). Details and failures: [docs/evaluation.md](docs/evaluation.md).",
        "",
        "| Metric | All | English | Bangla |",
        "|---|---|---|---|",
        f"| Retrieval hit rate (top 5) | {pct(s['retrieval_hit_rate'])} | {pct(s['retrieval_hit_rate_en'])} | {pct(s['retrieval_hit_rate_bn'])} |",
        f"| Answer accuracy | {pct(s['answer_accuracy'])} | {pct(s['answer_accuracy_en'])} | {pct(s['answer_accuracy_bn'])} |",
        f"| Refusal accuracy on out-of-scope questions | {pct(s['refusal_accuracy'])} | | |",
    ])


def shots_block():
    shots = [("Home", "home.png"), ("Death certificate guide", "guide.png"), ("Answer with sources", "answer.png")]
    found = [(t, f) for t, f in shots if (ROOT / "docs" / "screenshots" / f).exists()]
    if not found:
        return "Screenshots are added after deployment."
    head = "| " + " | ".join(t for t, _ in found) + " |"
    sep = "|" + "---|" * len(found)
    row = "| " + " | ".join(f"![{t}](docs/screenshots/{f})" for t, f in found) + " |"
    return "\n".join([head, sep, row])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app")
    parser.add_argument("--api")
    args = parser.parse_args()

    saved = json.loads(LINKS.read_text(encoding="utf-8")) if LINKS.exists() else {}
    app = args.app or saved.get("app")
    api = args.api or saved.get("api")
    LINKS.parent.mkdir(exist_ok=True)
    LINKS.write_text(json.dumps({"app": app, "api": api}, indent=2), encoding="utf-8")

    text = README.read_text(encoding="utf-8")
    text = replace_block(text, "links", links_block(app, api))
    text = replace_block(text, "eval", eval_block())
    text = replace_block(text, "shots", shots_block())
    README.write_text(text, encoding="utf-8")
    print("README.md updated. App:", app, "| API:", api)


if __name__ == "__main__":
    main()
