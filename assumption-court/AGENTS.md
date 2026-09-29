# ⚖️ ASSUMPTION COURT: ONE-GO BUILD FILE

> **For the coding agent:** this file is a complete, self-contained build order. When the human says **"build"**, execute the Autonomous Build Protocol (§A) from Phase P1 through P8 without waiting for approval between phases. Stop ONLY for the reasons listed in §A.3.
> **For the human (Amiya):** put this file in an empty folder as `BUILD.md`, add a `.env` (see §B.9), start Claude Code, and say: `Read BUILD.md fully, then build.`

---

## §A. AUTONOMOUS BUILD PROTOCOL (READ FIRST)

### A.1 Execution loop (repeat for every phase P1 → P8)
1. Re-read the phase in §C and the rules in §B.
2. Write a short plan (5–10 lines) into `PROGRESS.md` under the phase heading.
3. Implement.
4. Run the phase's **acceptance checks** (tests, curl, scripts). Fix until they pass.
5. `git commit -m "P<n>: <summary>"`.
6. Update the Status Log (§F) in `PROGRESS.md`: done / issues / next.
7. Continue immediately to the next phase.

### A.2 Engineering rules (apply everywhere)
- Never invent numbers, sources, API behaviours or library signatures. **Check official docs** before using any library API. If unsure, write `ASSUMPTION:` in a code comment and in PROGRESS.md.
- Keep all prompts in `backend/prompts/*.md` (versioned files, no inline magic strings).
- Log every LLM call: model, prompt file, tokens (if available), latency, raw response, and write it to `backend/logs/llm_calls.jsonl`.
- Prefer boring, well-documented solutions. Keep files under ~300 lines and use type hints.
- Never commit `.env` or secrets. Add them to `.gitignore` in P1.
- If one task causes more than about 45 minutes of friction, pick the simplest working alternative, note it in PROGRESS.md, and move on. Do not rabbit-hole.

### A.3 STOP and ask the human ONLY if:
1. `GEMINI_API_KEY` is missing or invalid (P1 check).
2. A required dataset or library cannot be obtained after two different attempts.
3. An action needs a human login or account (Hugging Face, Vercel, GitHub push). **Prepare everything, then list the exact commands in `DEPLOY.md` and continue with the remaining phases.**
4. The same acceptance check fails 3 times after genuinely different fixes. Write 3 options plus a recommendation in PROGRESS.md, then stop.

### A.4 Resumability
If the session is interrupted, the next session starts with: read `BUILD.md` + `PROGRESS.md`, run `git log --oneline`, and resume from the first phase not marked DONE.

---

## §B. THE SPEC

### B.1 North star
- **Problem:** people make big business bets on untested assumptions. A single AI answer accepts the premise, sounds confident and fabricates numbers.
- **Product:** a courtroom of 5 AI agents that puts an assumption on trial, grounds every claim in **retrieved quotes**, and issues a **rubric-scored verdict**, shown live as an evidence graph.
- **Success = 3 artifacts:** a deployed app a stranger can use; an evaluation table comparing the Court with a single AI; a public write-up.
- **Principles:**
  - The evidence graph is the product; the courtroom is packaging.
  - Grounding is the thesis. If our system fabricates, we've failed.
  - Show the seams: UNVERIFIED badges and rubric scores are visible.
  - Honest evaluation beats flattering evaluation: publish where the Court loses.
  - A fair baseline or no claim.

### B.2 Research basis (Paper → Product: an implementation, NOT a novel method)
| Role | Paper | Link | Implemented as |
|---|---|---|---|
| Base | AI Safety via Debate (Irving, Christiano & Amodei, 2018) | https://arxiv.org/abs/1805.00899 | Two opposing debaters plus a judge |
| Recent | DebateCV (He et al., 2025; WWW 2026) | https://arxiv.org/abs/2507.19090 | Bull vs Bear + a Judge weighing evidential strength; counter its known neutral-verdict bias |
| Recent | PROClaim (2026) | https://arxiv.org/abs/2603.28488 | Courtroom roles, progressive (staged) retrieval, evidence admission rules, role-switching |

Product additions (not research claims): premise trial, cause trial, quote-level Fact-checker, UNVERIFIED badge, rubric, "what would change the verdict", "3 questions to ask", and the live graph UI.

### B.3 Agents (5)
| Agent | Responsibility |
|---|---|
| 🔍 Researcher | Progressive retrieval: round 1 uses broad queries; round 2 targets gaps found by the debaters. Sources: DuckDuckGo (`ddgs` library) + Wikipedia REST API |
| 📈 Bull | Argues the assumption holds, using at most 3 evidence items |
| 📉 Bear | Argues the assumption is wrong or risky, using at most 3 evidence items |
| 🧮 Fact-checker | For every argument's claim, checks that the cited retrieved quote supports it → `verified \| mismatched \| unverifiable` |
| ⚖️ Judge | Scores VERIFIED evidence with the rubric and issues the verdict + rationale + verdict-changers + 3 questions |

### B.4 Pipeline (LangGraph)
```
input → classify (assumption | why-question)
  → STAGE 0  premise_trial: Researcher(r1) → Bull ⇄ Bear (2 rounds) → Fact-check → Judge(premise)
  → STAGE 1  cause_trial (only for why-questions AND premise not REFUTED):
             extract up to 3 candidate causes → for each cause: Researcher(r2) → Bull ⇄ Bear (1 round) → Fact-check → Judge(cause)
  → STAGE 3  final Judge → Report
```
- **Role-switching (PROClaim):** after each round, each debater outputs `stance: hold | concede | switch` + reason. A concession ends that side's arguments. A switch moves the agent to the other side for the next round (maximum 1 switch per trial). All of these are logged as graph events.
- **Anti-gish rule:** at most 3 evidence items per side per round. The code truncates any extra and logs a warning.
- **Unverified rule (code-enforced):** evidence with fact-check status ≠ `verified` gets `status="UNVERIFIED"` and is **removed from the Judge's scoring input**. It still appears in the report and graph.
- **Retrieval failure:** if no evidence is retrieved, the verdict is `INCONCLUSIVE` with reason `"retrieval failed"`, shown on screen. Never fabricate.

### B.5 Judge rubric + anti-neutral rule
Each VERIFIED evidence item is scored on:
- **Source tier:** 0–3 (3 = government / academic / official statistics; 2 = major media or industry reports; 1 = company blogs; 0 = unknown).
- **Recency:** 0–3 (3 = ≤ 1 year old; 2 = ≤ 3 years; 1 = ≤ 5 years; 0 = older or undated).

Each side is then scored:
- `side_score = mean(item source_tier + item recency) + corroboration (0–3: number of independent sources agreeing, capped) + contradiction_handling (0–3: did the side address the strongest opposing evidence?)`
- The side total is scaled to **0–12**.

The Judge LLM assigns the item-level scores. **Code computes the totals** (the LLM does not do the arithmetic).

**Anti-neutral rule:**
- `gap = |bull_total − bear_total|`.
- If `gap ≥ JUDGE_DECISIVE_GAP` (default 3) AND verified items ≥ 2, the verdict MUST be SUPPORTED (Bull higher) or REFUTED (Bear higher).
- If the Judge returns INCONCLUSIVE anyway, the router re-prompts once. If it still does, code overrides and logs `override=true`.
- **Confidence** = `min(0.95, 0.5 + gap/24 + 0.05 × corroboration)` (code-computed and displayed).

### B.6 Data schemas (Pydantic v2; mirror them as TypeScript types in the frontend)
```python
Evidence: id, side ("bull"|"bear"|"neutral"), claim_text, source_url, source_title,
          retrieved_quote, retrieved_at, factcheck ("verified"|"mismatched"|"unverifiable"),
          status ("VERIFIED"|"UNVERIFIED"), source_tier:int|None, recency:int|None
Argument: id, agent ("bull"|"bear"), round:int, text, evidence_ids:list[str],
          stance ("hold"|"concede"|"switch"), stance_reason
Verdict:  label ("SUPPORTED"|"REFUTED"|"INCONCLUSIVE"), bull_total:float, bear_total:float,
          gap:float, confidence:float, rationale:str (≤3 sentences, must cite rubric scores),
          verdict_changers:list[str], override:bool
CauseResult: cause_text, verdict:Verdict, evidence_ids
Report:   input_text, input_type, premise_verdict:Verdict, causes:list[CauseResult],
          evidence:list[Evidence], arguments:list[Argument], questions_to_ask:list[str] (exactly 3),
          cost:{llm_calls:int, tokens:int|None, seconds:float}
GraphEvent: seq:int, type ("node_add"|"edge_add"|"status"|"stance"|"verdict"), payload:dict, ts
TrialJob: job_id, status ("queued"|"running"|"done"|"error"), events:list[GraphEvent], report:Report|None, error:str|None
```
**Graph model:**
- Nodes: the input claim, each argument, each evidence item, each cause, and the verdict.
- Node colours: bull = green, bear = red, UNVERIFIED = grey with a badge, verdict = navy.
- Edges: evidence → argument (supports), argument → argument (rebuts), stance events (dashed).

### B.7 API (FastAPI)
- `GET /health` → `{"ok": true}`
- `POST /trial` with body `{"text": str}` → `{"job_id": str}` (the trial runs in a background task)
- `GET /trial/{job_id}` → the TrialJob. The frontend polls this every 1.5 seconds and renders any new events.
- `GET /examples` → a list of cached example trials, loaded from `backend/cached_cases/*.json`
- Enable CORS for the frontend origin (set via env). **Rate-limit `POST /trial` to 5 requests per IP per hour** to protect the free-tier quota.

### B.8 Tech stack (locked, do not change)
| Layer | Choice |
|---|---|
| LLM | Gemini via the official Google GenAI Python SDK. **Model name comes from env `GEMINI_MODEL`** (verify the current free-tier model name in Google AI Studio docs; do not hardcode). Fallback: Ollama (`LLM_PROVIDER=ollama`, `OLLAMA_MODEL`) behind the same `llm.py` interface |
| Orchestration | LangGraph |
| Backend | FastAPI + Uvicorn, Python 3.11 |
| Search | `ddgs` (DuckDuckGo) + Wikipedia REST API. Free, no keys |
| Frontend | Next.js (App Router, TypeScript) + React Flow (`@xyflow/react`) + Tailwind |
| Theme | Navy `#0A1F44`, white, one accent (`#3B82F6`); clean and minimal |
| Hosting | Backend: Hugging Face Spaces (Docker, port 7860). Frontend: Vercel |
| Tests | pytest (backend), Playwright smoke test optional |

### B.9 Environment (`.env`, never committed; create `.env.example` with blanks)
```
GEMINI_API_KEY=
GEMINI_MODEL=            # set from Google AI Studio docs
LLM_PROVIDER=gemini      # or ollama
OLLAMA_MODEL=
JUDGE_DECISIVE_GAP=3
MAX_EVIDENCE_PER_SIDE=3
FRONTEND_ORIGIN=http://localhost:3000
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

### B.10 Repo structure
```
assumption-court/
├── BUILD.md  PROGRESS.md  README.md  DEPLOY.md  .env.example  .gitignore
├── backend/
│   ├── app/ main.py config.py llm.py models.py retrieval.py rubric.py graph_events.py
│   │        pipeline/ state.py researcher.py debaters.py factcheck.py judge.py build.py
│   ├── prompts/ researcher.md bull.md bear.md factcheck.md judge.md classify.md causes.md baseline.md
│   ├── cached_cases/  logs/  tests/
│   ├── Dockerfile  requirements.txt
├── eval/
│   ├── data/ fever_100.jsonl  business_30.jsonl
│   ├── baseline.py  run_eval.py  grade_citations.py  report.md
└── frontend/ (Next.js app)
```

---

## §C. BUILD PHASES (execute P1 → P8)

### P1: Skeleton end-to-end
- Scaffold the repo (§B.10), `.gitignore`, `.env.example`, `requirements.txt`, `git init`.
- Write `llm.py` (a provider-agnostic `complete(prompt_file, vars) -> str` plus a structured-output helper that validates with Pydantic and retries once).
- **Check the API key first:** make one tiny Gemini call. If it fails → STOP (§A.3.1).
- Build a minimal LangGraph pipeline: classify → Bull → Bear → Judge on hardcoded text, with no retrieval yet.
- FastAPI `/health`, `POST /trial`, `GET /trial/{id}` with background execution.
- **Acceptance checks:**
  - `pytest` passes.
  - `curl -X POST localhost:8000/trial -d '{"text":"D2C brands fail because of ads"}'`, then polling, returns `status=done` with a Verdict JSON.

### P2: Retrieval + grounding (the thesis)
- `retrieval.py`: ddgs text search + Wikipedia summary/extract. Each result becomes Evidence with a **verbatim `retrieved_quote`** (1–3 sentences copied from the page or snippet; never paraphrased) plus the URL and timestamp.
- Researcher: derives 3–5 queries from the claim (round 1); round 2 targets the gaps.
- Fact-checker: for each argument's claim + cited evidence, returns verified / mismatched / unverifiable.
- Code enforces the unverified rule (§B.4). Handle retrieval failures gracefully.
- **Acceptance checks:**
  - **Fake-stat test (critical):** a Bull argument citing a fabricated statistic (inject it in a test fixture) must come back `UNVERIFIED` and be excluded from the Judge input. Write this as a pytest test and make it pass.
  - Retrieval returns ≥ 3 evidence items for "India is the world's largest milk producer". This is a live network test; mark it `@pytest.mark.network`.

### P3: Debate structure
- Bull/Bear with at most 3 evidence items per side per round, 2 rounds for the premise and 1 for each cause.
- Role-switching (§B.4) with stance output; graph events emitted.
- Classifier plus the cause-trial branch for why-questions (extract up to 3 causes).
- Judge input strips rhetoric: pass claims + evidence + stances, not the full prose. Instruct the Judge to ignore fluency.
- **Acceptance checks:**
  - Run 3 inputs: an assumption, a why-question and a clearly false claim. The JSON shows the debaters citing different evidence.
  - At least one concede/switch event occurs across the runs (with a clearly false claim, Bull should concede).
  - Save all three as `cached_cases/*.json`.

### P4: Judge rubric + report
- Implement §B.5 exactly: the LLM scores items, and `rubric.py` computes totals, gap, the anti-neutral override and confidence.
- Report assembly (§B.6), including verdict_changers and exactly 3 questions_to_ask.
- **Acceptance checks:**
  - Unit tests for `rubric.py` (gap maths, override logic, confidence formula).
  - The rationale text mentions the numeric scores.
  - On the clearly false claim, the verdict is REFUTED, not INCONCLUSIVE.

### P5: Baseline + evaluation harness
- `eval/baseline.py`: **same model, same retrieval budget** (same number of queries and results), ONE prompt, no agents. It outputs the same Verdict label set.
- **Data:**
  - `fever_100.jsonl`: 100 FEVER claims, stratified roughly 34/33/33 across SUPPORTS/REFUTES/NOT ENOUGH INFO. Map to SUPPORTED/REFUTED/INCONCLUSIVE. Obtain it from the official FEVER release or a reputable Hugging Face mirror. **If you can't obtain it after two attempts → STOP (§A.3.2).** Record the source URL in `eval/report.md`.
  - `business_30.jsonl`: create **30 business assumptions with `label: null`**. The human labels these before the business evaluation runs. Do not label them yourself.
- `run_eval.py`:
  - **Resumable:** append-only `eval/results.jsonl`; skips done IDs on restart; exponential backoff on HTTP 429.
  - Records per case: arm, predicted label, gold label, citations, llm_calls, seconds.
- `grade_citations.py`: an LLM grader (a separate prompt from the Judge) scores each (claim, quote) pair as supports / partial / does-not-support. It also outputs a random 20-case sample (seed 42) to `eval/manual_check.csv` for the human.
- **Acceptance checks:**
  - A 10-claim smoke run on both arms completes.
  - Killing the runner midway and restarting resumes correctly.
  - Tune `JUDGE_DECISIVE_GAP` on the smoke run only, then freeze it: `git tag eval-v1`.
- **Do NOT run the full 130 inside this build.** It's rate-limited; the human runs it later with `python eval/run_eval.py --all` (document this in README).

### P6: Frontend
- Next.js page layout, top to bottom:
  1. Agent bench (5 agents with static avatars).
  2. Stage area with React Flow graph.
  3. Verdict card.
  4. Chat-style input bar at the bottom.
- **Flow:** submit → `POST /trial` → poll → render events in order. The active agent's avatar highlights (a CSS glow; no character animation). Nodes and edges are added as events arrive.
- Evidence nodes show a tooltip with the verbatim quote and a source link. UNVERIFIED nodes are grey with a badge.
- Verdict card shows: label, confidence, Bull vs Bear scores, rationale, verdict-changers, and the 3 questions.
- An "Examples" dropdown loads `/examples` (cached cases) and replays their events. This is required for rate-limit-proof demos.
- Include loading, error and retrieval-failed states. It must be mobile-safe.
- **Acceptance checks:**
  - `npm run build` succeeds.
  - With the backend running, a live trial renders the graph and verdict card.
  - The example replay works with the backend stopped. Cache examples as static JSON in `frontend/public/examples/` as well.

### P7: Hardening + deploy prep
- Backend `Dockerfile` for HF Spaces (port 7860; reads env from Spaces secrets). Test it with `docker build` locally if Docker is available; otherwise note this in PROGRESS.md.
- Frontend: `NEXT_PUBLIC_API_BASE` from env; a Vercel-ready config.
- Add rate limiting on `/trial`, a request timeout (120 seconds per trial) and a friendly error when the quota is exhausted ("Try an example").
- `DEPLOY.md`: exact step-by-step commands for the human to create the HF Space, set its secrets, push, and import the frontend into Vercel with env vars. **Do not attempt logins.**
- `README.md` (30-second test):
  1. What it is.
  2. Why it matters.
  3. Papers credited ("implementation, not a novel method").
  4. Architecture diagram (a Mermaid block).
  5. How to run locally.
  6. Evaluation section with a placeholder table + "Where the Court loses" section (filled after the full evaluation).
  7. Cost per case.
- **Acceptance checks:**
  - A fresh clone + `.env` + the README's commands runs locally.
  - All tests pass.

### P8: Final verification + handoff
- Run the full test suite, including the fake-stat test.
- Run 1 live trial end-to-end and save it as an additional cached example.
- Produce `HANDOFF.md` listing:
  - (a) What was built.
  - (b) Known issues.
  - (c) **Human to-do list:** deploy per DEPLOY.md; label business_30; run the full evaluation; do the manual 20-case citation check; fill the README evaluation table; record the 90-second demo; post on LinkedIn.
- Update the Status Log, `git commit`, and `git tag v1.0`.
- **Final message to the human:** a summary + the HANDOFF.md checklist.

---

## §D. CODE-REVIEW CHECKLIST (verify at the end of P2, P4, P6 and P8)
- [ ] Every evidence item has a verbatim retrieved quote.
- [ ] UNVERIFIED evidence is visually distinct and excluded from Judge scoring.
- [ ] At most 3 evidence items per side per round.
- [ ] Judge output has rubric scores, rationale citing scores, verdict-changers and 3 questions.
- [ ] The anti-neutral rule is enforced in code; the threshold is frozen at `eval-v1`.
- [ ] Role-switch events are logged and visible in the graph.
- [ ] The baseline uses the identical model and retrieval budget.
- [ ] Prompts live in `prompts/`; every LLM call is logged.
- [ ] No invented citations; retrieval failures are shown on screen.
- [ ] The evaluation runner is resumable and handles 429s.

## §E. SCOPE KILL LIST (if blocked, cut in this order)
1. Avatar highlighting → plain text labels.
2. Cause trial → sub-claim nodes inside the premise trial.
3. Live trials in the demo → cached examples only.
4. Business evaluation 30 → 15.
5. **NEVER CUT:** quote grounding, UNVERIFIED rule, rubric + anti-neutral rule, fair baseline, evaluation harness, paper credits, cached examples.

## §F. STATUS LOG (kept in PROGRESS.md, one row per phase)
| Phase | Status (TODO/DONE/BLOCKED) | Done | Issues | Next |
|---|---|---|---|---|
| P1 | TODO | | | |
| P2 | TODO | | | |
| P3 | TODO | | | |
| P4 | TODO | | | |
| P5 | TODO | | | |
| P6 | TODO | | | |
| P7 | TODO | | | |
| P8 | TODO | | | |

---
*Built by Amiya Manas Singh: Paper → Product series.*
