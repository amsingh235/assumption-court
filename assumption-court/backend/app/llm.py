"""Provider-agnostic LLM interface. Every call is logged to backend/logs/llm_calls.jsonl.

Providers (env LLM_PROVIDER): gemini (default), ollama, fake (deterministic, offline; see fake_llm.py).
"""
from __future__ import annotations

import contextvars
import json
import re
import threading
import time
from dataclasses import dataclass, field
from string import Template
from typing import Any, Optional, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import PROMPTS_DIR, get_settings

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class LLMNotConfigured(LLMError):
    """Missing key/model for the selected provider. Safe to show to the user."""


class ModelBusy(LLMError):
    """Provider returned 5xx (overloaded / unavailable) after retries. Temporary; safe to show to the user."""


class QuotaExhausted(LLMError):
    """Provider returned HTTP 429 after retries. The API surfaces this as 'try an example'."""


@dataclass
class CallStats:
    llm_calls: int = 0
    tokens: Optional[int] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def add(self, tokens: Optional[int]) -> None:
        self.llm_calls += 1
        if tokens is not None:
            self.tokens = (self.tokens or 0) + tokens


# Per-trial counters; set by the pipeline runner inside its worker thread.
current_stats: contextvars.ContextVar[Optional[CallStats]] = contextvars.ContextVar("current_stats", default=None)
_log_lock = threading.Lock()


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def render_prompt(name: str, variables: dict[str, Any]) -> str:
    variables = {"_retry_note": "", **variables}
    flat = {k: v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=1) for k, v in variables.items()}
    return Template(load_prompt(name)).safe_substitute(flat)


# ---------------------------------------------------------------- providers

def _gemini_generate(prompt: str, json_mode: bool) -> tuple[str, Optional[int], str]:
    from google import genai
    from google.genai import types

    s = get_settings()
    if not s.gemini_api_key or not s.gemini_model:
        raise LLMNotConfigured("GEMINI_API_KEY and GEMINI_MODEL must be set (or use LLM_PROVIDER=fake)")
    client = genai.Client(api_key=s.gemini_api_key)
    config = types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json" if json_mode else "text/plain",
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),  # no tools used
    )
    delay = 4.0
    attempts = 2 if s.llm_fallback_provider else 4  # with a backup provider, hand over quickly
    for attempt in range(attempts):
        try:
            resp = client.models.generate_content(model=s.gemini_model, contents=prompt, config=config)
            usage = getattr(resp, "usage_metadata", None)
            tokens = getattr(usage, "total_token_count", None) if usage else None
            return resp.text or "", tokens, s.gemini_model
        except Exception as exc:  # google.genai.errors.APIError carries .code
            code = getattr(exc, "code", None)
            retryable = code == 429 or (isinstance(code, int) and code >= 500)
            if retryable and attempt < attempts - 1:
                time.sleep(delay)  # 4s, 8s, 16s
                delay *= 2
                continue
            if code == 429:
                raise QuotaExhausted(str(exc)) from exc
            if retryable:
                raise ModelBusy(str(exc)) from exc
            if code in (400, 401, 403, 404):
                raise LLMNotConfigured(f"Gemini rejected the request ({code}); check GEMINI_API_KEY and GEMINI_MODEL") from exc
            raise LLMError(f"gemini call failed: {exc}") from exc
    raise LLMError("unreachable")


def _openai_compat_generate(prompt: str, json_mode: bool) -> tuple[str, Optional[int], str]:
    """Any OpenAI-compatible /chat/completions API (Groq, OpenRouter, Together, Mistral, LM Studio, ...)."""
    s = get_settings()
    if not (s.openai_compat_base_url and s.openai_compat_api_key and s.openai_compat_model):
        raise LLMNotConfigured("OPENAI_COMPAT_BASE_URL, OPENAI_COMPAT_API_KEY and OPENAI_COMPAT_MODEL must be set")
    body: dict[str, Any] = {
        "model": s.openai_compat_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {s.openai_compat_api_key}"}
    url = f"{s.openai_compat_base_url}/chat/completions"
    delay = 4.0
    for attempt in range(3):
        resp = httpx.post(url, json=body, headers=headers, timeout=120)
        code = resp.status_code
        if code == 400 and "response_format" in body:
            body.pop("response_format")  # some models don't support JSON mode; the prompt still asks for JSON
            continue
        if code == 200:
            data = resp.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            tokens = (data.get("usage") or {}).get("total_tokens")
            return text, tokens, s.openai_compat_model
        if (code == 429 or code >= 500) and attempt < 2:
            time.sleep(delay)
            delay *= 2
            continue
        detail = resp.text[:300]
        if code == 429:
            raise QuotaExhausted(detail)
        if code >= 500:
            raise ModelBusy(detail)
        if code in (400, 401, 403, 404):
            raise LLMNotConfigured(f"the OpenAI-compatible API rejected the request ({code}): {detail}")
        raise LLMError(f"openai_compat call failed ({code}): {detail}")
    raise LLMError("openai_compat call failed after retries")


def _ollama_generate(prompt: str, json_mode: bool) -> tuple[str, Optional[int], str]:
    s = get_settings()
    if not s.ollama_model:
        raise LLMNotConfigured("OLLAMA_MODEL must be set when LLM_PROVIDER=ollama")
    body: dict[str, Any] = {"model": s.ollama_model, "prompt": prompt, "stream": False}
    if json_mode:
        body["format"] = "json"
    resp = httpx.post(f"{s.ollama_host}/api/generate", json=body, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    tokens = (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0) or None
    return data.get("response", ""), tokens, s.ollama_model


_PROVIDERS = {
    "gemini": _gemini_generate,
    "openai_compat": _openai_compat_generate,
    "ollama": _ollama_generate,
}


def _generate(prompt_name: str, prompt: str, variables: dict[str, Any], json_mode: bool) -> tuple[str, Optional[int], str]:
    s = get_settings()
    if s.llm_provider == "fake":
        from app.fake_llm import fake_generate

        return fake_generate(prompt_name, variables), None, "fake"
    if s.llm_provider not in _PROVIDERS:
        raise LLMError(f"unknown LLM_PROVIDER {s.llm_provider!r}")
    try:
        return _PROVIDERS[s.llm_provider](prompt, json_mode)
    except (ModelBusy, QuotaExhausted):
        backup = _PROVIDERS.get(s.llm_fallback_provider)
        if backup is None or s.llm_fallback_provider == s.llm_provider:
            raise
        return backup(prompt, json_mode)  # the log records which model actually answered


# ---------------------------------------------------------------- public API

def _log(record: dict[str, Any]) -> None:
    path = get_settings().llm_log_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with _log_lock, path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def complete(prompt_file: str, variables: dict[str, Any], json_mode: bool = False) -> str:
    prompt = render_prompt(prompt_file, variables)
    start = time.perf_counter()
    error: Optional[str] = None
    text, tokens, model = "", None, get_settings().llm_provider
    try:
        text, tokens, model = _generate(prompt_file, prompt, variables, json_mode)
        return text
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        stats = current_stats.get()
        if stats is not None:
            stats.add(tokens)
        _log({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "provider": get_settings().llm_provider,
            "model": model,
            "prompt_file": f"prompts/{prompt_file}.md",
            "tokens": tokens,
            "latency_s": round(time.perf_counter() - start, 3),
            "raw_response": text,
            "error": error,
        })


def _parse_json(text: str) -> Any:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    return json.loads(cleaned)


def complete_structured(prompt_file: str, variables: dict[str, Any], schema: type[T]) -> T:
    """Call the LLM expecting JSON matching `schema`; retry once with the validation error."""
    text = complete(prompt_file, variables, json_mode=True)
    try:
        return schema.model_validate(_parse_json(text))
    except (ValueError, ValidationError) as first_error:
        retry_vars = dict(variables)
        retry_vars["_retry_note"] = (
            f"Your previous reply was invalid ({str(first_error)[:300]}). Reply with valid JSON only."
        )
        text = complete(prompt_file, retry_vars, json_mode=True)
        try:
            return schema.model_validate(_parse_json(text))
        except (ValueError, ValidationError) as exc:
            raise LLMError(f"{prompt_file}: invalid structured output after retry: {exc}") from exc
