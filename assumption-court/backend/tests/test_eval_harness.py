"""P5: eval harness plumbing (fake providers; the dataset here is a throwaway fixture, not eval data)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval"))

import baseline  # noqa: E402
import grade_citations  # noqa: E402
import run_eval  # noqa: E402
from app.llm import QuotaExhausted  # noqa: E402


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    rows = [{"id": f"t-{i}", "claim": f"Test claim number {i} about markets", "label": "SUPPORTED"} for i in range(10)]
    (d / "fever_100.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return d


def rows(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def test_smoke_run_both_arms(data_dir, tmp_path):
    results = tmp_path / "results.jsonl"
    run_eval.main(["--dataset", "fever", "--limit", "10", "--data-dir", str(data_dir), "--results", str(results)])
    out = rows(results)
    assert len(out) == 20 and {r["arm"] for r in out} == {"court", "baseline"}
    for r in out:
        assert {"predicted", "gold", "citations", "llm_calls", "seconds"} <= r.keys()
    assert all(r["llm_calls"] == 1 for r in out if r["arm"] == "baseline")  # one prompt, no agents


def test_baseline_uses_court_retrieval_budget(data_dir, tmp_path):
    results = tmp_path / "results.jsonl"
    run_eval.main(["--limit", "2", "--data-dir", str(data_dir), "--results", str(results)])
    by = {(r["case_id"], r["arm"]): r for r in rows(results)}
    for case_id in ("t-0", "t-1"):
        assert by[(case_id, "baseline")]["retrieval_queries"] == by[(case_id, "court")]["retrieval_queries"]


def test_resume_after_kill(data_dir, tmp_path, monkeypatch):
    results = tmp_path / "results.jsonl"
    real, calls = run_eval.run_arm, {"n": 0}

    def dies_midway(*args):
        calls["n"] += 1
        if calls["n"] == 7:
            raise KeyboardInterrupt  # simulated kill
        return real(*args)

    monkeypatch.setattr(run_eval, "run_arm", dies_midway)
    with pytest.raises(KeyboardInterrupt):
        run_eval.main(["--data-dir", str(data_dir), "--results", str(results)])
    assert len(rows(results)) == 6
    monkeypatch.setattr(run_eval, "run_arm", real)
    run_eval.main(["--data-dir", str(data_dir), "--results", str(results)])
    keys = [(r["case_id"], r["arm"]) for r in rows(results)]
    assert len(keys) == 20 and len(set(keys)) == 20


def test_429_backoff_then_success(data_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(run_eval, "BACKOFF_S", [0, 0])
    real, fails = run_eval.run_arm, {"n": 2}

    def flaky(*args):
        if fails["n"]:
            fails["n"] -= 1
            raise QuotaExhausted("429")
        return real(*args)

    monkeypatch.setattr(run_eval, "run_arm", flaky)
    results = tmp_path / "results.jsonl"
    run_eval.main(["--limit", "1", "--arm", "court", "--data-dir", str(data_dir), "--results", str(results)])
    assert len(rows(results)) == 1 and not rows(results)[0].get("error")


def test_unlabelled_business_cases_are_skipped(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "business_30.jsonl").write_text(json.dumps({"id": "b1", "claim": "x", "label": None}) + "\n")
    assert run_eval.load_cases("business", d) == []


def test_repo_business_set_is_unlabelled():
    path = Path(run_eval._paths.DATA_DIR) / "business_30.jsonl"
    cases = rows(path)
    assert len(cases) == 30 and all(c["label"] is None for c in cases)


def test_grader_and_manual_sample(data_dir, tmp_path):
    results = tmp_path / "results.jsonl"
    run_eval.main(["--limit", "3", "--data-dir", str(data_dir), "--results", str(results)])
    grades, manual = tmp_path / "grades.jsonl", tmp_path / "manual.csv"
    args = ["--results", str(results), "--grades", str(grades), "--manual", str(manual), "--sample", "5"]
    grade_citations.main(args)
    n = len(rows(grades))
    grade_citations.main(args)  # resumable: nothing re-graded
    assert len(rows(grades)) == n > 0
    assert len(manual.read_text().splitlines()) == 6  # header + 5
    first = manual.read_text()
    grade_citations.main(args)
    assert manual.read_text() == first  # seed 42 -> stable sample


def test_baseline_queries_respect_budget():
    assert len(baseline.baseline_queries("x", 6)) == 6
