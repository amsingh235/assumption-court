# ⚖️ ASSUMPTION COURT — MASTER BUILD FILE
> **Read this entire file before doing anything. Re-read it every morning, at every phase gate, and whenever stuck.**
> This file is the single source of truth. If the code, the plan, and this file disagree, this file wins until you deliberately edit it.

---

## 0. HOW TO USE THIS FILE (META-RULES — NON-NEGOTIABLE)

Paste the block below at the start of every AI-assisted work session:

```
You are my senior engineer pair-programming on Assumption Court (project spec below).
RULES:
1. Read the full spec file before writing any code.
2. Never invent numbers, sources, or API behaviors — if unsure, say "assumption" and flag it.
3. Every phase must end by updating the Status Log (Section 12) in this file.
4. When I say "PHASE GATE", stop coding, re-read this file, and verify we're compliant before continuing.
5. Prefer working and boring over clever and broken.
6. If a task exceeds 2 hours of friction, STOP and escalate to me with options — do not rabbit-hole.
```

**Human rules (Amiya):**
- One session = one phase (or less). Never multitask phases.
- End every day by updating the Status Log, even if the update is "blocked because X".
- The demo video records on Day 9. No exceptions. Ship > perfect.

---

## 1. THE NORTH STAR

**Problem:** People make big business bets on untested assumptions. Single AI answers accept the premise, sound confident, and fabricate numbers.

**Product:** A courtroom of 5 AI agents that puts an assumption on trial, grounds every claim in retrieved evidence, and issues a rubric-scored verdict.

**Audience:** LinkedIn (hiring managers, FD eng teams, AI founders) + masters admissions committees.

**Success = three artifacts:**
1. A live deployed app (Hugging Face Spaces + Vercel) that survives a stranger trying it.
2. An eval table: Court vs Single AI on 130 claims (accuracy, citation accuracy, cost).
3. A public write-up (LinkedIn article / mini tech report).

**NOT success:** cute animations, agent count, buzzwords.

---

## 1A. RESEARCH BASIS (PAPER → PRODUCT)

This project is part of the "Paper → Product" series: we **implement published research as a working product**. We make no novelty claim on the method. Our additions are product features.

| Role | Paper | Link | What we implement from it |
|---|---|---|---|
| **Base** | AI Safety via Debate (Irving, Christiano & Amodei, 2018) | https://arxiv.org/abs/1805.00899 | The core principle: two agents argue opposing sides and a judge decides, so the truth is easier to surface than from a single answer |
| **Recent #1** | DebateCV: Debate-driven Claim Verification with Multiple LLM Agents (He et al., 2025; WWW 2026) | https://arxiv.org/abs/2507.19090 | Bull vs Bear opposing debaters + a Judge who weighs **evidential strength**. We also inherit its known failure mode: zero-shot moderators lean towards neutral verdicts, which we counter in §3 |
| **Recent #2** | PROClaim: Courtroom-Style Multi-Agent Debate with Progressive RAG and Role-Switching (2026) | https://arxiv.org/abs/2603.28488 | Courtroom roles, **progressive (staged) retrieval** for the Researcher, evidence admission rules, and **role-switching** to prevent premature convergence and shared bias |

**Our product additions (not research claims):** premise trial, cause trial, quote-level Fact-checker with the UNVERIFIED badge, rubric-scored Judge, "what would change the verdict", "3 questions to ask", and the live evidence graph UI.

**How to describe it publicly:** "Implemented DebateCV + PROClaim ideas as a live product; evaluated against a single-AI baseline." Never say "novel method".

---

## 2. CORE PRINCIPLES (THINK WITH THESE)

1. **The evidence graph is the product. The courtroom is packaging.** Every hour spent on visuals must serve the graph.
2. **Hallucination is our enemy — including our own.** If our Researcher fabricates, we are the thing we're critiquing. Grounding is not a feature; it's the thesis.
3. **Show the seams.** The "unverified" badge and the Judge's rubric score build more trust than a confident verdict.
4. **A posted 80% project beats a perfect project in drafts forever.** Day 9 = demo recording. Ship, then iterate publicly.
5. **Honest eval > flattering eval.** Publish where the Court loses. That post gets shared.
6. **Fair baseline or no claim.** Court vs Single AI only counts with the same model + same retrieval budget.

---

## 3. ARCHITECTURE

```
User input (assumption / "why" question)
        │
        ▼
┌─────────────────────────────────────────────┐
│  STAGE 0: PREMISE TRIAL                      │
│  Researcher: retrieve evidence FOR/AGAINST   │
│  whether the assumption is even true         │
├─────────────────────────────────────────────┤
│  STAGE 1: CAUSE TRIAL (sub-claims as nodes)  │
│  For each major reason: Bull vs Bear debate  │
│  max 3 evidence items per side (anti-gish)   │
│  ROLE-SWITCH: a debater may CONCEDE or SWITCH│
│  when evidence turns against it (PROClaim)   │
├─────────────────────────────────────────────┤
│  STAGE 2: FACT-CHECK (quote-level)           │
│  Every claim → retrieved quote required      │
│  No quote → "UNVERIFIED" badge, Judge skips  │
├─────────────────────────────────────────────┤
│  STAGE 3: JUDGE                              │
│  Rubric-scored, rationale shown, verdict:    │
│  SUPPORTED / REFUTED / INCONCLUSIVE (+conf.) │
│  ANTI-NEUTRAL RULE: if rubric gap ≥ threshold│
│  Judge MUST rule SUPPORTED or REFUTED        │
│  (counters DebateCV's neutral-bias finding)  │
└─────────────────────────────────────────────┘
        │
        ▼
Report: verdict • evidence for/against (with sources)
        • what would change the verdict • 3 questions to ask
```

**Stage → paper mapping:** Stage 0 retrieval = PROClaim progressive RAG · Stage 1 = DebateCV debaters + PROClaim role-switching · Stage 3 = Irving/DebateCV judge + our rubric.

**Anti-neutral rule (exact):** compute `gap = |bull_rubric_total − bear_rubric_total|` over VERIFIED evidence only. If `gap ≥ JUDGE_DECISIVE_GAP` (default 3 on a 0–12 scale), INCONCLUSIVE is not allowed. INCONCLUSIVE is valid only when the gap is small OR fewer than 2 verified evidence items exist in total. Tune the threshold on the 10-claim smoke run (Day 5), then **freeze it** before the full eval.

**Graph model (React Flow):** nodes = claims; node color = for/against/unverified; edges = evidence links; verdict node at bottom. The graph IS the debate made visible.

---

## 4. TECH STACK (LOCKED — DO NOT UPGRADE MID-BUILD)

| Layer | Choice | Why |
|---|---|---|
| LLM | Gemini free tier (fallback: Ollama local) | Zero cost |
| Orchestration | LangGraph | State machines, checkpoints |
| Backend | FastAPI | Deploys on Spaces |
| Search | DuckDuckGo (ddgs lib) + Wikipedia API | Free, no keys |
| Frontend | Next.js + React Flow + Tailwind | Vercel free tier |
| Navy blue + white theme | #0A1F44 navy, white, one accent | Per brand |
| Hosting | HF Spaces (backend) + Vercel (frontend) | $0 |

**MCP: SKIP for v1.** Agents call APIs directly — deploys cleanly. (Optional later: Brave Search MCP / Playwright MCP for local dev tooling only.)

---

## 5. THE 9-DAY PLAN

### DAY 1 — Skeleton that runs end-to-end (ugly is fine)
- [ ] FastAPI + LangGraph: hardcoded-agent flow for ONE test assumption ("D2C brands fail because of ads")
- [ ] One LLM call per agent role via Gemini
- [ ] Terminal output: verdict + evidence list
- **Gate 1:** `curl` the endpoint, get a structured verdict JSON. Nothing else matters today.

### DAY 2 — Retrieval & grounding (the thesis)
- [ ] Researcher stage: ddgs + Wikipedia queries derived from the claim
- [ ] Evidence objects: `{claim, source_url, retrieved_quote, retrieved_at}`
- [ ] Fact-checker prompt: verify quote-level match; output `verified | mismatched | unverifiable`
- [ ] Hard rule enforced in code: unverified claims carry `"status": "UNVERIFIED"` and Judge prompt forbids weighing them
- **Gate 2:** Feed a claim with a fake stat. It MUST come back UNVERIFIED. Test until it does.

### DAY 3 — Debate structure
- [ ] Bull/Bear with max 3 evidence items each (reject extras)
- [ ] Anti-rhetoric rule: Judge scores argument STRENGTH separately from fluency (strip adjectives in Judge input, or instruct Judge to ignore style)
- [ ] Role-switching (PROClaim): after each round, each debater outputs `{stance: hold | concede | switch, reason}`; concessions are shown as graph events
- [ ] Premise trial → cause trial as graph nodes (can be JSON only today)
- **Gate 3:** Run 3 assumptions, read the JSON debates. Do the agents actually disagree using evidence? Does at least one debater concede when shown strong counter-evidence?

### DAY 4 — Judge rubric + report
- [ ] Rubric: source tier (gov/academic > major media > blog), recency, independent corroborations, contradiction handling
- [ ] Judge output: verdict + per-criterion scores + 3 sentences of rationale + "what would change my mind"
- [ ] Anti-neutral rule in code (see §3): the router rejects an INCONCLUSIVE that breaks the rule and re-prompts the Judge once
- [ ] Report schema: verdict, evidence for/against w/ sources, verdict-changers, 3 questions to ask
- **Gate 4:** Verdict rationale must cite the rubric scores. No vibes. On 5 lopsided test claims, the Judge must NOT return INCONCLUSIVE.

### DAY 5 — Baseline single-AI + eval harness
- [ ] Baseline: same Gemini model, same retrieval budget, ONE prompt, no agents
- [ ] Dataset: **100 FEVER claims** (labels SUPPORTS / REFUTES / NOT ENOUGH INFO map 1:1 to SUPPORTED / REFUTED / INCONCLUSIVE; stratified ~34/33/33) + 30 business assumptions you write and label honestly **before** running any system
- [ ] Runner script: batch both systems, log accuracy / citation accuracy / cost per run
- [ ] **Resumable runner:** writes each result to `eval/results.jsonl` immediately; on restart, skips completed claim IDs; exponential backoff on 429 rate-limit errors
- [ ] **Rate-limit budget:** 130 claims × 2 arms × ~10 calls ≈ 2,600 LLM calls. Spread across Days 5–7 within free-tier daily limits, OR run the batch on Ollama locally (same model for BOTH arms, whichever you choose)
- [ ] Freeze `JUDGE_DECISIVE_GAP` and all prompts after the smoke run (git tag `eval-v1`)
- **Gate 5:** 10-claim smoke run on both. Numbers logged. Runner resumes correctly after a forced kill.

### DAY 6 — Full eval + frontend scaffold
- [ ] Continue the full 130-claim run in the background (resumable; finishes by end of Day 7). Fill the results table when complete.
- [ ] Next.js app: chat input → POST backend → poll job status → render graph (React Flow) + report
- **Gate 6:** Stranger (friend) can type an assumption and see a graph. Backend can still be terminal-ugly.

### DAY 7 — Frontend polish (budgeted, hard stop) + finish eval run
- [ ] Static avatars + typed dialogue for agents (NO character animation beyond CSS fades)
- [ ] Graph: for/against/unverified colors, verdict node, evidence tooltips with quotes
- [ ] Mobile-safe, loading states, error states
- [ ] Confirm the eval run is complete; do the manual citation check (§8)
- **Gate 7:** Would YOU stop scrolling for this in 3 seconds? If not, fix the graph view only. Eval table filled.

### DAY 8 — Hardening + deployment
- [ ] Deploy backend to Spaces, frontend to Vercel
- [ ] Cache 3–4 pre-run cases (Gemini free-tier rate limits WILL hit live demos)
- [ ] README: 30-second version (what/why/results table/demo GIF) + architecture diagram
- [ ] Cost table: $ per case
- **Gate 8:** Demo works from your phone on cellular. Friend can run it without your help.

### DAY 9 — RECORD + SHIP (immovable)
- [ ] Record 90-sec demo: one business assumption tried live, graph forming, verdict, results table
- [ ] Post #1: launch (demo video + results table)
- [ ] Update Status Log. This file becomes your retrospective input.

---

## 6. ENGINEERING RULES (CODE REVIEW CHECKLIST — APPLY AT EVERY PHASE GATE)

- [ ] Every evidence object has a retrieved quote, not a paraphrase
- [ ] UNVERIFIED claims are visually distinct and excluded from Judge weighing
- [ ] Max 3 evidence items per debater side
- [ ] Judge output contains rubric scores + rationale + verdict-changers
- [ ] Baseline uses identical model + retrieval budget
- [ ] All prompts are in versioned files (prompts/), never inline magic strings
- [ ] Every LLM call logged: tokens, latency, cost, raw response
- [ ] No invented citations anywhere — if retrieval fails, the system says so on screen
- [ ] Role-switch events (concede/switch) are logged and visible in the graph
- [ ] Anti-neutral rule enforced in code, with the threshold frozen before the full eval
- [ ] Eval runner is resumable and handles 429s; results are append-only JSONL

---

## 7. HOW TO THINK WHEN STUCK (DECISION FRAMEWORK)

Apply in order; stop at first resolution:

1. **Re-read Section 2.** Which principle applies? It usually answers it.
2. **Shrink the question.** "Deploy pipeline broken" → "does `curl localhost:8000/health` respond?" Fix the smallest verifiable step.
3. **2-Hour Rule.** Same wall for 2 hours? Stop. Escalate with 3 options + your recommendation. Do not rabbit-hole.
4. **Boring wins.** Two solutions? Pick the one with more Stack Overflow answers.
5. **Cut, don't patch.** Feature dragging? Cut it. The graph, the grounding, the eval survive everything else.
6. **"PHASE GATE"** — stop, re-read this file, verify compliance, then continue.

---

## 8. EVAL PROTOCOL

- **Dataset:** 100 FEVER claims (stratified across the 3 labels) + 30 self-labeled business claims (labels written before any run)
- **Metrics:** claim accuracy | citation accuracy | INCONCLUSIVE rate (watch for neutral bias) | concession rate | cost per case
- **Citation accuracy scoring:**
  1. **Automatic:** an LLM grader (a different model or prompt from the Judge) checks each (claim, retrieved quote) pair and scores it `supports | partial | does-not-support`.
  2. **Manual:** you hand-check a random 20 cases (fixed seed) and report the agreement % between you and the LLM grader.
  3. Publish both numbers. If agreement is < 80%, report the manual number as primary.
- **Rules:** same model both arms; same retrieval budget; run each claim once (no cherry-picking runs); prompts and thresholds frozen at git tag `eval-v1`
- **Publish:** full table in README + the failures. "Where the Court loses" section is mandatory.
- **Claim honestly:** "preliminary, n=130" — never generalize beyond the data.

---

## 9. LINKEDIN BUILD-IN-PUBLIC PLAN

| Day | Post (short, honest, one idea each) |
|---|---|
| Day 2 | "My Researcher agent fabricated a stat. Here's the quote-level grounding fix." |
| Day 4 | "Gave my Judge a rubric so it can't vibes-rule. The scores are now visible." |
| Day 5 | "Setting up the eval: Court vs one AI, same model, same budget. Fair or it doesn't count." |
| Day 8 | "Where the Court embarrassingly lost (and what I'm fixing first)." |
| Day 9 | **Launch:** 90-sec demo + results table + GitHub + write-up link |

Tone: show the seam, name the failure, state the fix. No hype adjectives.

---

## 10. DEFINITION OF DONE

- [ ] Stranger can use the deployed app unassisted
- [ ] Fake-stat test returns UNVERIFIED (re-run it on Day 9)
- [ ] 130-claim eval table published, including failures, INCONCLUSIVE rate and manual citation check
- [ ] README credits the 3 papers and states "implementation, not a novel method"
- [ ] README passes the 30-second test
- [ ] Demo video posted
- [ ] This file's Status Log complete

---

## 11. SCOPE KILL LIST (IF BEHIND SCHEDULE, CUT IN THIS ORDER)

1. Agent avatars/animation → static labels
2. Cause trial stage → collapse into premise trial with sub-claim nodes
3. Live demo → cached cases only
4. Business set 30 → 15 claims (keep all 100 FEVER claims)
5. NEVER CUT: quote grounding, UNVERIFIED badge, rubric, anti-neutral rule, fair baseline, eval table, paper mapping (§1A), Day 9 ship date

---

## 12. STATUS LOG (UPDATE DAILY — EVEN IF "BLOCKED")

| Day | Date | Done | Blocked on | Next action |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |
| 8 | | | | |
| 9 | | | | |

---

*Built by Amiya Manas Singh — "Ace of all trades, master of many." Ship it.*
