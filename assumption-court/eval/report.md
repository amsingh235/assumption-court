# Evaluation report: Court vs single-AI baseline

> Status: **not yet run.** The harness is built and tested offline. The numbers below are filled in after the
> human runs the full evaluation with a real `GEMINI_API_KEY` (see README → Evaluation).

## Setup
- **Arms:** Court (5 agents) vs Baseline (one prompt, `prompts/baseline.md`), the **same model** (`GEMINI_MODEL`)
  and the **same retrieval budget** (the baseline uses the number of queries the Court used on that case,
  with the same results per query).
- **FEVER source:** _fill in from `eval/data/fever_100.source.txt` after running `python eval/fetch_fever.py`._
  100 claims stratified 34/33/33 (SUPPORTS / REFUTES / NOT ENOUGH INFO → SUPPORTED / REFUTED / INCONCLUSIVE), seed 42.
- **Business set:** `eval/data/business_30.jsonl`, 30 assumptions labelled by the human (not by the model).
- **Frozen threshold:** `JUDGE_DECISIVE_GAP = _` (tuned on the 10-claim smoke run only, then tagged `eval-v1`).

## Results
_Paste the output of `python eval/run_eval.py --summary`._

| Dataset | Arm | N | Accuracy | INCONCLUSIVE rate | Avg LLM calls | Avg seconds |
|---|---|---|---|---|---|---|
| fever | court | | | | | |
| fever | baseline | | | | | |
| business | court | | | | | |
| business | baseline | | | | | |

## Citation quality
_Paste the output of `python eval/grade_citations.py`, plus the agreement between the LLM grader and the human on
the 20 pairs in `manual_check.csv`._

## Where the Court loses
_Fill in honestly: the cases where the baseline was right and the Court was wrong, and why._
