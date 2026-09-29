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
