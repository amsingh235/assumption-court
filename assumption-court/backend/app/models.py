"""Domain schemas (BUILD.md §B.6). Mirrored in frontend/lib/types.ts — change both together."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Side = Literal["bull", "bear", "neutral"]
FactCheck = Literal["verified", "mismatched", "unverifiable"]
EvidenceStatus = Literal["VERIFIED", "UNVERIFIED"]
Stance = Literal["hold", "concede", "switch"]
VerdictLabel = Literal["SUPPORTED", "REFUTED", "INCONCLUSIVE"]
InputType = Literal["assumption", "why-question"]
EventType = Literal["node_add", "edge_add", "status", "stance", "verdict"]
JobStatus = Literal["queued", "running", "done", "error"]


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Evidence(BaseModel):
    id: str
    side: Side
    claim_text: str
    source_url: str
    source_title: str
    retrieved_quote: str
    retrieved_at: str
    factcheck: FactCheck = "unverifiable"
    status: EvidenceStatus = "UNVERIFIED"
    source_tier: Optional[int] = None
    recency: Optional[int] = None


class Argument(BaseModel):
    id: str
    agent: Literal["bull", "bear"]
    round: int
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    stance: Stance = "hold"
    stance_reason: str = ""


class Verdict(BaseModel):
    label: VerdictLabel
    bull_total: float = 0.0
    bear_total: float = 0.0
    gap: float = 0.0
    confidence: float = 0.5
    rationale: str = ""
    verdict_changers: list[str] = Field(default_factory=list)
    override: bool = False


class CauseResult(BaseModel):
    cause_text: str
    verdict: Verdict
    evidence_ids: list[str] = Field(default_factory=list)


class Report(BaseModel):
    input_text: str
    input_type: InputType
    premise_verdict: Verdict
    causes: list[CauseResult] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    arguments: list[Argument] = Field(default_factory=list)
    questions_to_ask: list[str] = Field(default_factory=list, min_length=3, max_length=3)
    # Spec keys: llm_calls, tokens, seconds. Extras: retrieval_queries, llm_provider, retrieval_provider.
    cost: dict[str, Any] = Field(default_factory=dict)


class GraphEvent(BaseModel):
    seq: int
    type: EventType
    payload: dict[str, Any]
    ts: str = Field(default_factory=utcnow)


class TrialJob(BaseModel):
    job_id: str
    status: JobStatus = "queued"
    events: list[GraphEvent] = Field(default_factory=list)
    report: Optional[Report] = None
    error: Optional[str] = None


class TrialRequest(BaseModel):
    text: str = Field(min_length=3, max_length=500)


# ---------- Structured LLM outputs (validated in llm.complete_structured) ----------

class ClassifyOut(BaseModel):
    input_type: InputType
    premise: str  # the testable assumption (for a why-question: the premise it takes for granted)


class QueriesOut(BaseModel):
    queries: list[str]


class CitationOut(BaseModel):
    pool_id: str  # id of an item in the retrieved evidence pool
    claim_text: str  # the specific claim this quote is cited for


class DebaterOut(BaseModel):
    text: str
    citations: list[CitationOut] = Field(default_factory=list)
    stance: Stance = "hold"
    stance_reason: str = ""
    gap_query: str = ""  # optional: what the Researcher should look for next round


class FactCheckOut(BaseModel):
    factcheck: FactCheck
    reason: str = ""


class ItemScoreOut(BaseModel):
    evidence_id: str
    source_tier: int = Field(ge=0, le=3)
    recency: int = Field(ge=0, le=3)


class SideScoresOut(BaseModel):
    bull: int = Field(ge=0, le=3)
    bear: int = Field(ge=0, le=3)


class JudgeOut(BaseModel):
    item_scores: list[ItemScoreOut] = Field(default_factory=list)
    corroboration: SideScoresOut
    contradiction_handling: SideScoresOut
    label: VerdictLabel
    rationale: str
    verdict_changers: list[str] = Field(default_factory=list)


class CausesOut(BaseModel):
    causes: list[str]


class QuestionsOut(BaseModel):
    questions_to_ask: list[str]


class BaselineOut(BaseModel):
    label: VerdictLabel
    rationale: str
    citations: list[CitationOut] = Field(default_factory=list)


class GradeOut(BaseModel):
    grade: Literal["supports", "partial", "does-not-support"]
    reason: str = ""
