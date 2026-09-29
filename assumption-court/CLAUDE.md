# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Assumption Court: a 5-agent "courtroom" (Researcher, Bull, Bear, Fact-checker, Judge) that puts a business assumption on trial. It grounds every claim in verbatim retrieved quotes and returns a rubric-scored verdict, rendered live as an evidence graph. The full build order is in `BUILD.md`, which is imported below and is the source of truth.

- `BUILD.md` and `AGENTS.md` are identical copies of the spec. If you edit one, apply the same edit to the other.
- `MASTER-reference.md` is the human-facing plan (a 9-day schedule and a LinkedIn plan). It is not build instructions. Where it conflicts with `BUILD.md`, `BUILD.md` wins.
- `PROGRESS.md` holds the phase status log. Update it after every phase (§A.1).

## Repo layout gotcha

The git root is the **parent** directory (`/home/user/repo`), and the project lives in `assumption-court/`. P1 says "`git init`". **Do not** run it, because that would create a nested repo. Commit to the existing repo instead. Paths in `BUILD.md` §B.10 are relative to `assumption-court/`.

## Starting / resuming

- Start: "Read BUILD.md fully, then build." This runs phases P1→P8 without pausing, except for the stop conditions in §A.3.
- Resume: read `BUILD.md` and `PROGRESS.md`, run `git log --oneline`, then continue from the first phase not marked DONE.
- P1 hard-stops if `.env` is missing or `GEMINI_API_KEY` is invalid. Copy `.env.example` to `.env` first. `GEMINI_MODEL` must come from env and must never be hardcoded.

## Commands (once scaffolded per §B.10)

```bash
# Backend (Python 3.11)
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --port 8000          # run from backend/
cd backend && pytest                                # all tests (backend/pytest.ini sets pythonpath + markers)
cd backend && pytest -m "not network and not llm"   # offline tests only
cd backend && pytest tests/test_rubric.py::test_name # single test
# LLM_PROVIDER=fake gives deterministic canned responses (no API key needed).

# Frontend
cd frontend && npm install && npm run dev           # npm run build = P6 acceptance check

# Eval (the human runs the full set; the build runs only the 10-claim smoke test)
python eval/run_eval.py --all
```

## Invariants that span multiple files (never violate)

- **Grounding:** every `Evidence` has a verbatim `retrieved_quote` (never paraphrased). Non-`verified` fact-checks → `status="UNVERIFIED"`, which is excluded from Judge scoring in code but still shown in the graph and report.
- **Arithmetic lives in code:** the Judge LLM assigns only item-level `source_tier` and `recency`. `rubric.py` computes totals, gap, the anti-neutral override and confidence (§B.5).
- **Max 3 evidence items per side per round.** Code truncates any extra and logs a warning.
- **Prompts** live only in `backend/prompts/*.md`. **Every LLM call** is logged to `backend/logs/llm_calls.jsonl` via `llm.py`.
- **Pydantic models in `models.py` are mirrored as TypeScript types** in the frontend. Change both together.
- **Baseline fairness:** `eval/baseline.py` uses the same model and the same retrieval budget as the Court.
- Retrieval failure → `INCONCLUSIVE` with reason "retrieval failed". Never fabricate.
- `business_30.jsonl` labels stay `null`, because the human labels them.

@BUILD.md
