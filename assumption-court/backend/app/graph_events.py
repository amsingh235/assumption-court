"""Graph event stream. The frontend polls TrialJob.events and renders them in `seq` order.

Payload conventions (mirrored in frontend/lib/types.ts):
  node_add : {id, kind: claim|argument|evidence|cause|verdict, label, stage, side?, round?, agent?,
              status?, factcheck?, quote?, url?, title?}
  edge_add : {id, source, target, kind: supports|rebuts|stance|about|verdict}
  status   : {agent, message, stage}  or evidence update {evidence_id, factcheck, status, stage}
  stance   : {agent, stance, reason, round, argument_id, stage, side_now}
  verdict  : {stage, node_id, verdict: Verdict}
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Optional

from app.models import Argument, Evidence, GraphEvent, Verdict


class EventLog:
    def __init__(self, sink: Optional[Callable[[GraphEvent], None]] = None) -> None:
        self.events: list[GraphEvent] = []
        self._sink = sink
        self._lock = threading.Lock()
        self._edge_n = 0

    def emit(self, type_: str, payload: dict[str, Any]) -> GraphEvent:
        with self._lock:
            event = GraphEvent(seq=len(self.events) + 1, type=type_, payload=payload)
            self.events.append(event)
        if self._sink:
            self._sink(event)
        return event

    # ---- helpers
    def status(self, agent: str, message: str, stage: str) -> None:
        self.emit("status", {"agent": agent, "message": message, "stage": stage})

    def node(self, node_id: str, kind: str, label: str, stage: str, **extra: Any) -> None:
        self.emit("node_add", {"id": node_id, "kind": kind, "label": label, "stage": stage, **extra})

    def edge(self, source: str, target: str, kind: str) -> None:
        with self._lock:
            self._edge_n += 1
            edge_id = f"e{self._edge_n}"
        self.emit("edge_add", {"id": edge_id, "source": source, "target": target, "kind": kind})

    def evidence_node(self, ev: Evidence, stage: str) -> None:
        self.node(ev.id, "evidence", ev.claim_text, stage, side=ev.side, status=ev.status, factcheck=ev.factcheck,
                  quote=ev.retrieved_quote, url=ev.source_url, title=ev.source_title)

    def argument_node(self, arg: Argument, stage: str, side: str) -> None:
        self.node(arg.id, "argument", arg.text, stage, side=side, agent=arg.agent, round=arg.round)

    def evidence_update(self, ev: Evidence, stage: str) -> None:
        self.emit("status", {"evidence_id": ev.id, "factcheck": ev.factcheck, "status": ev.status, "stage": stage})

    def stance(self, arg: Argument, stage: str, side_now: str) -> None:
        self.emit("stance", {"agent": arg.agent, "stance": arg.stance, "reason": arg.stance_reason,
                             "round": arg.round, "argument_id": arg.id, "stage": stage, "side_now": side_now})

    def verdict(self, node_id: str, verdict: Verdict, stage: str, label: str) -> None:
        self.node(node_id, "verdict", label, stage)
        self.emit("verdict", {"stage": stage, "node_id": node_id, "verdict": verdict.model_dump()})
