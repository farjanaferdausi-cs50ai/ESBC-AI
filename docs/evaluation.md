# Evaluation results

Question set: 29 questions (answerable and out of scope, Bangla and English). Errors: 0.

| Metric | All | English | Bangla |
|---|---|---|---|
| Retrieval hit rate (top 5) | 100.0% | 100.0% | 100.0% |
| Answer accuracy (keyword match) | 100.0% | 100.0% | 100.0% |
| Refusal accuracy (out of scope) | 100.0% | | |

## Retrieval score separation

- Mean best score, answerable questions: 0.7294347826086957
- Mean best score, out-of-scope questions: 0.6255
- Lowest best score among answerable questions: 0.654
- Highest best score among out-of-scope questions: 0.664

Set SCORE_THRESHOLD between the last two values to separate answerable from out-of-scope questions.

## Failures

None.

Method: lightweight keyword-based checks, not an LLM judge. The expected keywords come from the stored official sources.
