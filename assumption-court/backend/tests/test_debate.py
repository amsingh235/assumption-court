"""P3: anti-gish cap, citation hygiene, role-switching."""
from app.models import CitationOut, DebaterOut
from app.pipeline import debaters
from app.retrieval import PoolItem


def pool(n):
    return [PoolItem(id=f"pool-{i}", query="q", source_url=f"https://s/{i}", source_title=f"S{i}",
                     retrieved_quote=f"Quote {i}.", retrieved_at="t") for i in range(1, n + 1)]


def scripted(outputs):
    """Stub complete_structured returning queued DebaterOut values in call order."""
    queue = list(outputs)

    def fake(prompt_file, variables, schema):
        return queue.pop(0)
    return fake


def cite(*ids):
    return [CitationOut(pool_id=f"pool-{i}", claim_text=f"Quote {i}.") for i in ids]


def test_evidence_capped_at_three_per_side_per_round(trial, monkeypatch):
    monkeypatch.setattr(debaters, "complete_structured", scripted([
        DebaterOut(text="bull", citations=cite(1, 2, 3, 4, 5)),
        DebaterOut(text="bear", citations=cite(6)),
    ]))
    args, evidence = debaters.run_debate(trial, "claim", "premise", pool(6), 1, "claim")
    assert len(args[0].evidence_ids) == 3
    assert [e.side for e in evidence].count("bull") == 3
    assert any("truncated" in w for w in trial.warnings)


def test_unknown_pool_ids_are_dropped(trial, monkeypatch):
    bogus = [CitationOut(pool_id="pool-99", claim_text="made up")]
    monkeypatch.setattr(debaters, "complete_structured", scripted([
        DebaterOut(text="bull", citations=cite(1) + bogus),
        DebaterOut(text="bear", citations=[]),
    ]))
    _, evidence = debaters.run_debate(trial, "claim", "premise", pool(2), 1, "claim")
    assert [e.retrieved_quote for e in evidence] == ["Quote 1."]


def test_evidence_quote_is_copied_verbatim_from_pool(trial, monkeypatch):
    monkeypatch.setattr(debaters, "complete_structured", scripted([
        DebaterOut(text="bull", citations=[CitationOut(pool_id="pool-2", claim_text="paraphrase")]),
        DebaterOut(text="bear"),
    ]))
    _, evidence = debaters.run_debate(trial, "claim", "premise", pool(2), 1, "claim")
    assert evidence[0].retrieved_quote == "Quote 2." and evidence[0].claim_text == "paraphrase"


def test_concede_ends_that_side(trial, monkeypatch):
    monkeypatch.setattr(debaters, "complete_structured", scripted([
        DebaterOut(text="bull r1", citations=cite(1), stance="concede", stance_reason="evidence is against me"),
        DebaterOut(text="bear r1", citations=cite(2)),
        DebaterOut(text="bear r2", citations=cite(3)),
    ]))
    args, _ = debaters.run_debate(trial, "claim", "premise", pool(3), 2, "claim")
    assert [(a.agent, a.round) for a in args] == [("bull", 1), ("bear", 1), ("bear", 2)]
    stance_events = [e for e in trial.events.events if e.type == "stance" and e.payload["stance"] == "concede"]
    assert stance_events and stance_events[0].payload["reason"] == "evidence is against me"


def test_switch_moves_agent_to_other_side_and_only_once(trial, monkeypatch):
    monkeypatch.setattr(debaters, "complete_structured", scripted([
        DebaterOut(text="b1", citations=cite(1), stance="switch", stance_reason="convinced"),
        DebaterOut(text="r1", citations=cite(2), stance="switch", stance_reason="me too"),
        DebaterOut(text="b2", citations=cite(3)),
        DebaterOut(text="r2", citations=cite(4)),
    ]))
    args, evidence = debaters.run_debate(trial, "claim", "premise", pool(4), 2, "claim")
    assert args[1].stance == "hold"  # second switch refused
    by_arg = {a.text: a for a in args}
    b2_evidence = [e for e in evidence if e.id in by_arg["b2"].evidence_ids]
    assert b2_evidence[0].side == "bear"  # the bull agent now argues the bear side
    assert any(e.type == "edge_add" and e.payload["kind"] == "stance" for e in trial.events.events)
