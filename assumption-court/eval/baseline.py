"""Single-AI baseline: SAME model, SAME retrieval budget, ONE prompt, no agents.

Budget: the same number of search queries the Court used on that case (passed in by run_eval.py),
each with the same RESULTS_PER_QUERY. Queries are built deterministically from the claim, so the
baseline spends exactly one LLM call.
"""
from __future__ import annotations

import time
from typing import Optional

import _paths  # noqa: F401
from app.config import get_settings
from app.llm import CallStats, complete_structured, current_stats
from app.models import BaselineOut
from app.retrieval import retrieve

QUERY_TEMPLATES = ["{c}", "{c} statistics", "evidence against {c}", "{c} study", "{c} data", "{c} report",
                   "is it true that {c}", "{c} criticism"]


def baseline_queries(claim: str, n: int) -> list[str]:
    claim = claim.rstrip(".?!")
    return [QUERY_TEMPLATES[i % len(QUERY_TEMPLATES)].format(c=claim) for i in range(max(1, n))]


def run_baseline(claim: str, n_queries: Optional[int] = None) -> dict:
    settings = get_settings()
    n = n_queries or (settings.queries_round1 + settings.queries_gap)
    stats = CallStats()
    token = current_stats.set(stats)
    start = time.monotonic()
    try:
        pool, errors = retrieve(baseline_queries(claim, n))
        for i, item in enumerate(pool, start=1):
            item.id = f"pool-{i}"
        if not pool:
            return {"label": "INCONCLUSIVE", "rationale": "retrieval failed", "citations": [], "llm_calls": 0,
                    "seconds": round(time.monotonic() - start, 2), "retrieval_queries": n}
        out = complete_structured("baseline", {"claim": claim, "pool": [
            {"pool_id": p.id, "title": p.source_title, "url": p.source_url, "quote": p.retrieved_quote} for p in pool
        ]}, BaselineOut)
    finally:
        current_stats.reset(token)
    by_id = {p.id: p for p in pool}
    citations = [{"claim_text": c.claim_text, "quote": by_id[c.pool_id].retrieved_quote, "url": by_id[c.pool_id].source_url}
                 for c in out.citations if c.pool_id in by_id]
    return {"label": out.label, "rationale": out.rationale, "citations": citations, "llm_calls": stats.llm_calls,
            "seconds": round(time.monotonic() - start, 2), "retrieval_queries": n}
