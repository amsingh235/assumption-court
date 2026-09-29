import json

from app import llm
from app.config import get_settings
from app.models import ClassifyOut


def test_every_call_is_logged():
    llm.complete_structured("classify", {"text": "Why do startups fail?"}, ClassifyOut)
    last = json.loads(get_settings().llm_log_path.read_text().splitlines()[-1])
    assert last["prompt_file"] == "prompts/classify.md"
    assert {"model", "tokens", "latency_s", "raw_response"} <= last.keys()


def test_structured_output_retries_once(monkeypatch):
    replies = iter(["not json", json.dumps({"input_type": "assumption", "premise": "x"})])
    seen = []

    def fake(name, prompt, variables, json_mode):
        seen.append(prompt)
        return next(replies), None, "stub"
    monkeypatch.setattr(llm, "_generate", fake)
    out = llm.complete_structured("classify", {"text": "x"}, ClassifyOut)
    assert out.input_type == "assumption"
    assert "previous reply was invalid" in seen[1]


def test_prompts_have_no_unfilled_placeholders():
    prompt = llm.render_prompt("judge", {"claim": "c", "evidence": [], "stances": [], "reprompt_note": ""})
    assert "$" not in prompt


class _ApiErr(Exception):
    def __init__(self, code):
        super().__init__(f"HTTP {code}")
        self.code = code


def _fake_genai(monkeypatch, codes):
    """Patch google.genai.Client so generate_content raises the given codes, then succeeds."""
    from google import genai

    calls = {"n": 0}

    class Resp:
        text = '{"input_type": "assumption", "premise": "x"}'
        usage_metadata = None

    class Models:
        def generate_content(self, **kw):
            calls["n"] += 1
            if calls["n"] <= len(codes):
                raise _ApiErr(codes[calls["n"] - 1])
            return Resp()

    class Client:
        def __init__(self, **kw):
            self.models = Models()

    monkeypatch.setattr(genai, "Client", Client)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    return calls


def test_gemini_retries_503_then_succeeds(monkeypatch, settings_env):
    settings_env(LLM_PROVIDER="gemini", GEMINI_API_KEY="k", GEMINI_MODEL="m")
    calls = _fake_genai(monkeypatch, [503, 503])
    text, _, _ = llm._gemini_generate("p", json_mode=True)
    assert "assumption" in text and calls["n"] == 3


def test_gemini_persistent_503_is_model_busy(monkeypatch, settings_env):
    import pytest

    settings_env(LLM_PROVIDER="gemini", GEMINI_API_KEY="k", GEMINI_MODEL="m")
    _fake_genai(monkeypatch, [503] * 10)
    with pytest.raises(llm.ModelBusy):
        llm._gemini_generate("p", json_mode=True)


def test_gemini_bad_key_is_not_configured(monkeypatch, settings_env):
    import pytest

    settings_env(LLM_PROVIDER="gemini", GEMINI_API_KEY="k", GEMINI_MODEL="m")
    _fake_genai(monkeypatch, [400])
    with pytest.raises(llm.LLMNotConfigured):
        llm._gemini_generate("p", json_mode=True)


class _Resp:
    def __init__(self, code, payload=None):
        self.status_code = code
        self._payload = payload or {}
        self.text = str(payload)

    def json(self):
        return self._payload


def _compat_env(settings_env, **extra):
    return settings_env(OPENAI_COMPAT_BASE_URL="https://api.example.test/v1", OPENAI_COMPAT_API_KEY="k",
                        OPENAI_COMPAT_MODEL="some-model", **extra)


def test_openai_compat_success(monkeypatch, settings_env):
    _compat_env(settings_env, LLM_PROVIDER="openai_compat")
    sent = {}

    def post(url, json, headers, timeout):
        sent.update(url=url, body=json, auth=headers["Authorization"])
        return _Resp(200, {"choices": [{"message": {"content": '{"ok": 1}'}}], "usage": {"total_tokens": 42}})

    monkeypatch.setattr(llm.httpx, "post", post)
    text, tokens, model = llm._openai_compat_generate("prompt", json_mode=True)
    assert (text, tokens, model) == ('{"ok": 1}', 42, "some-model")
    assert sent["url"] == "https://api.example.test/v1/chat/completions"
    assert sent["body"]["response_format"] == {"type": "json_object"} and sent["auth"] == "Bearer k"


def test_openai_compat_drops_json_mode_when_unsupported(monkeypatch, settings_env):
    _compat_env(settings_env, LLM_PROVIDER="openai_compat")
    bodies = []

    def post(url, json, headers, timeout):
        bodies.append(dict(json))
        if "response_format" in json:
            return _Resp(400, {"error": "response_format not supported"})
        return _Resp(200, {"choices": [{"message": {"content": "{}"}}]})

    monkeypatch.setattr(llm.httpx, "post", post)
    assert llm._openai_compat_generate("p", json_mode=True)[0] == "{}"
    assert "response_format" in bodies[0] and "response_format" not in bodies[1]


def test_busy_gemini_falls_back_to_backup(monkeypatch, settings_env):
    _compat_env(settings_env, LLM_PROVIDER="gemini", LLM_FALLBACK_PROVIDER="openai_compat",
                GEMINI_API_KEY="k", GEMINI_MODEL="m")

    def busy(prompt, json_mode):
        raise llm.ModelBusy("503")

    monkeypatch.setitem(llm._PROVIDERS, "gemini", busy)
    monkeypatch.setitem(llm._PROVIDERS, "openai_compat", lambda p, j: ('{"x": 1}', None, "backup-model"))
    assert llm._generate("classify", "p", {}, True) == ('{"x": 1}', None, "backup-model")


def test_busy_without_backup_still_raises(monkeypatch, settings_env):
    import pytest

    settings_env(LLM_PROVIDER="gemini", LLM_FALLBACK_PROVIDER="", GEMINI_API_KEY="k", GEMINI_MODEL="m")

    def busy(prompt, json_mode):
        raise llm.ModelBusy("503")

    monkeypatch.setitem(llm._PROVIDERS, "gemini", busy)
    with pytest.raises(llm.ModelBusy):
        llm._generate("classify", "p", {}, True)
