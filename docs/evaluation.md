# Evaluation results

Question set: 29 questions (answerable and out of scope, Bangla and English). Errors: 0.

| Metric | All | English | Bangla |
|---|---|---|---|
| Retrieval hit rate (top 5) | 73.9% | 69.2% | 80.0% |
| Answer accuracy (keyword match) | 60.9% | 46.2% | 80.0% |
| Refusal accuracy (out of scope) | 100.0% | | |

## Retrieval score separation

- Mean best score, answerable questions: 0.667
- Mean best score, out-of-scope questions: 0.6185
- Lowest best score among answerable questions: 0.478
- Highest best score among out-of-scope questions: 0.664

Set SCORE_THRESHOLD between the last two values to separate answerable from out-of-scope questions.

## Failures

- [en] What is the minimum age to receive the old age allowance? (answer missed expected fact)
- [en] What is the yearly income limit for the old age allowance? (answer missed expected fact)
- [en] How much is the monthly widow allowance in 2026-27? (answer missed expected fact)
- [en] How much financial support does a cancer patient receive? (answer missed expected fact)
- [en] What is the deadline to register a death without paying a fee? (answer missed expected fact)
- [en] What is the fee to register a death after more than 5 years? (answer missed expected fact)
- [en] What is the fee for the first correction of an NID? (answer missed expected fact)
- [bn] ৬৪ পৃষ্ঠার ১০ বছর মেয়াদী ই-পাসপোর্টের রেগুলার ডেলিভারি ফি কত? (answer missed expected fact)
- [bn] আয়কর কন্টাক্ট সেন্টারের নম্বর কত? (answer missed expected fact)

Method: lightweight keyword-based checks, not an LLM judge. The expected keywords come from the stored official sources.
