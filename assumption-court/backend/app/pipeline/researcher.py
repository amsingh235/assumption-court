"""Researcher: progressive retrieval (PROClaim). Round 1 = broad queries; round 2 = targeted gaps."""
from __future__ import annotations

from typing import Literal

from app.config import get_settings
from app.llm import complete_structured
from app.models import QueriesOut
from app.pipeline.state import Trial
from app.retrieval import PoolItem, retrieve


def research(
    trial: Trial,
    claim: str,
    stage: str,
    mode: Literal["broad", "gap", "cause"],
    notes: list[str] | None = None,
) -> list[PoolItem]:
    """Derive queries with the LLM, retrieve, assign pool ids and append to trial.pool. Returns new items."""
    settings = get_settings()
    budget = settings.queries_round1 if mode == "broad" else settings.queries_gap
    trial.events.status("researcher", f"Planning {mode} queries", stage)
    out = complete_structured(
        "researcher",
        {"claim": claim, "mode": mode, "max_queries": str(budget), "notes": notes or []},
        QueriesOut,
    )
    queries = [q.strip() for q in out.queries if q.strip()][:budget]
    if not queries:
        queries = [claim]
    trial.retrieval_queries += len(queries)
    trial.events.status("researcher", f"Searching: {' | '.join(queries)}", stage)

    items, errors = retrieve(queries)
    trial.retrieval_errors.extend(errors)
    known = {p.source_url for p in trial.pool}
    fresh = []
    for item in items:
        if item.source_url in known:
            continue
        item.id = trial.new_id("pool")
        fresh.append(item)
    trial.pool.extend(fresh)
    trial.events.status("researcher", f"Retrieved {len(fresh)} new sources ({len(errors)} source errors)", stage)
    return fresh
