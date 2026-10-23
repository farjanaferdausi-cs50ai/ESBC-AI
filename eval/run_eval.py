"""Evaluation harness. Run from the repository root:  python eval/run_eval.py

Measures, on a fixed question set with Bangla and English questions:
  * retrieval hit rate: expected evidence appears in the top retrieved chunks
  * answer accuracy: the generated answer contains the expected fact
  * refusal accuracy: out-of-scope questions are declined instead of guessed
  * the Bangla versus English gap
Results are written to docs/evaluation.md and docs/evaluation.json.
"""
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# (language, question, any-of expected keywords). expected=None means out of scope.
CASES = [
    ("en", "How much does a 64-page, 10-year e-passport cost with regular delivery?", ["8,050", "8050"]),
    ("en", "What are the delivery times for regular, express and super express e-passports?", ["15 working days", "7 working days", "2 working days"]),
    ("en", "What documents must I bring to the passport office for biometric enrolment?", ["application summary", "Printed application"]),
    ("en", "Which payment channels can I use to pay e-passport fees online?", ["A-Challan", "DGePay", "ShurjoPay"]),
    ("en", "What is the minimum age to receive the old age allowance?", ["65", "62"]),
    ("en", "What is the yearly income limit for the old age allowance?", ["45,000", "45000"]),
    ("en", "How much is the monthly widow allowance in 2026-27?", ["700"]),
    ("en", "How much financial support does a cancer patient receive?", ["1,00,000", "100,000", "one lakh", "1 lakh"]),
    ("en", "What is the deadline to register a death without paying a fee?", ["45"]),
    ("en", "What is the fee to register a death after more than 5 years?", ["50"]),
    ("en", "Can I apply for death registration online this week?", ["25 October", "25/10", "maintenance"]),
    ("en", "What is the income tax contact center number?", ["333"]),
    ("en", "What is the fee for the first correction of an NID?", ["200"]),
    ("bn", "\u09ec\u09ea \u09aa\u09c3\u09b7\u09cd\u09a0\u09be\u09b0 \u09e7\u09e6 \u09ac\u099b\u09b0 \u09ae\u09c7\u09af\u09bc\u09be\u09a6\u09c0 \u0987-\u09aa\u09be\u09b8\u09aa\u09cb\u09b0\u09cd\u099f\u09c7\u09b0 \u09b0\u09c7\u0997\u09c1\u09b2\u09be\u09b0 \u09a1\u09c7\u09b2\u09bf\u09ad\u09be\u09b0\u09bf \u09ab\u09bf \u0995\u09a4?", ["8,050", "8050", "\u09ee,\u09e6\u09eb\u09e6", "\u09ee\u09e6\u09eb\u09e6"]),
    ("bn", "\u09ac\u09af\u09bc\u09b8\u09cd\u0995 \u09ad\u09be\u09a4\u09be \u09aa\u09c7\u09a4\u09c7 \u09aa\u09c1\u09b0\u09c1\u09b7 \u0993 \u09a8\u09be\u09b0\u09c0\u09b0 \u09b8\u09b0\u09cd\u09ac\u09a8\u09bf\u09ae\u09cd\u09a8 \u09ac\u09af\u09bc\u09b8 \u0995\u09a4?", ["\u09ec\u09eb", "\u09ec\u09e8", "65", "62"]),
    ("bn", "\u09ac\u09bf\u09a7\u09ac\u09be \u09ad\u09be\u09a4\u09be\u09b0 \u09ae\u09be\u09b8\u09bf\u0995 \u09aa\u09b0\u09bf\u09ae\u09be\u09a3 \u0995\u09a4?", ["\u09ed\u09e6\u09e6", "700"]),
    ("bn", "\u09ae\u09c3\u09a4\u09cd\u09af\u09c1\u09b0 \u0995\u09a4 \u09a6\u09bf\u09a8\u09c7\u09b0 \u09ae\u09a7\u09cd\u09af\u09c7 \u09ab\u09bf \u099b\u09be\u09a1\u09bc\u09be \u09a8\u09bf\u09ac\u09a8\u09cd\u09a7\u09a8 \u0995\u09b0\u09be \u09af\u09be\u09af\u09bc?", ["\u09ea\u09eb", "45"]),
    ("bn", "\u09ae\u09c3\u09a4\u09cd\u09af\u09c1 \u09a8\u09bf\u09ac\u09a8\u09cd\u09a7\u09a8 \u09eb \u09ac\u099b\u09b0 \u09aa\u09b0\u09c7 \u0995\u09b0\u09b2\u09c7 \u09ab\u09bf \u0995\u09a4?", ["\u09eb\u09e6", "50"]),
    ("bn", "\u098f\u0987 \u09b8\u09aa\u09cd\u09a4\u09be\u09b9\u09c7 \u0995\u09bf \u0985\u09a8\u09b2\u09be\u0987\u09a8\u09c7 \u09ae\u09c3\u09a4\u09cd\u09af\u09c1 \u09a8\u09bf\u09ac\u09a8\u09cd\u09a7\u09a8\u09c7\u09b0 \u0986\u09ac\u09c7\u09a6\u09a8 \u0995\u09b0\u09be \u09af\u09be\u09ac\u09c7?", ["\u09e8\u09eb", "25", "\u09b0\u0995\u09cd\u09b7\u09a3\u09be\u09ac\u09c7\u0995\u09cd\u09b7\u09a3"]),
    ("bn", "\u099c\u09a8\u09cd\u09ae \u09a8\u09bf\u09ac\u09a8\u09cd\u09a7\u09a8\u09c7\u09b0 \u09a4\u09a5\u09cd\u09af \u09b8\u0982\u09b6\u09cb\u09a7\u09a8\u09c7\u09b0 \u09ab\u09bf \u0995\u09a4?", ["\u09eb\u09e6", "\u09e7\u09e6\u09e6", "50", "100"]),
    ("bn", "NID \u09b8\u0982\u09b6\u09cb\u09a7\u09a8\u09c7\u09b0 \u09ab\u09bf \u09aa\u09cd\u09b0\u09a5\u09ae\u09ac\u09be\u09b0 \u0995\u09a4 \u099f\u09be\u0995\u09be?", ["\u09e8\u09e6\u09e6", "200"]),
    ("bn", "\u0986\u09af\u09bc\u0995\u09b0 \u0995\u09a8\u09cd\u099f\u09be\u0995\u09cd\u099f \u09b8\u09c7\u09a8\u09cd\u099f\u09be\u09b0\u09c7\u09b0 \u09a8\u09ae\u09cd\u09ac\u09b0 \u0995\u09a4?", ["\u09e9\u09e9\u09e9", "333"]),
    ("bn", "\u09ae\u09c3\u09a4\u09cd\u09af\u09c1 \u09a8\u09bf\u09ac\u09a8\u09cd\u09a7\u09a8\u09c7\u09b0 \u099c\u09a8\u09cd\u09af \u0987\u09ae\u09be\u09ae\u09c7\u09b0 \u09aa\u09cd\u09b0\u09a4\u09cd\u09af\u09af\u09bc\u09a8 \u09b2\u09be\u0997\u09c7 \u0995\u09bf?", ["\u0987\u09ae\u09be\u09ae", "\u09aa\u09cd\u09b0\u09a4\u09cd\u09af\u09af\u09bc\u09a8"]),
    ("en", "How much is the driving licence fee?", None),
    ("en", "How do I apply for land mutation?", None),
    ("en", "How do I get a police clearance certificate?", None),
    ("bn", "\u09a1\u09cd\u09b0\u09be\u0987\u09ad\u09bf\u0982 \u09b2\u09be\u0987\u09b8\u09c7\u09a8\u09cd\u09b8\u09c7\u09b0 \u09ab\u09bf \u0995\u09a4?", None),
    ("bn", "\u099f\u09cd\u09b0\u09c7\u09a1 \u09b2\u09be\u0987\u09b8\u09c7\u09a8\u09cd\u09b8 \u0995\u09c0\u09ad\u09be\u09ac\u09c7 \u0995\u09b0\u09ac?", None),
    ("bn", "\u09ad\u09c2\u09ae\u09bf \u09ae\u09bf\u0989\u099f\u09c7\u09b6\u09a8\u09c7\u09b0 \u0986\u09ac\u09c7\u09a6\u09a8 \u0995\u09c0\u09ad\u09be\u09ac\u09c7 \u0995\u09b0\u09ac?", None),
]


def contains_any(text, keywords):
    low = text.lower()
    return any(k.lower() in low for k in keywords)


def run(cases, ask_fn, search_fn, pause=1.0):
    rows = []
    for lang, question, expected in cases:
        row = {"lang": lang, "question": question, "in_scope": expected is not None}
        try:
            result = ask_fn(question)
            row.update(confident=result["confident"], top=result["top_score"], answer=result["answer"])
            if expected is not None:
                hits = search_fn(question, k=5)
                row["retrieval_hit"] = any(contains_any(h["text"], expected) for h in hits)
                row["answer_correct"] = result["confident"] and contains_any(result["answer"], expected)
            else:
                row["refused"] = not result["confident"]
        except Exception as exc:
            row["error"] = str(exc)[:160]
        rows.append(row)
        time.sleep(pause)
    return rows


def rate(rows, key, lang=None):
    pool = [r for r in rows if key in r and (lang is None or r["lang"] == lang)]
    return (sum(1 for r in pool if r[key]) / len(pool) * 100) if pool else float("nan")


def summarise(rows):
    in_scope = [r for r in rows if r["in_scope"] and "top" in r]
    out_scope = [r for r in rows if not r["in_scope"] and "top" in r]
    stats = {
        "questions": len(rows),
        "errors": sum(1 for r in rows if "error" in r),
        "retrieval_hit_rate": rate(rows, "retrieval_hit"),
        "retrieval_hit_rate_en": rate(rows, "retrieval_hit", "en"),
        "retrieval_hit_rate_bn": rate(rows, "retrieval_hit", "bn"),
        "answer_accuracy": rate(rows, "answer_correct"),
        "answer_accuracy_en": rate(rows, "answer_correct", "en"),
        "answer_accuracy_bn": rate(rows, "answer_correct", "bn"),
        "refusal_accuracy": rate(rows, "refused"),
        "mean_top_score_in_scope": statistics.mean(r["top"] for r in in_scope) if in_scope else None,
        "mean_top_score_out_of_scope": statistics.mean(r["top"] for r in out_scope) if out_scope else None,
        "max_top_score_out_of_scope": max((r["top"] for r in out_scope), default=None),
        "min_top_score_in_scope": min((r["top"] for r in in_scope), default=None),
    }
    return stats


def fmt(value):
    return "n/a" if value is None or value != value else f"{value:.1f}%"


def write_reports(rows, stats):
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "evaluation.json").write_text(json.dumps({"stats": stats, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Evaluation results",
        "",
        f"Question set: {stats['questions']} questions (answerable and out of scope, Bangla and English). Errors: {stats['errors']}.",
        "",
        "| Metric | All | English | Bangla |",
        "|---|---|---|---|",
        f"| Retrieval hit rate (top 5) | {fmt(stats['retrieval_hit_rate'])} | {fmt(stats['retrieval_hit_rate_en'])} | {fmt(stats['retrieval_hit_rate_bn'])} |",
        f"| Answer accuracy (keyword match) | {fmt(stats['answer_accuracy'])} | {fmt(stats['answer_accuracy_en'])} | {fmt(stats['answer_accuracy_bn'])} |",
        f"| Refusal accuracy (out of scope) | {fmt(stats['refusal_accuracy'])} | | |",
        "",
        "## Retrieval score separation",
        "",
        f"- Mean best score, answerable questions: {stats['mean_top_score_in_scope']}",
        f"- Mean best score, out-of-scope questions: {stats['mean_top_score_out_of_scope']}",
        f"- Lowest best score among answerable questions: {stats['min_top_score_in_scope']}",
        f"- Highest best score among out-of-scope questions: {stats['max_top_score_out_of_scope']}",
        "",
        "Set SCORE_THRESHOLD between the last two values to separate answerable from out-of-scope questions.",
        "",
        "## Failures",
        "",
    ]
    failures = [
        r for r in rows
        if "error" in r or r.get("answer_correct") is False or r.get("retrieval_hit") is False or r.get("refused") is False
    ]
    if not failures:
        lines.append("None.")
    for r in failures:
        reason = r.get("error") or ("answer missed expected fact" if r.get("answer_correct") is False else "wrongly answered an out-of-scope question" if r.get("refused") is False else "evidence not retrieved")
        lines.append(f"- [{r['lang']}] {r['question']} ({reason})")
    lines += ["", "Method: lightweight keyword-based checks, not an LLM judge. The expected keywords come from the stored official sources."]
    (docs / "evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    from app.agent import ask
    from app.search import search

    rows = run(CASES, ask, search)
    stats = summarise(rows)
    write_reports(rows, stats)
    for key, value in stats.items():
        print(f"{key}: {value}")
    print("Wrote docs/evaluation.md and docs/evaluation.json")


if __name__ == "__main__":
    main()
