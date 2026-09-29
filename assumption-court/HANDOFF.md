# HANDOFF: Assumption Court

## (a) What was built

- **Backend** (`backend/`): FastAPI and a LangGraph pipeline covering classify → premise trial → cause trials → report.
  - Five agents: Researcher (DuckDuckGo + Wikipedia, progressive queries), Bull, Bear (≤3 quotes per round, concede/switch), Fact-checker, Judge.
  - Code-enforced rules: UNVERIFIED exclusion, the anti-gish cap, rubric arithmetic, the anti-neutral re-prompt/override, and INCONCLUSIVE on retrieval failure.
  - Operations: rate limit of 5 trials/hour per IP, 120 s trial timeout, a friendly quota error, and every LLM call logged.
  - Providers: `gemini`, `ollama` and an offline `fake`.
- **Frontend** (`frontend/`): a dark, pixel-agent courtroom with a live speech-bubble debate, exhibits with fact-check stamps, a transcript, an evidence graph and a ruling card. Examples replay even with the backend down.
- **Evaluation** (`eval/`): fair single-prompt baseline, resumable runner, citation grader with a manual-check sample, FEVER fetcher, and 30 unlabelled business assumptions.
- **Deploy:** Dockerfile for HF Spaces (built and smoke-tested locally) and `DEPLOY.md` for Spaces + Vercel.
- **Tests:** 44 offline pytest tests, plus `network` and `llm` marked tests for real conditions.

## (b) Known issues

- **Nothing has run against the real Gemini model yet.** Every verdict, cached example and pipeline call count so far comes from the deterministic fake LLM. Prompt quality, JSON conformance and verdict accuracy with Gemini are untested.
- Live retrieval (ddgs/Wikipedia) is untested because the build sandbox blocked those hosts. `pytest -m network` will tell you.
- `fever_100.jsonl` doesn't exist yet (fever.ai was blocked). Run `python eval/fetch_fever.py`.
- The cached examples in `backend/cached_cases/` and `frontend/public/examples/` are offline placeholders (titles say so). Regenerate them with the real model before any demo.
- The job store is in memory: restarting the Space loses running trials. The rate limit is per process.
- The pixel font needs Google Fonts; without it, headings fall back to monospace.

## (c) Human to-do list

1. `cp .env.example .env`, set `GEMINI_API_KEY` and `GEMINI_MODEL`, then:
   - `cd backend && pytest` (runs the `llm` and `network` tests too);
   - start one live trial in the UI.
2. Regenerate the demo cases with the real model: `cd backend && python scripts/generate_cached_cases.py`. Then run one more live trial as an extra cached example:

   ```bash
   python scripts/generate_cached_cases.py --only live-1 --text "…"
   ```
3. Label `eval/data/business_30.jsonl` (SUPPORTED / REFUTED / INCONCLUSIVE).
4. Run `python eval/fetch_fever.py` and record the source URL in `eval/report.md`.
5. Smoke run: `python eval/run_eval.py --dataset fever --limit 10`. Tune `JUDGE_DECISIVE_GAP` on this run only, then freeze it with `git tag eval-v1`.
6. Full evaluation: `python eval/run_eval.py --all`, then `--summary`, then `python eval/grade_citations.py`.
7. Do the manual 20-pair citation check in `eval/manual_check.csv`.
8. Fill in the README evaluation table and **Where the Court loses**, then `eval/report.md`.
9. Deploy per `DEPLOY.md` (HF Space + Vercel).
10. Tag `v1.0` once steps 1–9 hold.
11. Record the 90-second demo (use an example replay: it is rate-limit-proof).
12. Post on LinkedIn.
