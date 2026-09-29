"""Deterministic offline stand-in for the LLM (LLM_PROVIDER=fake).

It exists so the whole pipeline, API, frontend and eval harness can run without a Gemini key.
Its outputs are heuristics, NOT model judgments: verdicts produced in fake mode mean nothing
and every report records cost.llm_provider="fake" so the UI can flag it.

Deliberate behaviours (to exercise code paths):
- The Bull's round-1 argument includes one claim with a number not present in its quote, so the
  UNVERIFIED rule is exercised on every trial.
- A debater whose side has less evidence concedes (Bull) or switches (Bear) in the last round.
- The Judge sometimes returns INCONCLUSIVE despite a decisive gap, to exercise the anti-neutral re-prompt.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable

from app.config import get_settings
from app.rubric import is_decisive, leading_label, side_total

_PRO_MARKERS = ("consistent with the claim", "support for the claim", "repeats the claim")
_WORD = re.compile(r"[a-z0-9]+")
_NUM = re.compile(r"\d+(?:[.,]\d+)?%?")
_STOP = {"the", "a", "an", "of", "on", "in", "to", "and", "is", "are", "for", "with", "that", "this", "by", "it"}


def _h(text: str) -> int:
    return int(hashlib.md5(text.encode()).hexdigest(), 16)


def _lean(item: dict, index: int) -> str:
    quote = item.get("quote", "").lower()
    if "offline.invalid" in item.get("url", ""):
        return "pro" if any(m in quote for m in _PRO_MARKERS) else "con"
    return "pro" if index % 2 == 0 else "con"  # real sources: arbitrary but deterministic split


def lexical_check(claim: str, quote: str) -> str:
    """verified | mismatched | unverifiable, by numbers and word overlap only."""
    claim_nums, quote_nums = set(_NUM.findall(claim)), set(_NUM.findall(quote))
    if claim_nums - quote_nums:
        return "mismatched"
    words = [w for w in _WORD.findall(claim.lower()) if w not in _STOP]
    quote_words = set(_WORD.findall(quote.lower()))
    overlap = sum(w in quote_words for w in words) / max(1, len(words))
    return "verified" if overlap >= 0.6 else "unverifiable"


def _classify(v: dict) -> dict:
    text = v["text"].strip()
    if re.match(r"(?i)^why\b", text):
        premise = re.sub(r"(?i)^why\s+(do|does|did|are|is|was|were|have|has|can)?\s*", "", text).rstrip("?").strip()
        return {"input_type": "why-question", "premise": premise[:1].upper() + premise[1:]}
    return {"input_type": "assumption", "premise": text.rstrip(".")}


def _researcher(v: dict) -> dict:
    claim, n = v["claim"].rstrip(".?"), int(v["max_queries"])
    if v["mode"] == "gap" and v["notes"]:
        return {"queries": list(v["notes"])[:n]}
    if v["mode"] == "cause":
        return {"queries": [claim, f"{claim} evidence"][:n]}
    return {"queries": [claim, f"{claim} statistics", f"evidence against {claim}", f"{claim} study"][:n]}


def _debater(side: str) -> Callable[[dict], dict]:
    def run(v: dict) -> dict:
        pool, rnd, rounds, cap = v["pool"], int(v["round"]), int(v["rounds"]), int(v["max_evidence"])
        leans = [_lean(p, i) for i, p in enumerate(pool)]
        want = "pro" if side == "bull" else "con"
        mine = [p for p, lean in zip(pool, leans) if lean == want]
        theirs = len(pool) - len(mine)
        start = (rnd - 1) * cap
        picked = mine[start:start + cap] or mine[:cap]
        cites = [{"pool_id": p["pool_id"], "claim_text": p["quote"]} for p in picked]
        if side == "bull" and rnd == 1 and picked:  # fabricated statistic -> must end up UNVERIFIED
            fake = {"pool_id": picked[0]["pool_id"], "claim_text": f"{picked[0]['quote'].rstrip('.')} and grew 43% last year."}
            cites = (cites + [fake])[:cap] if len(cites) < cap else cites[:-1] + [fake]
        stance, reason = "hold", "The cited sources still favour my side."
        if rnd == rounds and rnd > 1 and len(mine) < theirs:
            stance = "concede" if side == "bull" else "switch"
            reason = f"Only {len(mine)} of {len(pool)} sources favour my side."
        label = "holds" if side == "bull" else "does not hold"
        text = f"[fake LLM] Round {rnd}: {len(picked)} retrieved source(s) suggest the claim {label}."
        gap = f"{v['claim'].rstrip('.?')} latest data" if side == "bull" and rnd == 1 else ""
        return {"text": text, "citations": cites, "stance": stance, "stance_reason": reason, "gap_query": gap}
    return run


def _factcheck(v: dict) -> dict:
    result = lexical_check(v["claim_text"], v["quote"])
    return {"factcheck": result, "reason": f"[fake LLM] lexical check: {result}"}


def _tier(url: str) -> int:
    if "/gov/" in url or re.search(r"\.(gov|edu)(/|$)|\.gov\.|\.ac\.", url):
        return 3
    if "/news/" in url or "wikipedia.org" in url:
        return 2
    return 1 if "/blog/" in url or "blog" in url else 0


def _recency(text: str) -> int:
    years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", text)]
    if not years:
        return 0
    age = datetime.now(timezone.utc).year - max(years)
    return 3 if age <= 1 else 2 if age <= 3 else 1 if age <= 5 else 0


def _judge(v: dict) -> dict:
    from app.models import Evidence

    evidence = v["evidence"]
    items = [{"evidence_id": e["evidence_id"], "source_tier": _tier(e["source_url"]),
              "recency": _recency(e["quote"] + " " + e["source_title"])} for e in evidence]
    conceded = {s["agent"] for s in v["stances"] if s["stance"] in ("concede", "switch")}
    corr, contra, totals = {}, {}, {}
    for side in ("bull", "bear"):
        side_items = [e for e in evidence if e["side"] == side]
        corr[side] = min(3, len({e["source_url"] for e in side_items}))
        contra[side] = 0 if side in conceded or not side_items else 2
        scored = [Evidence(id=i["evidence_id"], side=side, claim_text="", source_url="", source_title="",
                           retrieved_quote="", retrieved_at="", status="VERIFIED", source_tier=i["source_tier"],
                           recency=i["recency"]) for i, e in zip(items, evidence) if e["side"] == side]
        totals[side] = side_total(scored, corr[side], contra[side])
    decisive = is_decisive(totals["bull"], totals["bear"], len(evidence), get_settings().judge_decisive_gap)
    label = leading_label(totals["bull"], totals["bear"]) if decisive else "INCONCLUSIVE"
    if decisive and not v.get("reprompt_note") and _h(v["claim"]) % 4 == 0:
        label = "INCONCLUSIVE"  # exercise the anti-neutral re-prompt path
    return {
        "item_scores": items, "corroboration": corr, "contradiction_handling": contra, "label": label,
        "rationale": f"[fake LLM] Bull's verified sources scored {totals['bull']} and Bear's {totals['bear']} on the rubric.",
        "verdict_changers": ["A recent official statistic that directly measures the claim.",
                             "An independent study contradicting the leading side's sources."],
    }


def _causes(v: dict) -> dict:
    p = v["premise"].rstrip(".")
    return {"causes": [f"Rising costs explain why {p.lower()}", f"Competition explains why {p.lower()}",
                       f"Changing customer demand explains why {p.lower()}"]}


def _questions(v: dict) -> dict:
    return {"questions_to_ask": [
        "[fake LLM] Which primary data source measures this claim directly for your market?",
        "[fake LLM] What result would make you abandon this assumption?",
        "[fake LLM] Which UNVERIFIED claim matters most to your decision, and who can confirm it?",
    ]}


def _baseline(v: dict) -> dict:
    pool = v["pool"]
    leans = [_lean(p, i) for i, p in enumerate(pool)]
    pro, con = leans.count("pro"), leans.count("con")
    label = "INCONCLUSIVE" if not pool or abs(pro - con) < 2 else ("SUPPORTED" if pro > con else "REFUTED")
    return {"label": label, "rationale": f"[fake LLM] {pro} sources lean for, {con} against.",
            "citations": [{"pool_id": p["pool_id"], "claim_text": p["quote"]} for p in pool[:6]]}


def _grade(v: dict) -> dict:
    result = {"verified": "supports", "unverifiable": "partial", "mismatched": "does-not-support"}[
        lexical_check(v["claim_text"], v["quote"])]
    return {"grade": result, "reason": "[fake LLM] lexical check"}


_HANDLERS: dict[str, Callable[[dict], dict]] = {
    "classify": _classify, "researcher": _researcher, "bull": _debater("bull"), "bear": _debater("bear"),
    "factcheck": _factcheck, "judge": _judge, "causes": _causes, "questions": _questions,
    "baseline": _baseline, "grade": _grade,
}


def fake_generate(prompt_name: str, variables: dict[str, Any]) -> str:
    if prompt_name not in _HANDLERS:
        raise KeyError(f"fake LLM has no handler for prompt {prompt_name!r}")
    return json.dumps(_HANDLERS[prompt_name](variables))
