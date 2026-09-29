from fastapi.testclient import TestClient

from app import main


def client():
    main._hits.clear()
    return TestClient(main.app)


def test_health():
    assert client().get("/health").json() == {"ok": True}


def test_trial_roundtrip():
    c = client()
    job_id = c.post("/trial", json={"text": "D2C brands fail because of ads"}).json()["job_id"]
    job = c.get(f"/trial/{job_id}").json()  # TestClient runs background tasks before returning
    assert job["status"] == "done", job["error"]
    assert job["report"]["premise_verdict"]["label"] in {"SUPPORTED", "REFUTED", "INCONCLUSIVE"}
    assert job["events"]


def test_unknown_job_404():
    assert client().get("/trial/nope").status_code == 404


def test_rate_limit(settings_env):
    settings_env(TRIAL_RATE_LIMIT="2")
    c = client()
    codes = [c.post("/trial", json={"text": "Remote work lowers productivity"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_quota_error_is_friendly(monkeypatch):
    from app.llm import QuotaExhausted

    def boom(text, sink=None):
        raise QuotaExhausted("429")
    monkeypatch.setattr(main, "run_trial", boom)
    c = client()
    job_id = c.post("/trial", json={"text": "anything at all"}).json()["job_id"]
    job = c.get(f"/trial/{job_id}").json()
    assert job["status"] == "error" and "Try an example" in job["error"]


def test_examples_lists_cached_cases():
    cases = client().get("/examples").json()
    assert isinstance(cases, list)
    for case in cases:
        assert {"id", "title", "events", "report"} <= case.keys()
