import pytest

from app.models import Evidence
from app.rubric import apply_anti_neutral, confidence, is_decisive, side_total


def ev(tier, rec, status="VERIFIED", side="bull"):
    return Evidence(id="e", side=side, claim_text="c", source_url="u", source_title="t", retrieved_quote="q",
                    retrieved_at="now", factcheck="verified" if status == "VERIFIED" else "mismatched",
                    status=status, source_tier=tier, recency=rec)


def test_side_total_mean_plus_components():
    # mean((3+3), (1+1)) = 4, + corroboration 2 + contradiction 3 = 9
    assert side_total([ev(3, 3), ev(1, 1)], corroboration=2, contradiction_handling=3) == 9.0


def test_side_total_caps_at_12_and_clamps_inputs():
    assert side_total([ev(3, 3)] * 3, corroboration=9, contradiction_handling=9) == 12.0


def test_side_total_ignores_unverified_items():
    assert side_total([ev(3, 3, status="UNVERIFIED")], 3, 3) == 0.0


def test_corroboration_capped_by_verified_item_count():
    # one verified item cannot claim 3 independent agreeing sources
    assert side_total([ev(2, 2)], corroboration=3, contradiction_handling=0) == 5.0


def test_confidence_formula():
    assert confidence(0, 0) == 0.5
    assert confidence(6, 2) == pytest.approx(0.5 + 6 / 24 + 0.1)
    assert confidence(12, 3) == 0.95  # capped


def test_decisive_needs_gap_and_two_verified_items():
    assert is_decisive(8, 5, 2, 3)
    assert not is_decisive(8, 5.5, 2, 3)
    assert not is_decisive(9, 1, 1, 3)


def test_inconclusive_on_decisive_gap_triggers_one_reprompt_then_override():
    first = apply_anti_neutral("INCONCLUSIVE", 9, 4, 3, 3, already_reprompted=False)
    assert first.needs_reprompt and not first.override
    second = apply_anti_neutral("INCONCLUSIVE", 9, 4, 3, 3, already_reprompted=True)
    assert second.label == "SUPPORTED" and second.override and not second.needs_reprompt


def test_bear_lead_forces_refuted():
    assert apply_anti_neutral("INCONCLUSIVE", 2, 8, 3, 3, already_reprompted=True).label == "REFUTED"


def test_trailing_side_label_is_overridden():
    d = apply_anti_neutral("SUPPORTED", 2, 8, 3, 3, already_reprompted=False)
    assert d.label == "REFUTED" and d.override


def test_non_decisive_keeps_llm_label():
    d = apply_anti_neutral("INCONCLUSIVE", 6, 5, 4, 3, already_reprompted=False)
    assert d.label == "INCONCLUSIVE" and not d.override and not d.needs_reprompt
