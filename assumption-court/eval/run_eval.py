"""Resumable evaluation runner: Court vs single-AI baseline.

    python eval/run_eval.py --dataset fever --limit 10      # smoke run (both arms)
    python eval/run_eval.py --all                           # full 130 (fever_100 + labelled business_30)
    python eval/run_eval.py --summary                       # accuracy table from results.jsonl

Append-only results.jsonl; (case_id, arm) pairs already present are skipped, so killing and
re-running resumes. HTTP 429 (QuotaExhausted) -> exponential backoff, then a clean exit to resume later.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import _paths
from app.llm import QuotaExhausted
from app.pipeline.build import run_trial
from baseline import run_baseline

LABELS = ("SUPPORTED", "REFUTED", "INCONCLUSIVE")
BACKOFF_S = [30, 60, 120, 240]


def load_cases(dataset: str, data_dir: Path) -> list[dict]:
    path = data_dir / f"{'fever_100' if dataset == 'fever' else 'business_30'}.jsonl"
    if not path.exists():
        sys.exit(f"{path} not found. For FEVER run: python eval/fetch_fever.py")
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    unlabelled = [c for c in cases if c.get("label") is None]
    if unlabelled:
        print(f"{dataset}: skipping {len(unlabelled)} unlabelled case(s); label them in {path.name} first")
    return [dict(c, dataset=dataset) for c in cases if c.get("label") is not None]


def load_done(results: Path) -> dict[tuple[str, str], dict]:
    done = {}
    if results.exists():
        for line in results.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if not row.get("error"):
                    done[(row["case_id"], row["arm"])] = row
    return done


def run_arm(arm: str, case: dict, court_queries: int | None) -> dict:
    start = time.monotonic()
    if arm == "court":
        report, _ = run_trial(case["claim"])
        return {"predicted": report.premise_verdict.label,
                "citations": [{"claim_text": e.claim_text, "quote": e.retrieved_quote, "url": e.source_url,
                               "status": e.status} for e in report.evidence],
                "llm_calls": report.cost["llm_calls"], "retrieval_queries": report.cost["retrieval_queries"],
                "seconds": round(time.monotonic() - start, 2)}
    out = run_baseline(case["claim"], court_queries)
    return {"predicted": out["label"], "citations": out["citations"], "llm_calls": out["llm_calls"],
            "retrieval_queries": out["retrieval_queries"], "seconds": out["seconds"]}


def with_backoff(fn):
    for delay in BACKOFF_S + [None]:
        try:
            return fn()
        except QuotaExhausted:
            if delay is None:
                raise
            print(f"  429 quota; sleeping {delay}s")
            time.sleep(delay)


def run(cases: list[dict], arms: list[str], results: Path) -> None:
    done = load_done(results)
    with results.open("a", encoding="utf-8") as fh:
        for case in cases:
            for arm in arms:
                key = (case["id"], arm)
                if key in done:
                    continue
                court_queries = done.get((case["id"], "court"), {}).get("retrieval_queries")
                row = {"case_id": case["id"], "dataset": case["dataset"], "arm": arm, "claim": case["claim"],
                       "gold": case["label"]}
                try:
                    row.update(with_backoff(lambda: run_arm(arm, case, court_queries)))
                except QuotaExhausted:
                    print("Quota still exhausted; stopping. Re-run the same command later to resume.")
                    return
                except Exception as exc:  # record and continue; errored rows are retried next run
                    row["error"] = f"{type(exc).__name__}: {exc}"
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                fh.flush()
                done[key] = row
                print(f"{case['id']} {arm}: {row.get('predicted', 'ERROR')} (gold {case['label']})")


def summary(results: Path) -> str:
    rows = list(load_done(results).values())
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["dataset"], r["arm"])].append(r)
    lines = ["| Dataset | Arm | N | Accuracy | INCONCLUSIVE rate | Avg LLM calls | Avg seconds |",
             "|---|---|---|---|---|---|---|"]
    for (dataset, arm), rs in sorted(groups.items()):
        n = len(rs)
        acc = sum(r["predicted"] == r["gold"] for r in rs) / n
        inc = Counter(r["predicted"] for r in rs)["INCONCLUSIVE"] / n
        lines.append(f"| {dataset} | {arm} | {n} | {acc:.1%} | {inc:.1%} | "
                     f"{sum(r['llm_calls'] for r in rs) / n:.1f} | {sum(r['seconds'] for r in rs) / n:.1f} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", choices=["fever", "business"], action="append")
    p.add_argument("--all", action="store_true", help="fever + business, all cases")
    p.add_argument("--limit", type=int)
    p.add_argument("--arm", choices=["court", "baseline", "both"], default="both")
    p.add_argument("--summary", action="store_true")
    p.add_argument("--data-dir", type=Path, default=_paths.DATA_DIR)
    p.add_argument("--results", type=Path, default=_paths.RESULTS_PATH)
    a = p.parse_args(argv)
    if a.summary:
        print(summary(a.results))
        return
    datasets = ["fever", "business"] if a.all else (a.dataset or ["fever"])
    cases = [c for d in datasets for c in load_cases(d, a.data_dir)]
    if a.limit:
        cases = cases[:a.limit]
    arms = ["court", "baseline"] if a.arm == "both" else [a.arm]
    run(cases, arms, a.results)
    print(summary(a.results))


if __name__ == "__main__":
    main()
