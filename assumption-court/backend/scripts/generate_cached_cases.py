"""Run the demo inputs through the Court and save them as cached examples.

    cd backend && python scripts/generate_cached_cases.py            # uses LLM_PROVIDER / RETRIEVAL_PROVIDER from .env
    cd backend && python scripts/generate_cached_cases.py --only live-1 --text "Your claim"

Writes backend/cached_cases/<id>.json and mirrors them to frontend/public/examples/ (+ index.json)
so example replay works with the backend stopped.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import CACHED_CASES_DIR, PROJECT_DIR, get_settings  # noqa: E402
from app.models import utcnow  # noqa: E402
from app.pipeline.build import run_trial  # noqa: E402

DEMO_CASES = [
    ("assumption-d2c-ads", "D2C brands fail because of ads"),
    ("why-d2c-fail", "Why do most D2C brands fail?"),
    ("false-great-wall", "The Great Wall of China is visible from the Moon with the naked eye"),
]
FRONTEND_EXAMPLES = PROJECT_DIR / "frontend" / "public" / "examples"


def save(case_id: str, text: str) -> dict:
    settings = get_settings()
    report, events = run_trial(text)
    fake = settings.llm_provider == "fake" or settings.retrieval_provider == "fake"
    case = {
        "id": case_id,
        "title": text + (" (offline placeholder)" if fake else ""),
        "generated_at": utcnow(),
        "llm_provider": settings.llm_provider,
        "retrieval_provider": settings.retrieval_provider,
        "events": [e.model_dump() for e in events],
        "report": report.model_dump(),
    }
    CACHED_CASES_DIR.mkdir(parents=True, exist_ok=True)
    (CACHED_CASES_DIR / f"{case_id}.json").write_text(json.dumps(case, indent=1, ensure_ascii=False), encoding="utf-8")
    return case


def write_frontend_mirror() -> None:
    FRONTEND_EXAMPLES.mkdir(parents=True, exist_ok=True)
    index = []
    for path in sorted(CACHED_CASES_DIR.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        (FRONTEND_EXAMPLES / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        index.append({"id": case["id"], "title": case["title"], "file": path.name})
    (FRONTEND_EXAMPLES / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="case id to (re)generate")
    parser.add_argument("--text", help="input text for --only (new case)")
    args = parser.parse_args()
    cases = [(args.only, args.text)] if args.only and args.text else \
        [c for c in DEMO_CASES if not args.only or c[0] == args.only]
    for case_id, text in cases:
        case = save(case_id, text)
        v = case["report"]["premise_verdict"]
        print(f"{case_id}: {v['label']} (bull {v['bull_total']} / bear {v['bear_total']}), {len(case['events'])} events")
    write_frontend_mirror()


if __name__ == "__main__":
    main()
