"""Judge: the LLM scores VERIFIED items; rubric.py does the arithmetic and the anti-neutral rule."""
from __future__ import annotations

import re

from app.config import get_settings
from app.llm import complete_structured
from app.models import Argument, Evidence, JudgeOut, QuestionsOut, Verdict
from app.pipeline.factcheck import verified_only
from app.pipeline.state import Trial
from app.rubric import apply_anti_neutral, confidence, score_line, side_total

REPROMPT_NOTE = (
    "The rubric gap between the sides is decisive (>= {gap_min}) with at least 2 verified items. "
    "INCONCLUSIVE is not allowed here: choose SUPPORTED or REFUTED based on the scores."
)


def _first_sentences(text: str, n: int) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n]).strip()


def _inconclusive(reason: str) -> Verdict:
    return Verdict(label="INCONCLUSIVE", rationale=reason, confidence=0.5,
                   verdict_changers=["Retrieve relevant, verifiable sources for this claim."])


def _judge_input(claim: str, verified: list[Evidence], arguments: list[Argument]) -> dict:
    """Rhetoric stripped: claims + quotes + stances only, never the debaters' prose."""
    return {
        "claim": claim,
        "evidence": [{"evidence_id": e.id, "side": e.side, "claim_text": e.claim_text, "quote": e.retrieved_quote,
                      "source_title": e.source_title, "source_url": e.source_url, "retrieved_at": e.retrieved_at}
                     for e in verified],
        "stances": [{"agent": a.agent, "round": a.round, "stance": a.stance, "reason": a.stance_reason}
                    for a in arguments],
    }


def judge(trial: Trial, claim: str, stage: str, evidence: list[Evidence], arguments: list[Argument],
          pool_size: int) -> Verdict:
    trial.check_deadline()
    trial.events.status("judge", "Scoring verified evidence", stage)
    if pool_size == 0:
        return _inconclusive("INCONCLUSIVE: retrieval failed, so no evidence could be retrieved for this claim.")
    verified = verified_only(evidence)
    if not verified:
        return _inconclusive("INCONCLUSIVE: no cited evidence survived fact-checking, so there is nothing to score.")

    gap_min = get_settings().judge_decisive_gap
    variables = {**_judge_input(claim, verified, arguments), "reprompt_note": ""}
    out = complete_structured("judge", variables, JudgeOut)

    def totals(o: JudgeOut) -> tuple[float, float]:
        scores = {s.evidence_id: s for s in o.item_scores}
        for ev in verified:
            s = scores.get(ev.id)
            if s is None:
                trial.warn(f"{stage}: judge gave no score for {ev.id}; scored 0/0")
            ev.source_tier, ev.recency = (s.source_tier, s.recency) if s else (0, 0)
        bull = side_total([e for e in verified if e.side == "bull"], o.corroboration.bull, o.contradiction_handling.bull)
        bear = side_total([e for e in verified if e.side == "bear"], o.corroboration.bear, o.contradiction_handling.bear)
        return bull, bear

    bull_total, bear_total = totals(out)
    decision = apply_anti_neutral(out.label, bull_total, bear_total, len(verified), gap_min, already_reprompted=False)
    if decision.needs_reprompt:
        trial.events.status("judge", "Anti-neutral rule: re-prompting the Judge once", stage)
        variables["reprompt_note"] = REPROMPT_NOTE.format(gap_min=gap_min)
        out = complete_structured("judge", variables, JudgeOut)
        bull_total, bear_total = totals(out)
        decision = apply_anti_neutral(out.label, bull_total, bear_total, len(verified), gap_min, already_reprompted=True)
    if decision.override:
        trial.warn(f"{stage}: anti-neutral override -> {decision.label} (judge said {out.label})")

    gap = round(abs(bull_total - bear_total), 2)
    lead_corr = out.corroboration.bull if bull_total >= bear_total else out.corroboration.bear
    conf = confidence(gap, lead_corr)
    rationale = f"{_first_sentences(out.rationale, 2)} {score_line(bull_total, bear_total, gap, conf)}".strip()
    return Verdict(label=decision.label, bull_total=bull_total, bear_total=bear_total, gap=gap, confidence=conf,
                   rationale=rationale, verdict_changers=out.verdict_changers[:5], override=decision.override)


def questions_to_ask(trial: Trial) -> list[str]:
    premise = trial.premise_verdict
    out = complete_structured("questions", {
        "input_text": trial.text,
        "premise_verdict": premise.model_dump() if premise else {},
        "causes": [{"cause": c.cause_text, "label": c.verdict.label} for c in trial.causes],
        "unverified_claims": [e.claim_text for e in trial.evidence if e.status == "UNVERIFIED"][:5],
    }, QuestionsOut)
    questions = [q.strip() for q in out.questions_to_ask if q.strip()]
    if len(questions) != 3:
        trial.warn(f"questions: expected exactly 3, got {len(questions)}; normalised")
    fallback = [
        "What evidence would change this verdict?",
        "Which of the UNVERIFIED claims can you check with a primary source?",
        "What is the cheapest experiment that would test this assumption directly?",
    ]
    return (questions + fallback)[:3]
