"""LangGraph pipeline (BUILD.md §B.4):

classify -> premise_trial -> [cause_trials if why-question and premise not REFUTED] -> final -> Report
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.graph_events import EventLog
from app.llm import CallStats, complete_structured, current_stats
from app.models import CausesOut, CauseResult, ClassifyOut, GraphEvent, Report
from app.pipeline.debaters import run_debate
from app.pipeline.factcheck import factcheck_all
from app.pipeline.judge import judge, questions_to_ask
from app.pipeline.researcher import research
from app.pipeline.state import GraphState, Trial

PREMISE_ROUNDS = 2
CAUSE_ROUNDS = 1
MAX_CAUSES = 3


def _retrieval_failed(trial: Trial, stage: str) -> None:
    trial.events.emit("status", {"agent": "researcher", "stage": stage, "retrieval_failed": True,
                                 "message": "Retrieval failed: no sources found. Verdict will be INCONCLUSIVE."})


def classify_node(state: GraphState) -> GraphState:
    trial = state["trial"]
    out = complete_structured("classify", {"text": trial.text}, ClassifyOut)
    trial.input_type = out.input_type
    trial.premise = out.premise.strip() or trial.text
    trial.events.node("claim", "claim", trial.premise, "premise", input_type=trial.input_type)
    trial.events.status("court", f"Classified as {trial.input_type}", "premise")
    return state


def premise_node(state: GraphState) -> GraphState:
    trial = state["trial"]
    stage = "premise"
    pool = research(trial, trial.premise, stage, "broad")
    arguments, evidence = [], []
    if pool:
        arguments, evidence = run_debate(
            trial, trial.premise, stage, pool, PREMISE_ROUNDS, "claim",
            gap_research=lambda notes: research(trial, trial.premise, stage, "gap", notes),
        )
    else:
        _retrieval_failed(trial, stage)
    trial.arguments.extend(arguments)
    trial.evidence.extend(factcheck_all(trial, evidence, stage))
    verdict = judge(trial, trial.premise, stage, evidence, arguments, pool_size=len(trial.pool))
    trial.premise_verdict = verdict
    trial.events.verdict("verdict-premise", verdict, stage, f"Premise: {verdict.label}")
    trial.events.edge("claim", "verdict-premise", "verdict")
    return state


def route_after_premise(state: GraphState) -> str:
    trial = state["trial"]
    if trial.input_type == "why-question" and trial.premise_verdict and trial.premise_verdict.label != "REFUTED":
        return "causes"
    return "final"


def causes_node(state: GraphState) -> GraphState:
    trial = state["trial"]
    out = complete_structured("causes", {"text": trial.text, "premise": trial.premise}, CausesOut)
    causes = [c.strip() for c in out.causes if c.strip()][:MAX_CAUSES]
    for i, cause in enumerate(causes, start=1):
        trial.check_deadline()
        stage = f"cause:{i}"
        node_id = f"cause-{i}"
        trial.events.node(node_id, "cause", cause, stage)
        trial.events.edge(node_id, "claim", "about")
        pool = research(trial, cause, stage, "cause", [trial.text])
        arguments, evidence = [], []
        if pool:
            arguments, evidence = run_debate(trial, cause, stage, pool, CAUSE_ROUNDS, node_id)
        else:
            _retrieval_failed(trial, stage)
        trial.arguments.extend(arguments)
        trial.evidence.extend(factcheck_all(trial, evidence, stage))
        verdict = judge(trial, cause, stage, evidence, arguments, pool_size=len(pool))
        trial.causes.append(CauseResult(cause_text=cause, verdict=verdict, evidence_ids=[e.id for e in evidence]))
        trial.events.verdict(f"verdict-{node_id}", verdict, stage, f"Cause {i}: {verdict.label}")
        trial.events.edge(node_id, f"verdict-{node_id}", "verdict")
    return state


def final_node(state: GraphState) -> GraphState:
    trial = state["trial"]
    trial.check_deadline()
    trial.events.status("judge", "Writing the final report", "final")
    trial.questions = questions_to_ask(trial)
    return state


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("classify", classify_node)
    graph.add_node("premise_trial", premise_node)
    graph.add_node("cause_trials", causes_node)
    graph.add_node("final", final_node)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "premise_trial")
    graph.add_conditional_edges("premise_trial", route_after_premise, {"causes": "cause_trials", "final": "final"})
    graph.add_edge("cause_trials", "final")
    graph.add_edge("final", END)
    return graph.compile()


_GRAPH = None


def run_trial(text: str, sink: Optional[Callable[[GraphEvent], None]] = None) -> tuple[Report, list[GraphEvent]]:
    """Run a full trial synchronously. `sink` receives each GraphEvent as it is emitted."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    settings = get_settings()
    stats = CallStats()
    token = current_stats.set(stats)
    started = time.monotonic()
    events = EventLog(sink)
    trial = Trial(text=text.strip(), events=events, deadline=started + settings.trial_timeout_s)
    try:
        _GRAPH.invoke({"trial": trial})
    finally:
        current_stats.reset(token)
    report = Report(
        input_text=trial.text,
        input_type=trial.input_type,
        premise_verdict=trial.premise_verdict,
        causes=trial.causes,
        evidence=trial.evidence,
        arguments=trial.arguments,
        questions_to_ask=trial.questions,
        cost={
            "llm_calls": stats.llm_calls,
            "tokens": stats.tokens,
            "seconds": round(time.monotonic() - started, 2),
            "retrieval_queries": trial.retrieval_queries,
            "llm_provider": settings.llm_provider,
            "retrieval_provider": settings.retrieval_provider,
            "retrieval_errors": len(trial.retrieval_errors),
            "warnings": trial.warnings,
        },
    )
    return report, events.events
