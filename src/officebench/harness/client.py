"""Streaming client for OpenAI-compatible chat completions with tool calls.

One request = one round. The stream is assembled the way chat front ends do it: text and reasoning deltas are
concatenated, tool-call deltas are merged by their index, reasoning arrives as `reasoning_content`, `reasoning` or
inside <think>…</think> in the text. Usage and the cost (usage.cost, or provider_metadata.gateway.cost of the Vercel AI
Gateway) are read from any chunk that carries them.

Failures are classified, because they are scored differently (docs/harness.md):
- provider: overload or outage (429, 502, 503, 504, 529, overload errors, HTTP 500 from a remote API); retried
- network: connection errors, timeouts, a stream that ends without a finish reason; retried
- server: an error from a local/private model server (HTTP 500, 400, 422 …) — the user would see the chat break, so
  it counts as a failure of the model setup; not retried
- config: 401, 403, 404 (wrong key, URL or model name); the run stops
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

RETRY_STATUS = {429, 502, 503, 504, 529}
CONFIG_STATUS = {401, 403, 404}
OVERLOAD = re.compile(r"overload|rate.?limit|capacity|too many requests|unavailable", re.I)
THINK = re.compile(r"<think>(.*?)(</think>|$)", re.S)


class ConfigError(RuntimeError):
    """Wrong key, URL or model name: retrying is pointless, the run stops."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass
class Completion:
    content: str = ""
    reasoning: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    usage: dict = field(default_factory=dict)
    cost: float | None = None
    model: str | None = None
    provider: dict = field(default_factory=dict)  # provider-specific fields (routing, metadata) for the log
    ttft: float | None = None  # seconds until the first delta with text, reasoning or a tool call
    seconds: float = 0.0  # duration of the successful attempt
    wait_seconds: float = 0.0  # backoff before retries
    attempts: int = 1
    error: str | None = None
    error_kind: str | None = None  # provider | network | server (None = success)


def is_local(base_url: str) -> bool:
    """localhost, private or link-local addresses, *.local and host names without a dot (e.g. 'llm')."""
    host = (urlparse(base_url).hostname or "").lower()
    if host in ("localhost",) or host.endswith(".local") or "." not in host:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def _find_cost(obj: Any, parent: str = "") -> float | None:
    found = None
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "cost" and parent in ("gateway", "usage") and isinstance(v, (int, float, str)):
                try:
                    found = float(v)
                except ValueError:
                    pass
            elif isinstance(v, (dict, list)) and k not in ("content", "tool_calls", "reasoning_details"):
                c = _find_cost(v, k)
                found = c if c is not None else found
    elif isinstance(obj, list):
        for v in obj:
            c = _find_cost(v, parent)
            found = c if c is not None else found
    return found


def _provider_fields(obj: dict) -> dict:
    """Keys of a chunk or delta that say which provider served the request (kept short for the log); the Vercel AI
    Gateway sends choices[0].delta.provider_metadata.gateway.routing.finalProvider."""
    out = {}
    for k, v in obj.items():
        if "provider" in k.lower() or k in ("system_fingerprint",):
            gateway = v.get("gateway") if isinstance(v, dict) else None
            routing = gateway.get("routing") if isinstance(gateway, dict) else None
            if isinstance(routing, dict) and routing.get("finalProvider"):
                out["served_by"] = routing["finalProvider"]
            text = json.dumps(v, ensure_ascii=False)
            out[k] = v if len(text) <= 2000 else text[:2000] + "…"
    return out


class _Assembler:
    def __init__(self, started: float) -> None:
        self.started = started
        self.c = Completion()
        self.calls: dict[int, dict] = {}
        self.done = False

    def feed(self, chunk: dict) -> None:
        if "error" in chunk and chunk["error"]:
            raise _StreamError(chunk["error"])
        if chunk.get("usage"):
            self.c.usage = chunk["usage"]
        cost = _find_cost(chunk)
        if cost is not None:
            self.c.cost = cost
        self.c.model = chunk.get("model") or self.c.model
        self.c.provider.update(_provider_fields(chunk))
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or choice.get("message") or {}
            self.c.provider.update(_provider_fields(delta))
            text = delta.get("content") or ""
            reasoning = delta.get("reasoning_content") or delta.get("reasoning") or ""
            if (text or reasoning or delta.get("tool_calls")) and self.c.ttft is None:
                self.c.ttft = round(time.monotonic() - self.started, 3)
            self.c.content += text
            self.c.reasoning += reasoning if isinstance(reasoning, str) else ""
            for tc in delta.get("tool_calls") or []:
                index = tc.get("index")
                if index is None:  # some servers omit it: a new id starts a new call, otherwise continue the last
                    index = len(self.calls) if tc.get("id") or not self.calls else max(self.calls)
                call = self.calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
                call["id"] = tc.get("id") or call["id"]
                fn = tc.get("function") or {}
                call["name"] += fn.get("name") or ""
                args = fn.get("arguments")
                call["arguments"] += args if isinstance(args, str) else (json.dumps(args) if args else "")
            if choice.get("finish_reason"):
                self.c.finish_reason = choice["finish_reason"]

    def result(self) -> Completion:
        c = self.c
        if "<think>" in c.content:  # reasoning inside the text (llama.cpp without a reasoning parser, some APIs)
            c.reasoning += "".join(m.group(1) for m in THINK.finditer(c.content))
            c.content = THINK.sub("", c.content)
        c.content = c.content.strip()
        c.tool_calls = [ToolCall(v["id"] or f"call_{i}", v["name"], v["arguments"])
                        for i, v in sorted(self.calls.items())]
        return c


class _StreamError(Exception):
    def __init__(self, error: Any) -> None:
        self.error = error
        super().__init__(json.dumps(error, ensure_ascii=False)[:500] if not isinstance(error, str) else error[:500])


async def _attempt(http: httpx.AsyncClient, url: str, headers: dict, body: dict) -> Completion:
    started = time.monotonic()
    asm = _Assembler(started)
    async with http.stream("POST", url, headers=headers, json=body) as resp:
        if resp.status_code != 200:
            text = (await resp.aread()).decode("utf-8", "replace")[:1000]
            raise httpx.HTTPStatusError(f"HTTP {resp.status_code}: {text}", request=resp.request, response=resp)
        if "text/event-stream" not in resp.headers.get("content-type", ""):
            asm.feed(json.loads(await resp.aread()))  # server ignored stream=true
            asm.done = True
        else:
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    asm.done = True
                    break
                if data:
                    asm.feed(json.loads(data))
    c = asm.result()
    if not asm.done and c.finish_reason is None:
        raise httpx.ReadError("stream ended without finish reason or [DONE]")
    c.seconds = round(time.monotonic() - started, 3)
    return c


async def complete(http: httpx.AsyncClient, base_url: str, api_key: str | None, body: dict, *, retries: int = 20,
                   pause: float = 30.0, on_retry=None) -> Completion:
    """One streamed chat completion with retries for provider and network failures; on_retry(message) is called
    before each retry."""
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body = {**body, "stream": True, "stream_options": {"include_usage": True}}
    local = is_local(base_url)
    waited, attempt = 0.0, 0
    while True:
        attempt += 1
        try:
            c = await _attempt(http, url, headers, body)
            c.attempts, c.wait_seconds = attempt, round(waited, 1)
            return c
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status in CONFIG_STATUS:
                raise ConfigError(str(e)) from e
            retry = status in RETRY_STATUS or (not local and (status >= 500 or OVERLOAD.search(str(e))))
            kind = "provider" if retry else "server"
            message = str(e)
        except _StreamError as e:
            retry = not local or bool(OVERLOAD.search(str(e)))
            kind, message = ("provider" if retry else "server"), f"error in stream: {e}"
        except (httpx.TransportError, json.JSONDecodeError) as e:
            retry, kind, message = True, "network", f"{type(e).__name__}: {e}"
            if local and isinstance(e, httpx.ConnectError):
                retries, pause = min(retries, 3), min(pause, 10.0)
                message = f"local server refuses connections: {e}"
        if not retry or attempt > retries:
            return Completion(error=message[:1000], error_kind=kind, attempts=attempt, wait_seconds=round(waited, 1))
        delay = min(pause, 2.0 * attempt) if kind == "network" else pause
        if on_retry:
            on_retry(f"{kind} error, retry {attempt}/{retries} in {delay:.0f}s: {message[:120]}")
        await asyncio.sleep(delay)
        waited += delay
