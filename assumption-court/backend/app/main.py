"""FastAPI app (BUILD.md §B.7)."""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import OrderedDict, deque

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import CACHED_CASES_DIR, get_settings
from app.llm import QuotaExhausted
from app.models import GraphEvent, TrialJob, TrialRequest
from app.pipeline.build import run_trial
from app.pipeline.state import TrialTimeout

log = logging.getLogger("assumption_court")
MAX_JOBS = 200

app = FastAPI(title="Assumption Court", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().frontend_origin.split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_jobs: "OrderedDict[str, TrialJob]" = OrderedDict()
_jobs_lock = threading.Lock()
_hits: dict[str, deque] = {}
_hits_lock = threading.Lock()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(ip: str) -> None:
    limit, window = get_settings().trial_rate_limit, 3600.0
    now = time.time()
    with _hits_lock:
        hits = _hits.setdefault(ip, deque())
        while hits and now - hits[0] > window:
            hits.popleft()
        if len(hits) >= limit:
            retry = int(window - (now - hits[0])) + 1
            raise HTTPException(429, detail=f"Rate limit: {limit} trials per hour. Try an example meanwhile.",
                                headers={"Retry-After": str(retry)})
        hits.append(now)


def _store(job: TrialJob) -> None:
    with _jobs_lock:
        _jobs[job.job_id] = job
        while len(_jobs) > MAX_JOBS:
            _jobs.popitem(last=False)


def run_job(job_id: str, text: str) -> None:
    job = _jobs[job_id]
    job.status = "running"

    def sink(event: GraphEvent) -> None:
        job.events.append(event)

    try:
        report, _ = run_trial(text, sink=sink)
        job.report = report
        job.status = "done"
    except QuotaExhausted:
        job.error = "The free LLM quota is exhausted right now. Try an example instead."
        job.status = "error"
    except TrialTimeout:
        job.error = f"The trial took longer than {get_settings().trial_timeout_s}s and was stopped. Try an example."
        job.status = "error"
    except Exception as exc:  # surfaced to the UI; full trace in server logs
        log.exception("trial %s failed", job_id)
        job.error = f"Trial failed ({type(exc).__name__}). Try again or load an example."
        job.status = "error"


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/trial")
def create_trial(body: TrialRequest, request: Request, background: BackgroundTasks) -> dict:
    check_rate_limit(client_ip(request))
    job = TrialJob(job_id=uuid.uuid4().hex[:12])
    _store(job)
    background.add_task(run_job, job.job_id, body.text)
    return {"job_id": job.job_id}


@app.get("/trial/{job_id}")
def get_trial(job_id: str) -> TrialJob:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, detail="Unknown job id")
    return job


@app.get("/examples")
def examples() -> list[dict]:
    cases = []
    for path in sorted(CACHED_CASES_DIR.glob("*.json")):
        try:
            cases.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            log.warning("skipping unreadable cached case %s", path.name)
    return cases
