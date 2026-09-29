"""End-to-end pipeline in fake mode (no network, no API key)."""
from app.pipeline import build
from app.pipeline import researcher as researcher_mod


def test_assumption_trial_report_shape():
    report, events = build.run_trial("D2C brands fail because of ads")
    assert report.input_type == "assumption"
    assert report.premise_verdict is not None
    assert len(report.questions_to_ask) == 3
    assert report.causes == []
    assert [e.seq for e in events] == list(range(1, len(events) + 1))
    assert report.cost["llm_provider"] == "fake" and report.cost["llm_calls"] > 0
    assert all(e.retrieved_quote for e in report.evidence)
    assert "Rubric: Bull" in report.premise_verdict.rationale  # rationale cites scores


def test_why_question_runs_cause_trials():
    report, events = build.run_trial("Why do most D2C brands fail?")
    assert report.input_type == "why-question"
    if report.premise_verdict.label != "REFUTED":
        assert 1 <= len(report.causes) <= 3
        assert any(e.type == "node_add" and e.payload["kind"] == "cause" for e in events)


def test_unverified_evidence_appears_in_report_and_graph():
    report, events = build.run_trial("D2C brands fail because of ads")
    unverified = [e for e in report.evidence if e.status == "UNVERIFIED"]
    assert unverified, "fake bull always cites one fabricated statistic"
    updated = {e.payload.get("evidence_id") for e in events if e.type == "status"}
    assert all(u.id in updated for u in unverified)


def test_retrieval_failure_is_inconclusive_and_signalled(monkeypatch):
    monkeypatch.setattr(researcher_mod, "retrieve", lambda queries: ([], ["ddgs: blocked"]))
    report, events = build.run_trial("Remote work lowers productivity")
    assert report.premise_verdict.label == "INCONCLUSIVE"
    assert "retrieval failed" in report.premise_verdict.rationale
    assert any(e.payload.get("retrieval_failed") for e in events)
    assert report.arguments == []  # nothing to argue about; no fabricated debate
