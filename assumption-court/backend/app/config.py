"""Runtime settings, read from environment (and `.env` at the project root)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
PROMPTS_DIR = BACKEND_DIR / "prompts"
CACHED_CASES_DIR = BACKEND_DIR / "cached_cases"
LOGS_DIR = BACKEND_DIR / "logs"

# `.env` lives at the project root; backend/.env is also honoured for Docker builds.
load_dotenv(PROJECT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


def _float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    return float(raw) if raw else default


@dataclass(frozen=True)
class Settings:
    llm_provider: str  # gemini | openai_compat | ollama | fake
    llm_fallback_provider: str  # "" or another provider, used when the primary is overloaded / out of quota
    gemini_api_key: str
    gemini_model: str
    ollama_model: str
    ollama_host: str
    openai_compat_base_url: str  # e.g. Groq or OpenRouter (any OpenAI-compatible /chat/completions API)
    openai_compat_api_key: str
    openai_compat_model: str
    retrieval_provider: str  # live | fake
    judge_decisive_gap: float
    max_evidence_per_side: int
    queries_round1: int
    queries_gap: int
    results_per_query: int
    frontend_origin: str
    trial_rate_limit: int  # POST /trial per IP per hour
    trial_timeout_s: int
    llm_log_path: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "gemini").strip().lower() or "gemini",
        llm_fallback_provider=os.getenv("LLM_FALLBACK_PROVIDER", "").strip().lower(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "").strip(),
        ollama_model=os.getenv("OLLAMA_MODEL", "").strip(),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434").strip(),
        openai_compat_base_url=os.getenv("OPENAI_COMPAT_BASE_URL", "").strip().rstrip("/"),
        openai_compat_api_key=os.getenv("OPENAI_COMPAT_API_KEY", "").strip(),
        openai_compat_model=os.getenv("OPENAI_COMPAT_MODEL", "").strip(),
        retrieval_provider=os.getenv("RETRIEVAL_PROVIDER", "live").strip().lower() or "live",
        judge_decisive_gap=_float("JUDGE_DECISIVE_GAP", 3.0),
        max_evidence_per_side=_int("MAX_EVIDENCE_PER_SIDE", 3),
        queries_round1=_int("QUERIES_ROUND1", 4),
        queries_gap=_int("QUERIES_GAP", 2),
        results_per_query=_int("RESULTS_PER_QUERY", 3),
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").strip(),
        trial_rate_limit=_int("TRIAL_RATE_LIMIT", 5),
        trial_timeout_s=_int("TRIAL_TIMEOUT_S", 120),
        llm_log_path=Path(os.getenv("LLM_LOG_PATH", str(LOGS_DIR / "llm_calls.jsonl"))),
    )
