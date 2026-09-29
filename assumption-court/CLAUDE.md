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

## Commands

```bash
# Backend (Python 3.11; venv at assumption-court/.venv)
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
cd backend && LLM_PROVIDER=fake RETRIEVAL_PROVIDER=fake uvicorn app.main:app --port 8000   # fully offline
cd backend && pytest -m "not network and not llm"    # offline suite (pytest.ini sets pythonpath + markers)
cd backend && pytest tests/test_rubric.py::test_decisive_needs_gap_and_two_verified_items   # single test
cd backend && python scripts/generate_cached_cases.py  # regenerate cached_cases/ + frontend/public/examples/

# Frontend (Next 16: read node_modules/next/dist/docs before using unfamiliar APIs, per frontend/AGENTS.md)
cd frontend && npm install && npm run dev
cd frontend && npm run lint && npm run build

# Eval (the human runs the full set)
python eval/fetch_fever.py && python eval/run_eval.py --all && python eval/run_eval.py --summary
```

`LLM_PROVIDER=fake` (`backend/app/fake_llm.py`) and `RETRIEVAL_PROVIDER=fake` are deterministic stand-ins, keyed by prompt name. When you add a prompt, add a handler there too or fake mode breaks. The test suite forces both (`tests/conftest.py`).

## Architecture across files

- **Pipeline:** `app/pipeline/build.py` (LangGraph: classify → premise trial → cause trials → final) calls `researcher.py`, `debaters.py`, `factcheck.py` and `judge.py`. They share a mutable `Trial` (`pipeline/state.py`) and emit `GraphEvent`s via `graph_events.py`. `main.py` runs `run_trial` in a background task and appends the events to the polled `TrialJob`.
- **Event stream = UI contract:** the payload shapes are documented in the `graph_events.py` docstring and mirrored in `frontend/lib/types.ts`. The frontend has one paced queue, `frontend/lib/usePlayback.ts`, fed by live polling and by example replay. Each dequeued event updates two pure reducers: `lib/scene.ts` (pixel courtroom and transcript) and `lib/graphState.ts` (React Flow graph). A new event type needs handling in both.
- Evidence nodes are emitted *before* fact-checking with `status=None` (pending). A later `status` event with `evidence_id` sets VERIFIED/UNVERIFIED.

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
