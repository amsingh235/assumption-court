# PROGRESS: Assumption Court

## Status Log
| Phase | Status (TODO/DONE/BLOCKED) | Done | Issues | Next |
|---|---|---|---|---|
| P1 | DONE (fake LLM) | Scaffold, `llm.py` (gemini/ollama/fake + JSON retry + call log), LangGraph pipeline, FastAPI `/health` `/trial` `/examples`, curl check passes | No `GEMINI_API_KEY` yet, so the "tiny Gemini call" check is PENDING (human) | Add `.env`, run `pytest -m llm` |
| P2 | DONE (offline) | ddgs + Wikipedia retrieval with verbatim quotes, Researcher (broad/gap/cause), Fact-checker, code-enforced UNVERIFIED rule, fake-stat test passes | Sandbox network blocks DuckDuckGo/Wikipedia; `pytest -m network` PENDING (human) | Run network test locally |
| P3 | DONE (fake LLM) | 2-round premise / 1-round cause debates, anti-gish cap, concede/switch with graph events, classifier + cause branch, rhetoric-stripped Judge input, 3 cached cases | Cached cases are fake-mode placeholders | Regenerate with the real model |
| P4 | DONE | `rubric.py` (totals, gap, anti-neutral re-prompt + override, confidence) with unit tests; report with exactly 3 questions; rationale cites scores | "Clearly false → REFUTED" holds in fake mode only; real-model check PENDING | Verify with real key |
| P5 | DONE (harness) | Fair baseline (same model, Court's per-case query count, 1 prompt), resumable `run_eval.py` with 429 backoff, `grade_citations.py` + manual sample, `fetch_fever.py`, `business_30.jsonl` (unlabelled) | FEVER download blocked by sandbox network (§A.3.2): the fetch script is ready for the human. 10-claim smoke + resume tested on a throwaway fixture with the fake LLM. `JUDGE_DECISIVE_GAP` tuning and `eval-v1` tag PENDING | Human: fetch FEVER, smoke run, tune, tag |
| P6 | DONE | Pixel-agent courtroom UI (see notes), transcript, evidence graph, ruling card, example replay offline, `npm run build` + lint clean | — | — |
| P7 | DONE | Dockerfile (HF Spaces, uid 1000, port 7860), built and smoke-tested locally; DEPLOY.md; README; rate limit, 120 s timeout, friendly quota error | Local docker test needed a test-only CA layer for the sandbox proxy (not in the real Dockerfile) | Human: deploy per DEPLOY.md |
| P8 | PARTIAL | Full offline suite passes; HANDOFF.md written | Live end-to-end trial with the real model and `v1.0` tag PENDING (need key + network) | Human: see HANDOFF.md |

## Phase notes

### Environment constraints during the build
- No `GEMINI_API_KEY`. The user asked to build everything with fake/mock Gemini calls, which is `LLM_PROVIDER=fake` (`backend/app/fake_llm.py`). It is deterministic and heuristic, and it is **not** a model. Every report records `cost.llm_provider`, and the UI shows an "offline placeholder" banner.
- The sandbox network policy blocks DuckDuckGo, Wikipedia, Hugging Face and fever.ai (only PyPI and npm are reachable), so `RETRIEVAL_PROVIDER=fake` was added for offline development. Its sources are labelled `[FAKE OFFLINE SOURCE]` and use the reserved `.invalid` TLD.

### P5
- ASSUMPTION: FEVER URLs `https://fever.ai/download/fever/shared_task_dev.jsonl` and `paper_dev.jsonl` (official release page). The script accepts `--url` or a local file if they move.
- Baseline retrieval budget = the number of queries the Court used on the same case (read from `results.jsonl`), with the same results per query. Queries are templated from the claim, so the baseline makes exactly 1 LLM call.

### P6 (user-directed change)
- The user rejected the first dashboard-style UI and asked for a desktop-first, Claude-style pixel-agent look (dark theme, cream tiles, clay sprites, "AGENTS" tree header) where agents visibly come together, talk and argue. This **replaces the BUILD.md P6 rule "CSS glow; no character animation"**. Agents walk to the floor, speak in typewriter bubbles, shake on rebuttal, concede with a white flag or switch podiums. The fact-checker stamps exhibits and the judge slams a ruling banner. `prefers-reduced-motion` disables movement.
- The Silkscreen pixel font loads from Google Fonts at runtime and falls back to monospace. It could not load inside the sandbox (TLS proxy), so the screenshots show the fallback.

### P7
- `docker build` from the sandbox needed `--network host`, proxy build args and a CA layer. That was done in a scratch copy only; the committed Dockerfile is the plain one for Spaces.
