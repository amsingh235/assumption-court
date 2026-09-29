"""Grade every (claim, quote) citation in results.jsonl with a separate LLM grader prompt (prompts/grade.md).

    python eval/grade_citations.py

Resumable (citation_grades.jsonl). Prints the supports/partial/does-not-support rate per arm and writes a
random 20-pair sample (seed 42) to manual_check.csv for the human spot check.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import _paths
from app.llm import complete_structured
from app.models import GradeOut

GRADES_PATH = _paths.EVAL_DIR / "citation_grades.jsonl"
MANUAL_PATH = _paths.EVAL_DIR / "manual_check.csv"


def pair_key(row: dict, cite: dict) -> str:
    raw = f"{row['case_id']}|{row['arm']}|{cite['claim_text']}|{cite['quote']}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, default=_paths.RESULTS_PATH)
    p.add_argument("--grades", type=Path, default=GRADES_PATH)
    p.add_argument("--manual", type=Path, default=MANUAL_PATH)
    p.add_argument("--sample", type=int, default=20)
    a = p.parse_args(argv)

    graded = {}
    if a.grades.exists():
        for line in a.grades.read_text(encoding="utf-8").splitlines():
            if line.strip():
                g = json.loads(line)
                graded[g["key"]] = g
    rows = [json.loads(l) for l in a.results.read_text(encoding="utf-8").splitlines() if l.strip()]
    with a.grades.open("a", encoding="utf-8") as fh:
        for row in rows:
            for cite in row.get("citations", []):
                key = pair_key(row, cite)
                if key in graded:
                    continue
                out = complete_structured("grade", {"claim_text": cite["claim_text"], "quote": cite["quote"]}, GradeOut)
                g = {"key": key, "case_id": row["case_id"], "arm": row["arm"], "claim_text": cite["claim_text"],
                     "quote": cite["quote"], "url": cite.get("url", ""), "status": cite.get("status", ""),
                     "grade": out.grade, "reason": out.reason}
                fh.write(json.dumps(g, ensure_ascii=False) + "\n")
                graded[key] = g

    per_arm: dict[str, Counter] = defaultdict(Counter)
    for g in graded.values():
        per_arm[g["arm"]][g["grade"]] += 1
    for arm, counts in sorted(per_arm.items()):
        total = sum(counts.values())
        print(f"{arm}: {total} citations | " + " | ".join(f"{k} {v / total:.1%}" for k, v in sorted(counts.items())))

    sample = random.Random(42).sample(sorted(graded.values(), key=lambda g: g["key"]), min(a.sample, len(graded)))
    with a.manual.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["key", "arm", "case_id", "claim_text", "quote", "url", "grade",
                                                "human_grade", "notes"])
        writer.writeheader()
        for g in sample:
            writer.writerow({k: g.get(k, "") for k in writer.fieldnames})
    print(f"wrote {len(sample)} pairs to {a.manual} for manual checking")


if __name__ == "__main__":
    main()
