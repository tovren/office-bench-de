"""Scoring: one Result per task run from the run log, the built files and the content check.

    obench score RUN_FOLDER...      writes results.jsonl into every model folder

As a module: score_run(model_folder) -> [Result]; write_results(folder, results); load_results(folder) (scores again
when results.jsonl is missing or older than the log); model_folders(paths) finds the model folders of run folders.

Definitions (used by the report; for users explained in docs/scoring.md):
- office call: a call whose name is not one of the task's extra tools, also a misspelt function name (the model
  tried the office tool). Calls of extra tools never count as office calls, even when their arguments fail to parse.
- done: an office call whose result starts with "Done" (the tool built a file).
- file_first_call: the first office call (by round, then index) is done.
- turns: per user message: sent, office_call, file (a done call), fulfilled = sent and, by the turn's `expect`, a
  file (file), no office call (no_file) or anything (any). turns_ok: all turns fulfilled.
- file_at_end: file tasks: a done call in the last turn that expects a file (without such a turn: any done call).
- delivered_file: the file of the last done call, the one the user ends up with. content_ok / clean: content check
  of that file (Findings.ok = no hard defect, .clean = no defect at all); False without a file; None when the file
  of the last done call is missing in files/ (then success is None too).
- previous_file: follow-up tasks: the file last built in an earlier turn than the delivered one; the content check
  compares with it (`retained`). None when the delivered file comes from the first turn.
- final answer: the text of the last round if the last turn ended with an answer (a round without tool calls); an
  empty text is no final answer. The log keeps 4000 characters (reply_truncated).
- reply check ([reply].topics / forbidden, file tasks too): every topic is in the final answer and nothing
  forbidden. Not determinable (None) when the logged answer is truncated and a topic is missing or nothing forbidden
  was found so far (the cut part could change it). Misses also go into other_defects (hard).
- further reply checks ([reply].words_max, no_markdown): soft defects in other_defects; not part of success.
- behavior check ([behavior]): every tools_expected was called and no tools_forbidden (names of the task's extra
  tools); violations are hard defects in other_defects.
- success: file tasks (file, follow_up): file_at_end, turns_ok and content_ok, plus the reply check if the task has
  [reply].topics/forbidden and the behavior check if it has [behavior]. no_file: turns_ok (no office call in turns
  that expect no file), a final answer, the reply check and the behavior check. None = not determinable.
- scored: False when a provider or network failure (the client retried and gave up; the model cannot help it) ended
  the task run before its outcome was settled: file tasks before a done call in the last file turn, no_file tasks
  before the final answer (unless an unnecessary office call had already decided it). Whether the content is good
  does not matter for that. Also not scored: task runs of the run's selection without a log line (run aborted or
  still going; outcome "missing") and tasks that no longer exist. A server error (the model's own server failed:
  the user's chat would break) counts as a failed run.
- round_limit: the last turn ended at the profile's max_rounds (the calls of that last answer were not executed,
  like Open WebUI's tool-call limit); the missing final answer is then due to the limit and not counted as "no final
  answer". Text in that last answer is no final answer either (the model still wanted to call tools).
- rejections: every office call that is not done, with its category (CATEGORIES) and file_after (a file came later
  in the same turn); recovered: a file came after the first rejection.
- claims_file: a text of a turn without a done call says a file was created or is ready (German pattern, sentences
  with negations or conditions do not count). invented_links: Markdown links, URLs and sandbox: paths in the texts.
- extra_tools_offered / extra_tools_called (the task's extra tools; called = the model called it, whatever the
  arguments); unnecessary_call: an office call in a turn that expects no file (None without such a turn).
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from officebench.checks.content import check_files
from officebench.checks.registry import REPLY_CHECKS
from officebench.checks.reply import check_behavior, reply_defects
from officebench.checks.text import forbidden_found, missing_topics
from officebench.harness.runner import MAX_LOGGED_TEXT, read_log
from officebench.tasks import Task, extra_tool, load_tasks

RESULTS = "results.jsonl"
CATEGORIES = {
    "json": "invalid JSON", "schema": "schema / required field", "garbled": "garbled arguments",
    "validation": "tool's content validation", "wrong_function": "wrong function", "not_object": "not a JSON object",
    "exception": "exception in the tool", "other": "other",
}
OUTAGE = {"provider", "network"}  # failures the model cannot help; server errors count against the model setup

# The conversations are German: a sentence claims a file if it names one and says it is ready; negations and
# conditions mark admitted failures or promises.
FILE_WORD = (r"(?:datei|dokument|word-?dokument|word-?datei|excel-?(?:datei|tabelle|mappe)|arbeitsmappe|"
             r"tabellenkalkulation|präsentation|powerpoint|foliensatz|xlsx|docx|pptx)\w*")
CLAIM = re.compile(
    rf"\b{FILE_WORD}[^.!?\n]{{0,120}}\b(?:erstellt|angelegt|generiert|gespeichert|aufbereitet|exportiert|"
    r"heruntergeladen|bereitgestellt|fertig|bereit|angehängt)\b"
    rf"|\b(?:habe|hab)\b[^.!?\n]{{0,80}}\b{FILE_WORD}[^.!?\n]{{0,80}}\b(?:erstellt|angelegt|generiert|gebaut)\b",
    re.I)
NEGATION = re.compile(r"\b(?:nicht|kein\w*|leider|fehler\w*|fehlgeschlagen|gescheitert|problem\w*|versuch\w*|"
                      r"konnte|kann|könnte|würde|sobald|falls|wenn|soll)\b", re.I)
LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*<?([^)\s>]+)[^)]*\)"
                  r"|((?:https?|file|attachment)://[^\s)\]>\"'`]+)"
                  r"|((?:sandbox:|/mnt/data/)[^\s)\]>\"'`]+)", re.I)
INTERNAL = {"internal": True}


@dataclass
class Result:
    run: str
    model: str
    task: str
    rep: int
    title: str = ""
    kind: str = "file"  # file | follow_up | no_file
    file_type: str | None = None
    task_hash: str | None = None
    task_changed: bool = False  # the task file changed since the run (the checks of the current version apply)
    today: str | None = None
    outcome: str = "missing"  # answer | round_limit | error | missing (no log line)
    error_kind: str | None = None  # provider | network | server
    error: str | None = None
    scored: bool = True
    rounds: int = 0
    office_calls: int = 0  # all statuses, without extra tools
    extra_calls: int = 0
    extra_tools_offered: list = field(default_factory=list)
    extra_tools_called: list = field(default_factory=list)  # in order of the first call
    file_first_call: bool | None = None
    file_at_end: bool | None = None
    rounds_to_file: int | None = None
    seconds_to_file: float | None = None  # model time (sum of round durations) up to the first file
    seconds: float = 0.0
    wait_seconds: float = 0.0  # pauses between retries of provider/network failures
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float | None = None
    rejections: list = field(default_factory=list)  # {round, index, turn, name, category, text, file_after}
    recovered: bool | None = None
    files_built: int = 0
    extra_files: bool = False  # more files built than turns that expect one
    delivered_file: str | None = None
    previous_file: str | None = None
    turns: list = field(default_factory=list)  # {turn, expect, sent, office_call, file, fulfilled}
    turns_ok: bool | None = None
    unnecessary_call: bool | None = None
    final_answer: bool = False
    round_limit: bool = False
    reply_truncated: bool = False
    claims_file: bool = False
    invented_links: list = field(default_factory=list)
    missing_reply_topics: list | None = None  # None: the task has no [reply].topics
    forbidden_reply_hits: list | None = None  # None: the task has no [reply].forbidden
    missing_tools: list | None = None  # None: the task has no [behavior]
    unwanted_tools: list | None = None
    other_defects: list = field(default_factory=list)  # {label, severity, check, text} of reply and behavior checks
    metrics: dict = field(default_factory=dict)  # of the content check of the delivered file
    content_ok: bool | None = None
    clean: bool | None = None
    hard_defects: list = field(default_factory=list)  # labels, each once
    soft_defects: list = field(default_factory=list)
    defects: list = field(default_factory=list)  # {label, severity, check, text}
    success: bool | None = None
    notes: list = field(default_factory=list)
    file_path: Path | None = field(default=None, metadata=INTERNAL)
    previous_path: Path | None = field(default=None, metadata=INTERNAL)
    answer_text: str = field(default="", metadata=INTERNAL)
    file_lost: bool = field(default=False, metadata=INTERNAL)  # the file of the last done call is not in files/
    unknown_task: bool = field(default=False, metadata=INTERNAL)

    @property
    def file_task(self) -> bool:
        return self.kind != "no_file"

    @property
    def has_reply_check(self) -> bool:
        return self.missing_reply_topics is not None or self.forbidden_reply_hits is not None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if not self.__dataclass_fields__[k].metadata.get("internal")}

    @classmethod
    def from_dict(cls, data: dict) -> Result:
        names = {f.name for f in fields(cls) if not f.metadata.get("internal")}
        return cls(**{k: v for k, v in data.items() if k in names})


# ------------------------------------------------------------------------------------------------------ helpers --

def first_line(text: str) -> str:
    """The specific reason of a rejection: the first '- ' bullet, else the first line."""
    bullets = [z.strip()[2:] for z in text.splitlines() if z.strip().startswith("- ")]
    if bullets:
        return bullets[0]
    return next((z.strip() for z in text.splitlines() if z.strip() and z.strip() not in "{}"), text.strip())


def category(status: str | None, text: str) -> str:
    """Category of a rejected office call from the call status (officebench.tool.CallResult) and the result text."""
    text = str(text or "")
    if status == "parse_error":
        return "json"
    if status == "not_object":
        return "not_object"
    if status == "unknown_function":
        return "wrong_function"
    if status == "exception":
        return "schema" if re.search(r"required positional argument|unexpected keyword argument", text) else "exception"
    if text.startswith("The file could not be created because of an internal error"):
        return "exception"
    main = first_line(text)
    if "garbled" in main:
        return "garbled"
    if "the JSON is invalid" in main or "not valid JSON" in main:
        return "json"
    if re.search(r"Field required|Input should be|Extra inputs|at most \d+|at least \d+|should have at", main):
        return "schema"
    if text.startswith("The file was NOT created"):
        return "validation"
    return "other"


def claims_file(text: str) -> bool:
    return any(CLAIM.search(s) and not NEGATION.search(s) for s in re.split(r"(?<=[.!?])\s+|\n+", text or ""))


def links(text: str) -> list[str]:
    return [next(g for g in m.groups() if g) for m in LINK.finditer(text or "")]


def reply_ok(r: Result) -> bool | None:
    """Reply check: all topics there and nothing forbidden; None if the truncated log could hide the outcome."""
    missing, hits = r.missing_reply_topics or [], r.forbidden_reply_hits or []
    if hits:
        return False
    if r.reply_truncated and (missing or r.forbidden_reply_hits is not None):
        return None
    return not missing


def behavior_ok(r: Result) -> bool:
    return not (r.missing_tools or r.unwanted_tools)


def _defect(d) -> dict:
    return {"label": d.label, "severity": d.severity, "check": d.check, "text": str(d)}


def _function_names(task: Task) -> dict:
    """{function name in the spec: extra tool name} of the task's extra tools (the names usually agree)."""
    out = {}
    for name in task.spec.extra_tools:
        try:
            out[extra_tool(name)["spec"]["function"]["name"]] = name
        except (OSError, KeyError, ValueError):
            out[name] = name
    return out


# --------------------------------------------------------------------------------------------- one task run --

def _from_log(r: Result, rec: dict, task: Task, files_dir: Path) -> None:
    rounds = rec.get("rounds") or []
    r.outcome = rec.get("outcome") or "error"
    r.error_kind = rec.get("error_kind")
    r.error = str(rec["error"])[:300] if rec.get("error") else None
    r.rounds = len(rounds)
    r.seconds = round(sum(x.get("seconds") or 0 for x in rounds), 1)
    r.wait_seconds = round(sum(x.get("wait_seconds") or 0 for x in rounds), 1)
    r.tokens_in = sum((x.get("usage") or {}).get("prompt_tokens") or 0 for x in rounds)
    r.tokens_out = sum((x.get("usage") or {}).get("completion_tokens") or 0 for x in rounds)
    costs = [x["cost"] for x in rounds if isinstance(x.get("cost"), (int, float))]
    r.cost = round(sum(costs), 6) if costs else None

    extra = _function_names(task)
    done = []  # (round, index, turn, file name or None)
    first_office = None
    elapsed = 0.0
    for i, rd in enumerate(rounds):
        turn = rd.get("turn", 0)
        elapsed += rd.get("seconds") or 0
        for j, c in enumerate(rd.get("calls") or []):
            if c.get("name") in extra:
                r.extra_calls += 1
                if extra[c["name"]] not in r.extra_tools_called:
                    r.extra_tools_called.append(extra[c["name"]])
                continue
            r.office_calls += 1
            if first_office is None:
                first_office = bool(c.get("done"))
            if c.get("done"):
                if not done:
                    r.rounds_to_file, r.seconds_to_file = i + 1, round(elapsed, 1)
                done.append((i, j, turn, c.get("file")))
            else:
                text = str(c.get("result", ""))
                r.rejections.append({"round": i, "index": j, "turn": turn, "name": c.get("name"),
                                     "category": category(c.get("status"), text), "text": first_line(text)[:160]})
    for a in r.rejections:
        a["file_after"] = any((i, j) > (a["round"], a["index"]) and t == a["turn"] for i, j, t, _ in done)
    if r.rejections:
        first = min((a["round"], a["index"]) for a in r.rejections)
        r.recovered = any((i, j) > first for i, j, *_ in done)
    r.file_first_call = bool(first_office)
    r.files_built = len(done)

    by_turn = defaultdict(list)
    for rd in rounds:
        by_turn[rd.get("turn", 0)].append(rd)
    sent = len(rec.get("turns") or [])

    def office(rd):
        return [c for c in rd.get("calls") or [] if c.get("name") not in extra]

    for t, turn in enumerate(task.turns):
        rs = by_turn.get(t, [])
        called = any(office(rd) for rd in rs)
        built = any(c.get("done") for rd in rs for c in office(rd))
        was_sent = t < sent
        fulfilled = was_sent and (built if turn.expect == "file" else not called if turn.expect == "no_file" else True)
        r.turns.append({"turn": t, "expect": turn.expect, "sent": was_sent, "office_call": called, "file": built,
                        "fulfilled": fulfilled})
    r.turns_ok = all(t["fulfilled"] for t in r.turns)
    file_turns = [t for t in r.turns if t["expect"] == "file"]
    r.file_at_end = file_turns[-1]["file"] if file_turns else bool(done)
    if any(t["expect"] == "no_file" for t in r.turns):
        r.unnecessary_call = any(t["office_call"] for t in r.turns if t["expect"] == "no_file")
    expected = sum(1 for t in r.turns if t["expect"] != "no_file")
    if r.files_built > max(1, expected):
        r.extra_files = True
        r.notes.append(f"{r.files_built} files built")

    # the delivered file and the one of an earlier turn it is compared with
    if done:
        *_, last_turn, name = done[-1]
        r.delivered_file = name
        r.file_path = files_dir / name if name else None
        r.file_lost = r.file_path is None or not r.file_path.is_file()
        if r.file_lost:
            r.notes.append("file of the last done call not in files/")
        earlier = [d for d in done if d[2] < last_turn and d[3]]
        if earlier:
            r.previous_file = earlier[-1][3]
            r.previous_path = files_dir / r.previous_file

    # texts the user reads
    for t in r.turns:
        texts = [rd.get("content") or "" for rd in by_turn.get(t["turn"], [])]
        if not t["file"] and any(claims_file(x) for x in texts):
            r.claims_file = True
        for x in texts:
            r.invented_links += [u for u in links(x) if u not in r.invented_links]
    answer = (rec.get("final_answer") or "").strip() if r.outcome == "answer" else ""
    r.final_answer = bool(answer)
    r.answer_text = answer
    r.reply_truncated = r.final_answer and len(rec.get("final_answer") or "") >= MAX_LOGGED_TEXT
    r.round_limit = r.outcome == "round_limit"
    for t, end in enumerate(rec.get("turns") or []):
        if end.get("end") == "round_limit" and t < len(rec["turns"]) - 1:
            r.notes.append(f"turn {t + 1}: round limit reached")
    if r.round_limit:
        r.notes.append("round limit reached, hence no final answer")
    elif not r.final_answer and r.outcome != "error":
        r.notes.append("no final answer")
    if r.error:
        r.notes.append(f"error ({r.error_kind}): {r.error[:80]}")

    # reply and behavior checks
    reply = task.spec.reply
    if reply.topics:
        r.missing_reply_topics = missing_topics(answer, reply.topics) if answer else list(reply.topics)
        if r.missing_reply_topics:
            label, severity = REPLY_CHECKS["topics"]
            r.other_defects.append({"label": label, "severity": severity, "check": "topics",
                                    "text": f"topic missing in the reply: {', '.join(r.missing_reply_topics)}"})
    if reply.forbidden:
        r.forbidden_reply_hits = forbidden_found(answer, reply.forbidden) if answer else []
        if r.forbidden_reply_hits:
            label, severity = REPLY_CHECKS["forbidden"]
            r.other_defects.append({"label": label, "severity": severity, "check": "forbidden",
                                    "text": f"forbidden in the reply: {', '.join(r.forbidden_reply_hits)}"})
    if answer:
        r.other_defects += [_defect(d) for d in reply_defects(answer, reply)]
    behavior = task.spec.behavior
    if behavior.tools_expected or behavior.tools_forbidden:
        r.missing_tools, r.unwanted_tools, found = check_behavior(r.extra_tools_called, behavior)
        r.other_defects += [_defect(d) for d in found]


def settle(r: Result) -> None:
    """Sets success and scored (definitions in the module docstring)."""
    if r.outcome == "missing" or r.unknown_task:
        r.scored, r.success = False, None
        return
    if r.file_task:
        if r.file_lost:
            r.content_ok = r.clean = r.success = None
        elif r.delivered_file is None:
            r.content_ok = r.clean = r.success = False
        elif not r.file_at_end or not r.turns_ok or not behavior_ok(r):
            r.success = False
        elif r.content_ok and r.has_reply_check:
            r.success = reply_ok(r)
        else:
            r.success = r.content_ok
    elif not behavior_ok(r):
        r.success = False
    else:
        reply = reply_ok(r)
        r.success = None if reply is None else bool(r.turns_ok and r.final_answer and reply)
    if r.error_kind in OUTAGE:  # scored only if the outcome was settled before the outage, whatever the content
        r.scored = bool(r.file_at_end) if r.file_task else bool(r.final_answer or r.unnecessary_call)


# ------------------------------------------------------------------------------------------------- a run --

def score_run(folder: Path) -> list[Result]:
    """Results of a model folder (runs/<run>/<model>/); one content-check call for all delivered files."""
    folder = Path(folder)
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    log = read_log(folder / "log.jsonl")
    tasks = load_tasks()
    today = (meta.get("profile") or {}).get("today")
    model = (meta.get("model") or {}).get("name") or folder.name
    wanted = [(t, rep) for t in meta.get("tasks") or [] for rep in range(int(meta.get("repeats") or 0))]
    keys = sorted(set(log) | set(wanted), key=lambda k: (k[0], k[1]))
    results = []
    for task_id, rep in keys:
        r = Result(run=folder.parent.name, model=model, task=task_id, rep=rep, today=today)
        task = tasks.get(task_id)
        rec = log.get((task_id, rep))
        if task is None:
            r.unknown_task = True
            r.outcome = (rec or {}).get("outcome") or "missing"
            r.notes.append("task no longer exists")
        else:
            s = task.spec
            r.title, r.kind, r.file_type, r.extra_tools_offered = s.title, s.kind, s.file_type, list(s.extra_tools)
        if rec is None:
            r.notes.append("no log line (run aborted or still going)")
            r.file_first_call = r.file_at_end = r.turns_ok = None
        elif task is not None:
            r.task_hash = rec.get("task_hash")
            if r.task_hash and r.task_hash != task.hash:
                r.task_changed = True
                r.notes.append(f"task changed since the run (log {r.task_hash}, now {task.hash})")
            _from_log(r, rec, task, folder / "files")
        results.append(r)
    _check_content(results, tasks, today)
    for r in results:
        settle(r)
    return results


def _check_content(results: list[Result], tasks: dict, today) -> None:
    todo = [r for r in results if r.file_task and r.file_path is not None and not r.file_lost and r.task in tasks]
    previous = {r.file_path: r.previous_path if r.previous_path and r.previous_path.is_file() else None for r in todo}
    found = check_files([(r.file_path, tasks[r.task], previous[r.file_path]) for r in todo], today=today)
    for r in todo:
        f = found[r.file_path]
        r.content_ok, r.clean, r.metrics = bool(f.ok), bool(f.clean), dict(f.metrics)
        r.defects = [_defect(d) for d in f.defects]
        r.hard_defects = list(dict.fromkeys(d.label for d in f.hard))
        r.soft_defects = list(dict.fromkeys(d.label for d in f.soft))


def write_results(folder: Path, results: list[Result]) -> Path:
    path = Path(folder) / RESULTS
    path.write_text("".join(json.dumps(r.to_dict(), ensure_ascii=False) + "\n" for r in results), encoding="utf-8")
    return path


def load_results(folder: Path, rescore: bool = False) -> list[Result]:
    """results.jsonl of a model folder; scored (and written) again if missing, older than the log or rescore."""
    folder = Path(folder)
    path, log = folder / RESULTS, folder / "log.jsonl"
    if rescore or not path.exists() or (log.exists() and log.stat().st_mtime > path.stat().st_mtime):
        results = score_run(folder)
        write_results(folder, results)
        return results
    return [Result.from_dict(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line]


def model_folders(paths) -> list[Path]:
    """Model folders (with meta.json) among the paths: each path is a model folder or a run folder holding them."""
    out = []
    for p in map(Path, paths):
        found = [p] if (p / "meta.json").is_file() else sorted(
            q for q in p.iterdir() if (q / "meta.json").is_file()) if p.is_dir() else []
        if not found:
            raise FileNotFoundError(f"{p}: neither a model folder (meta.json) nor a run folder with model folders")
        out += found
    return list(dict.fromkeys(out))


def main(paths: list[str]) -> int:
    for folder in model_folders(paths):
        results = score_run(folder)
        path = write_results(folder, results)
        scored = [r for r in results if r.scored]
        print(f"{path}: {len(results)} task runs, {len(scored)} scored, "
              f"{sum(1 for r in scored if r.success)} successful, "
              f"{sum(1 for r in scored if r.success is None)} not determinable")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
