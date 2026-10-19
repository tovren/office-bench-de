"""The streaming client and the runner against a fake OpenAI-compatible server (httpx.MockTransport)."""

import asyncio
import json

import httpx
import pytest

from officebench.config import ModelConfig, load_profile
from officebench.harness.client import ConfigError, complete, is_local
from officebench.harness.runner import read_log, run_task
from officebench.tasks import load_tasks


def sse(*chunks, done=True) -> bytes:
    lines = [f"data: {json.dumps(c)}\n\n" for c in chunks]
    if done:
        lines.append("data: [DONE]\n\n")
    return "".join(lines).encode()


def delta(**d) -> dict:
    return {"choices": [{"index": 0, "delta": d}]}


def finish(reason: str) -> dict:
    return {"choices": [{"index": 0, "delta": {}, "finish_reason": reason}]}


def stream_response(body: bytes) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)


def run(coro):
    return asyncio.run(coro)


async def _complete(handler, base_url="https://api.example.com/v1", **kw):
    kw.setdefault("pause", 0)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        return await complete(http, base_url, "key", {"model": "m", "messages": []}, **kw)


def test_stream_is_assembled():
    tool_args = json.dumps({"title": "Test", "sheets": []})
    body = sse(
        delta(role="assistant", reasoning_content="Ich denke "),
        delta(reasoning_content="nach."),
        delta(content="Hier "),
        delta(content="kommt die Datei."),
        delta(tool_calls=[{"index": 0, "id": "call_1", "function": {"name": "create_excel_file", "arguments": ""}}]),
        delta(tool_calls=[{"index": 0, "function": {"arguments": tool_args[:10]}}]),
        delta(tool_calls=[{"index": 0, "function": {"arguments": tool_args[10:]}}]),
        finish("tool_calls"),
        {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.0012},
         "model": "m-served"},
    )
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers["authorization"]
        return stream_response(body)

    c = run(_complete(handler))
    assert c.content == "Hier kommt die Datei."
    assert c.reasoning == "Ich denke nach."
    assert [(t.id, t.name, t.arguments) for t in c.tool_calls] == [("call_1", "create_excel_file", tool_args)]
    assert c.finish_reason == "tool_calls" and c.usage["completion_tokens"] == 5 and c.cost == 0.0012
    assert c.model == "m-served" and c.error is None and c.attempts == 1
    assert seen["body"]["stream"] is True and seen["body"]["stream_options"] == {"include_usage": True}
    assert seen["auth"] == "Bearer key"


def test_think_tags_and_gateway_metadata():
    meta = {"gateway": {"routing": {"finalProvider": "runinfra"}, "cost": "0.002"}}
    body = sse(delta(content="<think>überlegen</think>Antwort", provider_metadata=meta), finish("stop"))
    c = run(_complete(lambda r: stream_response(body)))
    assert c.content == "Antwort" and c.reasoning == "überlegen"
    assert c.provider["served_by"] == "runinfra" and c.cost == 0.002


def test_parallel_tool_calls_and_missing_index():
    body = sse(
        delta(tool_calls=[{"index": 0, "id": "a", "function": {"name": "f", "arguments": "{}"}},
                          {"index": 1, "id": "b", "function": {"name": "g", "arguments": "{}"}}]),
        delta(tool_calls=[{"id": "c", "function": {"name": "h", "arguments": "{"}}]),  # no index: a new call
        delta(tool_calls=[{"function": {"arguments": "}"}}]),  # no index, no id: continues the last
        finish("tool_calls"),
    )
    c = run(_complete(lambda r: stream_response(body)))
    assert [(t.name, t.arguments) for t in c.tool_calls] == [("f", "{}"), ("g", "{}"), ("h", "{}")]


def test_retry_on_rate_limit():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(429, json={"error": {"message": "at capacity"}})
        return stream_response(sse(delta(content="ok"), finish("stop")))

    retries = []
    c = run(_complete(handler, on_retry=retries.append))
    assert c.content == "ok" and c.attempts == 3 and len(retries) == 2


def test_provider_error_after_all_retries():
    c = run(_complete(lambda r: httpx.Response(503, text="down"), retries=2))
    assert c.error_kind == "provider" and c.attempts == 3 and "503" in c.error


def test_local_server_error_is_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(500, text="Failed to parse tool call arguments as JSON")

    c = run(_complete(handler, base_url="http://127.0.0.1:8080/v1"))
    assert c.error_kind == "server" and len(calls) == 1


def test_stream_without_end_is_a_network_error():
    body = sse(delta(content="abgebro"), done=False)
    c = run(_complete(lambda r: stream_response(body), retries=1))
    assert c.error_kind == "network" and c.attempts == 2


def test_error_object_in_stream_from_remote_api_is_provider():
    body = sse({"error": {"message": "upstream overloaded"}})
    c = run(_complete(lambda r: stream_response(body), retries=0))
    assert c.error_kind == "provider"


def test_wrong_key_stops():
    with pytest.raises(ConfigError):
        run(_complete(lambda r: httpx.Response(401, text="invalid key")))


def test_non_streaming_answer_is_accepted():
    body = {"choices": [{"index": 0, "message": {"role": "assistant", "content": "hallo"}, "finish_reason": "stop"}]}
    c = run(_complete(lambda r: httpx.Response(200, json=body)))
    assert c.content == "hallo" and c.finish_reason == "stop"


@pytest.mark.parametrize("url, local", [
    ("http://127.0.0.1:8000/v1", True), ("http://localhost:1234/v1", True), ("http://llm:8000/v1", True),
    ("http://192.168.1.5/v1", True), ("http://box.local/v1", True), ("https://ai-gateway.vercel.sh/v1", False),
    ("https://8.8.8.8/v1", False),
])
def test_is_local(url, local):
    assert is_local(url) is local


# ------------------------------------------------------------------------------------------------ runner --

MODEL = ModelConfig(name="fake", label="Fake", base_url="https://api.example.com/v1", model="fake-model")


class FakeModel:
    """Answers each request from a script: a list of responses (tool calls or text), one per request."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []

    def __call__(self, request):
        body = json.loads(request.content)
        self.requests.append(body)
        step = self.script.pop(0) if self.script else {"text": "Fertig."}
        if "calls" in step:
            chunks = [delta(tool_calls=[{"index": i, "id": f"c{len(self.requests)}{i}",
                                         "function": {"name": n, "arguments": a}}]) for i, (n, a) in
                      enumerate(step["calls"])]
            return stream_response(sse(*chunks, finish("tool_calls")))
        return stream_response(sse(delta(content=step["text"]), finish("stop")))


def _run_task(task_id, script, tmp_path, profile=None):
    fake = FakeModel(script)
    task = load_tasks()[task_id]

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as http:
            return await run_task(http, MODEL, None, profile or load_profile(), task, 0, tmp_path, progress=lambda m: 0)

    return run(go()), fake


def _reference_call(task_id):
    ref = json.loads((load_tasks()[task_id].reference_path).read_text(encoding="utf-8"))
    return ref["function"], json.dumps(ref["arguments"], ensure_ascii=False)


def test_file_task_end_to_end(tmp_path):
    name, args = _reference_call("anfrage")
    rec, fake = _run_task("anfrage", [{"calls": [("create_excel_file", "{kaputt"), ]},
                                      {"calls": [(name, args)]}, {"text": "Das Angebot ist fertig."}], tmp_path)
    assert rec["outcome"] == "answer" and rec["final_answer"] == "Das Angebot ist fertig."
    statuses = [[c["status"] for c in r["calls"]] for r in rec["rounds"]]
    assert statuses == [["parse_error"], ["ok"], []]
    built = [p.name for p in tmp_path.iterdir() if p.suffix == ".xlsx"]
    assert len(built) == 1 and built[0].startswith("anfrage-0__r1c0__")
    first = fake.requests[0]
    assert first["messages"][0] == {"role": "system", "content": load_profile().system_prompt}
    user = first["messages"][1]["content"]  # attachment text in front of the prompt
    assert user.startswith("Angehängte Dateien") and '<file name="Anfrage Schreinerei Vogt.pdf">' in user
    assert user.endswith(load_tasks()["anfrage"].turns[0].text)
    assert [t["function"]["name"] for t in first["tools"]] == ["create_excel_file", "create_powerpoint_file",
                                                               "create_word_file"]
    second = fake.requests[1]["messages"]  # the error went back to the model as a tool message
    assert second[-1]["role"] == "tool" and "could not be parsed" in second[-1]["content"]
    assert second[-2]["tool_calls"][0]["function"]["arguments"] == "{kaputt"


def test_follow_up_and_extra_tools(tmp_path):
    rec, fake = _run_task("termin", [{"calls": [("create_calendar_event", json.dumps({"title": "T"}))]},
                                     {"text": "Eingetragen."}], tmp_path)
    assert rec["rounds"][0]["calls"][0]["status"] == "extra_tool"
    assert "K-20417" in fake.requests[1]["messages"][-1]["content"]
    assert {t["function"]["name"] for t in fake.requests[0]["tools"]} >= {"create_calendar_event", "send_email"}

    name, args = _reference_call("sparquote")
    ref = json.loads(load_tasks()["sparquote"].reference_path.read_text(encoding="utf-8"))
    prev = json.dumps(ref["previous"]["arguments"], ensure_ascii=False)
    rec, fake = _run_task("sparquote", [{"calls": [(name, prev)]}, {"text": "Hier."},
                                        {"calls": [(name, args)]}, {"text": "Ergänzt."}], tmp_path)
    assert [t["end"] for t in rec["turns"]] == ["answer", "answer"]
    files = sorted(p.name for p in tmp_path.iterdir() if p.name.startswith("sparquote") and p.suffix == ".xlsx")
    assert [f.split("__")[1] for f in files] == ["r0c0", "r1c0"]  # rounds count across turns
    assert fake.requests[2]["messages"][-1]["content"] == load_tasks()["sparquote"].turns[1].text


def test_round_limit(tmp_path):
    profile = load_profile().model_copy(update={"max_rounds": 2})
    loop = [{"calls": [("create_word_file", "{}")]}] * 5
    rec, fake = _run_task("protokoll", loop, tmp_path, profile)
    assert rec["outcome"] == "round_limit" and rec["final_answer"] is None
    assert len(fake.requests) == 3 and rec["rounds"][-1]["not_executed"][0]["name"] == "create_word_file"


def test_error_ends_the_run(tmp_path, monkeypatch):

    def handler(request):
        return httpx.Response(503, text="down")

    task = load_tasks()["protokoll"]

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            from officebench.harness import runner
            orig = runner.complete

            async def few_retries(*a, **kw):
                return await orig(*a, **{**kw, "retries": 1, "pause": 0})

            monkeypatch.setattr(runner, "complete", few_retries)
            return await run_task(http, MODEL, None, load_profile(), task, 0, tmp_path, progress=lambda m: 0)

    rec = run(go())
    assert rec["outcome"] == "error" and rec["error_kind"] == "provider"


def test_read_log_keeps_last_line(tmp_path):
    log = tmp_path / "log.jsonl"
    log.write_text('{"task": "a", "rep": 0, "outcome": "error"}\n{"task": "a", "rep": 0, "outcome": "answer"}\n')
    assert read_log(log)[("a", 0)]["outcome"] == "answer"


def test_round_limit_in_first_turn_keeps_history_valid(tmp_path):
    profile = load_profile().model_copy(update={"max_rounds": 1})
    loop = [{"calls": [("create_excel_file", "{}")]}, {"calls": [("create_excel_file", "{}")]}, {"text": "Ok."}]
    rec, fake = _run_task("sparquote", loop, tmp_path, profile)
    assert [t["end"] for t in rec["turns"]] == ["round_limit", "answer"]
    history = fake.requests[2]["messages"]  # first request of turn 2
    answered = {m["tool_call_id"] for m in history if m["role"] == "tool"}
    calls = {tc["id"] for m in history if m["role"] == "assistant" for tc in m.get("tool_calls", [])}
    assert calls == answered and history[-1]["role"] == "user"
