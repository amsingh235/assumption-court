"""Build eval/data/fever_100.jsonl: 100 FEVER claims stratified 34/33/33 (seed 42).

    python eval/fetch_fever.py

Source: the official FEVER 1.0 release (https://fever.ai/dataset/fever.html). We use the labelled
shared-task dev split. ASSUMPTION: the download URLs below are the ones listed on that page; if they
move, pass --url with the new location (or a local path) and record it in eval/report.md.
Label mapping: SUPPORTS->SUPPORTED, REFUTES->REFUTED, NOT ENOUGH INFO->INCONCLUSIVE.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import httpx

import _paths

URLS = [
    "https://fever.ai/download/fever/shared_task_dev.jsonl",
    "https://fever.ai/download/fever/paper_dev.jsonl",
]
MAPPING = {"SUPPORTS": "SUPPORTED", "REFUTES": "REFUTED", "NOT ENOUGH INFO": "INCONCLUSIVE"}
QUOTAS = {"SUPPORTS": 34, "REFUTES": 33, "NOT ENOUGH INFO": 33}


def load(source: str) -> list[dict]:
    if Path(source).exists():
        text = Path(source).read_text(encoding="utf-8")
    else:
        resp = httpx.get(source, timeout=120, follow_redirects=True)
        resp.raise_for_status()
        text = resp.text
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def stratify(rows: list[dict], seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    out = []
    for label, quota in QUOTAS.items():
        pool = [r for r in rows if r.get("label") == label]
        if len(pool) < quota:
            raise SystemExit(f"only {len(pool)} {label} rows; need {quota}")
        out += rng.sample(pool, quota)
    rng.shuffle(out)
    return [{"id": f"fever-{r['id']}", "claim": r["claim"], "label": MAPPING[r["label"]], "fever_label": r["label"]}
            for r in out]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", action="append", help="override source URL or local file (tried in order)")
    a = p.parse_args()
    errors = []
    for source in a.url or URLS:
        try:
            rows = load(source)
            break
        except Exception as exc:
            errors.append(f"{source}: {exc}")
    else:
        raise SystemExit("could not obtain FEVER:\n  " + "\n  ".join(errors))
    cases = stratify(rows)
    out = _paths.DATA_DIR / "fever_100.jsonl"
    out.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), encoding="utf-8")
    (_paths.DATA_DIR / "fever_100.source.txt").write_text(f"{source}\nseed=42 quotas={QUOTAS}\n", encoding="utf-8")
    print(f"wrote {len(cases)} claims to {out} (source: {source}). Record the source in eval/report.md.")


if __name__ == "__main__":
    main()
