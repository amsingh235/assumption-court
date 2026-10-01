# ⚖️ Assumption Court

**Put your assumption on trial.** Five AI agents debate it live, and every claim needs a retrieved quote or it's thrown out.

👉 **Live demo:** https://assumption-court-theta.vercel.app

![Assumption Court demo](assumption-court/docs/demo.png)

## Why
Ask a single chatbot whether your idea is good and it usually agrees, confidently, sometimes with an invented statistic. Assumption Court makes AI argue both sides and only counts what it can prove.

## The court
| Agent | Role |
|---|---|
| 🔍 Researcher | Searches the web and Wikipedia and brings back exact quotes |
| 📈 Bull | Argues the assumption holds |
| 📉 Bear | Argues it doesn't |
| 🧮 Fact-checker | Throws out any claim its quote doesn't support |
| ⚖️ Judge | Scores the evidence, not the eloquence: SUPPORTED, REFUTED or INCONCLUSIVE |

**One rule: no quote, no claim.** Unverified arguments are greyed out and never reach the judge.

Every ruling also tells you **what would change the verdict** and **3 questions to ask before you bet on it**.

## Research it's built on
- *AI Safety via Debate*, Irving et al. (2018)
- *DebateCV* (2025)
- *PROClaim* (2026)

## Stack
LangGraph + FastAPI (backend, Render) · Next.js (frontend, Vercel) · Groq / Gemini LLMs · DuckDuckGo + Wikipedia retrieval · ₹0 to run

## Run it yourself
See [`assumption-court/DEPLOY.md`](assumption-court/DEPLOY.md) for setup and deployment, and `assumption-court/.env.example` for configuration.

## Note
The demo runs on free tiers. The first trial may take about 50 seconds while the server wakes up. If the free AI quota runs out, use **Replay an example**.

---
Built by Amiya Singh as build #1 of **Paper → Product**: turning AI research papers into things you can click on.
