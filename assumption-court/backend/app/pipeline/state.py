"""Mutable per-trial context shared by all pipeline nodes."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, TypedDict

from app.graph_events import EventLog
from app.models import Argument, CauseResult, Evidence, InputType, Verdict
from app.retrieval import PoolItem


class TrialTimeout(RuntimeError):
    pass


@dataclass
class Trial:
    text: str
    events: EventLog
    deadline: float  # time.monotonic() value
    input_type: InputType = "assumption"
    premise: str = ""
    pool: list[PoolItem] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    arguments: list[Argument] = field(default_factory=list)
    premise_verdict: Optional[Verdict] = None
    causes: list[CauseResult] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    retrieval_queries: int = 0
    retrieval_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    _counters: dict[str, int] = field(default_factory=dict)

    def new_id(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}-{self._counters[prefix]}"

    def check_deadline(self) -> None:
        if time.monotonic() > self.deadline:
            raise TrialTimeout("trial exceeded its time budget")

    def warn(self, message: str) -> None:
        self.warnings.append(message)


class GraphState(TypedDict):
    trial: Trial
