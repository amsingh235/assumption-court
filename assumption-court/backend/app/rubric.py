"""Judge rubric arithmetic (BUILD.md §B.5). The LLM scores items; code computes everything else."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models import Evidence, VerdictLabel

SIDE_MAX = 12.0


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def side_total(items: list[Evidence], corroboration: int, contradiction_handling: int) -> float:
    """mean(source_tier + recency) [0-6] + corroboration [0-3] + contradiction_handling [0-3] -> 0-12.

    Only VERIFIED items with both scores count. A side with no scorable items gets 0 for the item mean,
    and corroboration is capped by the number of its verified items.
    ASSUMPTION: the three components already sum to at most 12, so "scaled to 0-12" is a clamp, not a rescale.
    """
    scored = [e for e in items if e.status == "VERIFIED" and e.source_tier is not None and e.recency is not None]
    mean_item = sum(clamp(e.source_tier, 0, 3) + clamp(e.recency, 0, 3) for e in scored) / len(scored) if scored else 0.0
    corroboration = int(clamp(corroboration, 0, min(3, len(scored))))
    contradiction = int(clamp(contradiction_handling, 0, 3)) if scored else 0
    return round(clamp(mean_item + corroboration + contradiction, 0, SIDE_MAX), 2)


def confidence(gap: float, corroboration: int) -> float:
    """min(0.95, 0.5 + gap/24 + 0.05 * corroboration). `corroboration` is the leading side's score."""
    return round(min(0.95, 0.5 + gap / 24 + 0.05 * clamp(corroboration, 0, 3)), 3)


@dataclass(frozen=True)
class Decision:
    label: VerdictLabel
    needs_reprompt: bool
    override: bool


def is_decisive(bull_total: float, bear_total: float, verified_items: int, decisive_gap: float) -> bool:
    return abs(bull_total - bear_total) >= decisive_gap and verified_items >= 2


def leading_label(bull_total: float, bear_total: float) -> VerdictLabel:
    return "SUPPORTED" if bull_total > bear_total else "REFUTED"


def apply_anti_neutral(
    llm_label: VerdictLabel,
    bull_total: float,
    bear_total: float,
    verified_items: int,
    decisive_gap: float,
    already_reprompted: bool,
) -> Decision:
    """Anti-neutral rule.

    Decisive gap + >=2 verified items: the label MUST be the leading side's.
      - LLM says INCONCLUSIVE and we have not re-prompted yet -> ask the router to re-prompt once.
      - Still INCONCLUSIVE, or the LLM picked the trailing side -> code overrides (override=True).
    Not decisive: the LLM's label stands.
    """
    if not is_decisive(bull_total, bear_total, verified_items, decisive_gap):
        return Decision(llm_label, needs_reprompt=False, override=False)
    required = leading_label(bull_total, bear_total)
    if llm_label == required:
        return Decision(required, needs_reprompt=False, override=False)
    if llm_label == "INCONCLUSIVE" and not already_reprompted:
        return Decision(llm_label, needs_reprompt=True, override=False)
    return Decision(required, needs_reprompt=False, override=True)


def score_line(bull_total: float, bear_total: float, gap: float, conf: Optional[float] = None) -> str:
    line = f"Rubric: Bull {bull_total:g}/12 vs Bear {bear_total:g}/12 (gap {gap:g})"
    return line + (f", confidence {conf:.2f}." if conf is not None else ".")
