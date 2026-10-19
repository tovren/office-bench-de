"""Runs tasks against a model: the chat loop with tool calls, files and the run log.

A run folder (runs/<run>/<model>/) holds
- meta.json: model config (without key), profile, tool and task hashes, harness version
- log.jsonl: one line per task run (format: docs/harness.md)
- files/: the raw arguments of every tool call and every file the tool built, named
  <task>-<rep>__r<round>c<index>__<name>; the round counts across turns, so the highest (round, index) is the file
  the user ends up with.

Per user message the model gets at most `max_rounds` rounds with tool calls; if it still calls tools after that,
the calls are not executed and the turn ends without a final answer (like Open WebUI's tool-call limit).
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import time
import urllib.parse
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import httpx

from officebench import tool as office_tool
from officebench.config import ModelConfig, Profile
from officebench.tasks import Task, extra_tool, selection_hash

from .client import Completion, ConfigError, complete

LOG_FORMAT = 1
MAX_LOGGED_TEXT = 4000


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def harness_version() -> str:
    try:
        out = subprocess.run(["git", "-C", str(Path(__file__).parent), "describe", "--always", "--dirty"],
                             capture_output=True, text=True, timeout=10)
        commit = out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        commit = None
    return f"{version('office-bench-de')}" + (f"+{commit}" if commit else "")


def safe_name(name: str) -> str:
    return re.sub(r"[/\\\x00-\x1f]", "_", name)[:150] or "_"


def read_log(path: Path) -> dict[tuple[str, int], dict]:
    """Last log line per (task, rep)."""
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                out[(rec["task"], rec["rep"])] = rec
    return out


def _round_entry(c: Completion, turn: int) -> dict:
    entry = {"turn": turn, "seconds": c.seconds, "ttft": c.ttft, "attempts": c.attempts,
             "wait_seconds": c.wait_seconds, "finish_reason": c.finish_reason, "usage": c.usage, "cost": c.cost,
             "model": c.model, "provider": c.provider, "content": c.content[:MAX_LOGGED_TEXT],
             "reasoning_chars": len(c.reasoning), "calls": []}
    if c.error:
        entry.update(error=c.error, error_kind=c.error_kind)
    return entry


async def run_task(http: httpx.AsyncClient, model: ModelConfig, api_key: str | None, profile: Profile, task: Task,
                   rep: int, files_dir: Path, progress=print) -> dict:
    """One task run: all turns, all rounds. Returns the log record."""
    extras = {name: extra_tool(name) for name in task.spec.extra_tools}
    tools = office_tool.SPECS + [e["spec"] for e in extras.values()]
    tag = f"{task.id}-{rep}"
    messages: list[dict] = [{"role": "system", "content": profile.system_prompt}]
    rec = {"format": LOG_FORMAT, "task": task.id, "rep": rep, "task_hash": task.hash, "started": now(),
           "turns": [], "rounds": [], "outcome": None}
    round_no = 0
    for t_index, turn in enumerate(task.turns):
        user_text = profile.render_user_message(turn.text, turn.attachments)
        messages.append({"role": "user", "content": user_text})
        end, tool_rounds = None, 0
        while end is None:
            body = {"model": model.model, "messages": messages, "tools": tools, **model.params}
            c = await complete(http, model.base_url, api_key, body,
                               on_retry=lambda m: progress(f"  {tag}: {m}"))
            entry = _round_entry(c, t_index)
            rec["rounds"].append(entry)
            if c.error:
                end = "error"
                break
            assistant: dict = {"role": "assistant", "content": c.content or None}
            if c.tool_calls:
                assistant["tool_calls"] = [{"id": tc.id, "type": "function",
                                            "function": {"name": tc.name, "arguments": tc.arguments}}
                                           for tc in c.tool_calls]
            messages.append(assistant)
            if not c.tool_calls:
                end = "answer"
                break
            if tool_rounds >= profile.max_rounds:  # limit reached: calls are not executed, no final answer
                entry["not_executed"] = [{"name": tc.name, "arguments_chars": len(tc.arguments)}
                                         for tc in c.tool_calls]
                end = "round_limit"
                break
            tool_rounds += 1
            for index, tc in enumerate(c.tool_calls):
                prefix = f"{tag}__r{round_no}c{index}__"
                fn = urllib.parse.quote(tc.name, safe="")[:120] or "_empty_"
                (files_dir / f"{prefix}{fn}.json").write_text(tc.arguments, encoding="utf-8")
                result = await office_tool.execute(tc.name, tc.arguments, extras, profile.valves)
                call = {"name": tc.name, "status": result.status, "done": result.done,
                        "arguments_chars": len(tc.arguments), "result": result.content[:MAX_LOGGED_TEXT]}
                if result.dropped:
                    call["dropped"] = result.dropped
                for f in result.files:
                    path = files_dir / f"{prefix}{safe_name(f.name)}"
                    path.write_bytes(f.data)
                    call["file"] = path.name
                entry["calls"].append(call)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result.content})
            round_no += 1
        rec["turns"].append({"end": end, "rounds": sum(1 for r in rec["rounds"] if r["turn"] == t_index)})
        if end == "error":
            last = rec["rounds"][-1]
            rec.update(error=last["error"], error_kind=last["error_kind"])
            break
    rec["outcome"] = rec["turns"][-1]["end"]
    final = rec["rounds"][-1] if rec["rounds"] else {}
    rec["final_answer"] = final.get("content", "") if rec["outcome"] == "answer" else None
    rec["finished"] = now()
    return rec


async def run(model: ModelConfig, profile: Profile, tasks: list[Task], repeats: int, out: Path, *,
              retry_failed: bool = False, progress=print) -> Path:
    """Run every task `repeats` times; resumes an existing run folder (finished task runs are skipped)."""
    folder = out / model.name
    files_dir = folder / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    meta = {"model": model.public(), "profile": profile.model_dump(mode="json"), "profile_hash": profile.digest(),
            "tool_hash": office_tool.tool_hash(), "tool_commit": office_tool.SOURCE_COMMIT,
            "tasks": [t.id for t in tasks], "task_selection_hash": selection_hash(tasks), "repeats": repeats,
            "harness": harness_version()}
    meta_path = folder / "meta.json"
    old = {}
    if meta_path.exists():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        changed = [k for k in ("model", "profile_hash", "tool_hash") if old.get(k) != meta[k]]
        if changed:
            raise ValueError(f"{folder} was run with a different {', '.join(changed)}; use a new run name")
    meta["started"] = old.get("started") or now()
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log_path = folder / "log.jsonl"
    done = read_log(log_path)
    todo = [(t, r) for t in tasks for r in range(repeats)
            if (t.id, r) not in done or (retry_failed and done[(t.id, r)].get("error_kind") in ("provider", "network"))]
    progress(f"{model.name}: {len(todo)} task runs to do ({len(tasks) * repeats - len(todo)} already in the log)")
    api_key = model.api_key()
    sem = asyncio.Semaphore(model.concurrency)
    lock = asyncio.Lock()
    counter = {"n": 0}
    started = time.monotonic()

    async def one(http, task, rep):
        async with sem:
            for old_file in files_dir.glob(f"{task.id}-{rep}__*"):  # a retried run starts clean
                old_file.unlink()
            rec = await run_task(http, model, api_key, profile, task, rep, files_dir, progress)
            async with lock:
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                counter["n"] += 1
                progress(f"  [{counter['n']}/{len(todo)}] {task.id}-{rep}: {rec['outcome']}"
                         + (f" ({rec.get('error_kind')}: {rec.get('error', '')[:80]})" if rec.get("error") else "")
                         + f"  {time.monotonic() - started:.0f}s")

    timeout = httpx.Timeout(connect=30, read=600, write=60, pool=None)
    async with httpx.AsyncClient(timeout=timeout) as http:
        jobs = [asyncio.create_task(one(http, t, r)) for t, r in todo]
        try:
            await asyncio.gather(*jobs)
        except ConfigError:
            for j in jobs:
                j.cancel()
            raise
    return folder


def run_sync(*args, **kwargs) -> Path:
    return asyncio.run(run(*args, **kwargs))
