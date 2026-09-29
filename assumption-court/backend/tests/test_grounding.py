"""P2: grounding. The fake-stat test is the critical acceptance check."""
import os

import pytest

from app.models import Argument, Evidence
from app.pipeline import judge as judge_mod
from app.pipeline.factcheck import enforce_unverified, factcheck_all, verified_only
from app.retrieval import search_ddg, search_wikipedia, verbatim_quote

QUOTE = "India is the world's largest milk producer, accounting for about 24% of global production."


def make_ev(ev_id, claim, side="bull", quote=QUOTE):
    return Evidence(id=ev_id, side=side, claim_text=claim, source_url=f"https://example.org/{ev_id}",
                    source_title="Fixture source", retrieved_quote=quote, retrieved_at="2026-01-01T00:00:00+00:00")


def fixture_evidence():
    return [
        make_ev("ev-real", "India is the world's largest milk producer"),
        make_ev("ev-fake", "India produces 61% of the world's milk"),  # fabricated statistic
        make_ev("ev-bear", "India accounts for about 24% of global production", side="bear"),
    ]


def test_fake_stat_is_unverified_and_excluded_from_judge(trial, monkeypatch):
    evidence = factcheck_all(trial, fixture_evidence(), "premise")
    by_id = {e.id: e for e in evidence}
    assert by_id["ev-fake"].factcheck == "mismatched"
    assert by_id["ev-fake"].status == "UNVERIFIED"
    assert by_id["ev-real"].status == "VERIFIED"

    seen = {}
    real = judge_mod.complete_structured

    def spy(prompt_file, variables, schema):
        seen.setdefault(prompt_file, []).append(variables)
        return real(prompt_file, variables, schema)

    monkeypatch.setattr(judge_mod, "complete_structured", spy)
    args = [Argument(id="arg-1", agent="bull", round=1, text="x", evidence_ids=["ev-real", "ev-fake"])]
    verdict = judge_mod.judge(trial, "India is the world's largest milk producer", "premise", evidence, args, pool_size=3)

    judged_ids = {e["evidence_id"] for e in seen["judge"][0]["evidence"]}
    assert "ev-fake" not in judged_ids
    assert judged_ids == {"ev-real", "ev-bear"}
    assert by_id["ev-fake"].source_tier is None  # never scored
    assert verdict.label in {"SUPPORTED", "REFUTED", "INCONCLUSIVE"}
    # still present for the report and the graph
    assert any(e.payload.get("evidence_id") == "ev-fake" and e.payload["status"] == "UNVERIFIED"
               for e in trial.events.events)


def test_stale_verified_status_cannot_leak_into_judge_input():
    ev = make_ev("ev-x", "claim")
    ev.factcheck, ev.status = "unverifiable", "VERIFIED"  # inconsistent state
    assert verified_only([ev]) == []
    assert ev.status == "UNVERIFIED"


@pytest.mark.parametrize("check", ["mismatched", "unverifiable"])
def test_non_verified_factcheck_is_unverified(check):
    ev = make_ev("ev-y", "claim")
    ev.factcheck = check
    assert enforce_unverified(ev).status == "UNVERIFIED"


def test_verbatim_quote_is_substring_and_at_most_three_sentences():
    text = "First one. Second one! Third one? Fourth one. Fifth."
    quote = verbatim_quote(text)
    assert quote == "First one. Second one! Third one?"
    assert quote in text


def test_verbatim_quote_long_sentence_is_cut_not_rewritten():
    text = "word " * 200
    quote = verbatim_quote(text, max_chars=50)
    assert len(quote) <= 50 and quote in " ".join(text.split())


def test_retrieval_failure_gives_inconclusive(trial):
    verdict = judge_mod.judge(trial, "anything", "premise", [], [], pool_size=0)
    assert verdict.label == "INCONCLUSIVE"
    assert "retrieval failed" in verdict.rationale


@pytest.mark.network
def test_live_retrieval_milk():
    claim = "India is the world's largest milk producer"
    items = []
    for fn in (lambda: search_ddg(claim, 5), lambda: search_wikipedia(claim, 2)):
        try:
            items.extend(fn())
        except Exception as exc:  # one source may be down; the other must deliver
            print(f"source failed: {exc}")
    assert len(items) >= 3
    assert all(i.retrieved_quote and i.source_url.startswith("http") for i in items)


@pytest.mark.llm
def test_fake_stat_with_real_llm(trial, settings_env):
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    settings_env(LLM_PROVIDER=os.getenv("REAL_LLM_PROVIDER", "gemini"))
    evidence = factcheck_all(trial, [make_ev("ev-fake", "India produces 61% of the world's milk")], "premise")
    assert evidence[0].status == "UNVERIFIED"
