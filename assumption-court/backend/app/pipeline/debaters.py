"""Bull vs Bear debate with anti-gish cap and PROClaim role-switching."""
from __future__ import annotations

from typing import Callable, Optional

from app.config import get_settings
from app.llm import complete_structured
from app.models import Argument, DebaterOut, Evidence
from app.pipeline.state import Trial
from app.retrieval import PoolItem

AGENTS = ("bull", "bear")
GapResearch = Callable[[list[str]], list[PoolItem]]


def _pool_view(pool: list[PoolItem]) -> list[dict]:
    return [{"pool_id": p.id, "title": p.source_title, "url": p.source_url, "quote": p.retrieved_quote} for p in pool]


def _arg_view(arg: Optional[Argument], evidence: dict[str, Evidence]) -> dict | str:
    if arg is None:
        return "(none yet)"
    return {"text": arg.text, "claims": [evidence[i].claim_text for i in arg.evidence_ids if i in evidence],
            "stance": arg.stance}


def run_debate(
    trial: Trial,
    claim: str,
    stage: str,
    pool: list[PoolItem],
    rounds: int,
    claim_node: str,
    gap_research: Optional[GapResearch] = None,
) -> tuple[list[Argument], list[Evidence]]:
    """Run `rounds` rounds. Returns the new arguments and evidence (evidence not yet fact-checked)."""
    max_ev = get_settings().max_evidence_per_side
    side_of = {"bull": "bull", "bear": "bear"}  # agent -> side it currently argues
    active = {"bull": True, "bear": True}
    switch_used = False
    last: dict[str, Optional[Argument]] = {"bull": None, "bear": None}
    arguments: list[Argument] = []
    evidence: list[Evidence] = []
    by_id: dict[str, Evidence] = {}

    for round_no in range(1, rounds + 1):
        trial.check_deadline()
        gap_notes: list[str] = []
        for agent in AGENTS:
            if not active[agent]:
                continue
            side = side_of[agent]
            opponent = "bear" if agent == "bull" else "bull"
            trial.events.status(agent, f"Round {round_no}: arguing the {side} side", stage)
            out = complete_structured(side, {
                "claim": claim, "round": str(round_no), "rounds": str(rounds), "max_evidence": str(max_ev),
                "pool": _pool_view(pool), "own_previous": _arg_view(last[agent], by_id),
                "opponent_last": _arg_view(last[opponent], by_id),
            }, DebaterOut)

            pool_by_id = {p.id: p for p in pool}
            citations = [c for c in out.citations if c.pool_id in pool_by_id]
            if len(citations) < len(out.citations):
                trial.warn(f"{stage} r{round_no} {agent}: dropped {len(out.citations) - len(citations)} citation(s) to unknown pool ids")
            if len(citations) > max_ev:  # anti-gish rule
                trial.warn(f"{stage} r{round_no} {agent}: truncated {len(citations)} evidence items to {max_ev}")
                citations = citations[:max_ev]

            arg = Argument(id=trial.new_id("arg"), agent=agent, round=round_no, text=out.text,
                           stance=out.stance, stance_reason=out.stance_reason)
            trial.events.argument_node(arg, stage, side)
            trial.events.edge(arg.id, claim_node, "about")
            if last[opponent] is not None:
                trial.events.edge(arg.id, last[opponent].id, "rebuts")
            for cite in citations:
                src = pool_by_id[cite.pool_id]
                ev = Evidence(id=trial.new_id("ev"), side=side, claim_text=cite.claim_text,
                              source_url=src.source_url, source_title=src.source_title,
                              retrieved_quote=src.retrieved_quote, retrieved_at=src.retrieved_at)
                arg.evidence_ids.append(ev.id)
                evidence.append(ev)
                by_id[ev.id] = ev
                trial.events.evidence_node(ev, stage)
                trial.events.edge(ev.id, arg.id, "supports")
            arguments.append(arg)
            last[agent] = arg
            if out.gap_query:
                gap_notes.append(out.gap_query)

            # Role-switching (PROClaim): concede ends this side; one switch per trial.
            if arg.stance == "concede":
                active[agent] = False
            elif arg.stance == "switch":
                if switch_used:
                    trial.warn(f"{stage}: {agent} tried a second switch; treated as hold")
                    arg.stance, arg.stance_reason = "hold", f"(second switch refused) {arg.stance_reason}"
                else:
                    switch_used = True
                    side_of[agent] = opponent if side_of[agent] == agent else agent
            trial.events.stance(arg, stage, side_of[agent])
            if arg.stance != "hold":
                trial.events.edge(arg.id, claim_node, "stance")

        if not any(active.values()):
            break
        if gap_research and gap_notes and round_no < rounds:
            pool = pool + gap_research(gap_notes)

    return arguments, evidence
