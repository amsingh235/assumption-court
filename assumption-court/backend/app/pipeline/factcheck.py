"""Fact-checker: does each cited verbatim quote actually support the claim it is cited for?

The UNVERIFIED rule is enforced here in code, not by the LLM: anything whose fact-check is not
`verified` becomes status=UNVERIFIED and is excluded from Judge scoring (it stays in the report/graph).
"""
from __future__ import annotations

from app.llm import complete_structured
from app.models import Evidence, FactCheckOut
from app.pipeline.state import Trial


def enforce_unverified(ev: Evidence) -> Evidence:
    ev.status = "VERIFIED" if ev.factcheck == "verified" else "UNVERIFIED"
    if ev.status == "UNVERIFIED":
        ev.source_tier = None
        ev.recency = None
    return ev


def verified_only(evidence: list[Evidence]) -> list[Evidence]:
    """Judge scoring input. Re-applies the rule so a stale status can never leak through."""
    return [ev for ev in evidence if enforce_unverified(ev).status == "VERIFIED"]


def factcheck_all(trial: Trial, evidence: list[Evidence], stage: str) -> list[Evidence]:
    if evidence:
        trial.events.status("factchecker", f"Checking {len(evidence)} quotes against their claims", stage)
    for ev in evidence:
        trial.check_deadline()
        out = complete_structured("factcheck", {
            "claim_text": ev.claim_text, "quote": ev.retrieved_quote, "source_title": ev.source_title,
        }, FactCheckOut)
        ev.factcheck = out.factcheck
        enforce_unverified(ev)
        trial.events.evidence_update(ev, stage, out.reason)
    return evidence
