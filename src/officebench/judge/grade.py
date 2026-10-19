"""Quality judge: an LLM grades each delivered file (or final answer) on five criteria, without knowing the model.

    obench judge RUN_FOLDER... --judge configs/judges/<judge>.toml [--samples 2] [--out grades.jsonl]

Per model and task the judge sees the first `samples` task runs not ended by an outage that delivered a file (any
such run for tasks without a file): the file as Markdown text
(render.render_text: Excel with formulas and recalculated values) plus images of its pages, or the final chat answer
for tasks without a file. It also sees what the model saw — the user's messages, the text of attached files and the
reference date — and the task's checklist (what a 5 looks like). Files are copied with neutral timestamps first, and
nothing in the request names the model. Each file is graded in its own request against fixed anchors
(criteria.toml), so grades do not depend on which other files are graded.

Output: one JSON line per graded item (model, task, rep, file, judge, grades, mean, reasons, usage, cost); existing
lines are kept, so an interrupted run resumes.
"""

from __future__ import annotations

import asyncio
import base64
import json
import random
import re
import shutil
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import httpx

from officebench.checks.core import REFERENCE_DATE
from officebench.config import ModelConfig
from officebench.harness.client import complete
from officebench.runs import OUTAGE, delivered_files, read_jsonl, read_log, read_meta
from officebench.tasks import Task, load_tasks

from .render import neutral_copy, render_images, render_texts

HERE = Path(__file__).resolve().parent
CRITERIA = tomllib.loads((HERE / "criteria.toml").read_text(encoding="utf-8"))["criterion"]
CRITERIA_IDS = tuple(c["id"] for c in CRITERIA)
FILE_KINDS = {"docx": "Word document", "xlsx": "Excel workbook", "pptx": "PowerPoint presentation"}
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MAX_IMAGES = 12

SYSTEM = """You are a strict, fair reviewer in a blind review. Language models used a tool to create files for German \
office users. You grade one file at a time against fixed criteria. You do not know which model made it; do not guess.

Grade the file on its own against the descriptions, not against other files you may have seen, and use the whole \
scale. A single severe error (formulas stored as text, an empty required table, a document that breaks off) may on \
its own push the affected grades down to 1–2. Length is not a value in itself.

Check before you grade: recalculate sums, formula results, costs and percentages; check every date with its weekday, \
every calendar week, whether deadlines fall on weekends or holidays, and whether appointments lie before the reference \
date. For tasks with attachments, check that facts were taken over correctly and completely and nothing was invented. \
Errors that only come from the conversion to text or image do not count."""


@dataclass
class Item:
    model: str
    task: Task
    rep: int
    file: Path | None  # None: final answer of a task without a file
    answer: str | None = None
    today: str = REFERENCE_DATE.isoformat()

    @property
    def key(self) -> tuple:
        return (self.model, self.task.id, self.rep)


def _today_text(iso: str) -> str:
    d = date.fromisoformat(iso[:10])
    return f"{WEEKDAYS[d.weekday()]}, {d.strftime('%d.%m.%Y')}"


def _fence(text: str) -> str:
    ticks = "`" * max(3, max((len(m) for m in re.findall(r"`+", text)), default=0) + 1)
    return f"{ticks}text\n{text.rstrip()}\n{ticks}"


def task_text(task: Task, today: str) -> str:
    """What the model was asked: user messages, attachments, reference date, what is graded, checklist, criteria."""
    turns = task.turns
    if len(turns) == 1:
        parts = ["## The task given to the model", "> " + turns[0].text.replace("\n", "\n> ")]
    else:
        parts = ["## The conversation with the model"]
        parts += [f"**User message {i}:**\n\n> " + t.text.replace("\n", "\n> ") for i, t in enumerate(turns, 1)]
    attachments = [a for t in turns for a in t.attachments]
    if attachments:
        parts.append(f"The user attached {len(attachments)} file(s); the model got their full text (read from the "
                     "file, without layout). Check that facts from them were taken over correctly and completely and "
                     "that nothing was invented.")
        parts += [f"**Attachment „{a.name}“:**\n\n{_fence(a.text)}" for a in attachments]
    parts.append(f"Reference date of the run (\"today\" for the model): **{_today_text(today)}**.")
    spec = task.spec
    if spec.kind == "no_file":
        parts.append("No file was asked for here, but an answer in the chat. You grade the answer text; \"structure\" "
                     "means the outline and readability of the answer.")
    elif spec.kind == "follow_up":
        parts.append(f"This was a conversation with {len(turns)} messages; the model answered after each. A "
                     f"{FILE_KINDS[spec.file_type]} was expected. You grade the **last delivered file**: it should "
                     "meet the wishes of all messages, including the first.")
    else:
        parts.append(f"A {FILE_KINDS[spec.file_type]} was expected. You grade the file the user got in the end.")
    checklist = spec.judge.checklist
    parts.append("## Checklist (what a 5 looks like)\n\n" + ("\n".join(f"- {p}" for p in checklist) if checklist
                                                              else "(No checklist; keep to the task.)"))
    crit = ["## Criteria (whole grades 1–5, 5 = very good)"]
    for c in CRITERIA:
        crit.append(f"**{c['name']}** (`{c['id']}`): {c['question']}\n- 5: {c['grade_5']}\n- 3: {c['grade_3']}\n"
                    f"- 1: {c['grade_1']}")
    parts.append("\n\n".join(crit))
    return "\n\n".join(parts)


def answer_format() -> str:
    example = {c: {"grade": 4, "reason": "one or two sentences with the main evidence"} for c in CRITERIA_IDS}
    return ("## Your answer\n\nThink it through, then end your answer with exactly one JSON object in this form "
            "(grades as whole numbers 1–5):\n\n```json\n" + json.dumps(example, indent=1) + "\n```")


def build_messages(item: Item, rendered: str, images: list[Path]) -> list[dict]:
    if item.file is None:
        material = ("## The model's final answer\n\n" + _fence(item.answer) if item.answer else
                    "## The model's final answer\n\n**No final answer.** The conversation ended with a tool call, an "
                    "error or without text; the user got no answer.")
    else:
        note = ("The file as text (Markdown, read from the file; Excel with row and column headers, formulas and "
                "recalculated results)" + (f" and images of its rendered pages (at most {MAX_IMAGES}; the text is "
                                           "complete and decides)" if images else "") + ".")
        material = f"## The file: {item.file.name.split('__', 2)[-1]}\n\n{note}\n\n{_fence(rendered)}"
    text = "\n\n".join([task_text(item.task, item.today), material, answer_format()])
    content: list[dict] = [{"type": "text", "text": text}]
    for img in images[:MAX_IMAGES]:
        data = base64.b64encode(img.read_bytes()).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}})
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]


def parse_grades(text: str) -> dict | None:
    """The last JSON object in the answer with all five criteria as whole numbers 1–5."""
    for m in reversed(list(re.finditer(r"\{", text))):
        try:
            obj, _ = json.JSONDecoder().raw_decode(text[m.start():])
        except ValueError:
            continue
        if not isinstance(obj, dict) or not set(CRITERIA_IDS) <= set(obj):
            continue
        grades, reasons = {}, {}
        for c in CRITERIA_IDS:
            v = obj[c]
            g = v.get("grade") if isinstance(v, dict) else v
            if not isinstance(g, int) or isinstance(g, bool) or not 1 <= g <= 5:
                return None
            grades[c] = g
            reasons[c] = v.get("reason", "") if isinstance(v, dict) else ""
        return {"grades": grades, "reasons": reasons}
    return None


def select_items(folders: list[Path], samples: int, tasks: dict[str, Task] | None = None) -> list[Item]:
    """Per model folder and task: the first `samples` runs not ended by an outage that delivered a file; for tasks
    without a file the first such runs, with or without a final answer."""
    tasks = tasks or load_tasks()
    items = []
    for folder in folders:
        meta = read_meta(folder)
        model, today = meta["model"]["name"], str(meta["profile"]["today"])
        logs = read_log(folder / "log.jsonl")
        files = delivered_files(folder)
        for task_id in meta["tasks"]:
            task = tasks.get(task_id)
            if task is None:
                continue
            found = []
            for (tid, rep), rec in sorted(logs.items()):
                if tid != task_id or rec.get("error_kind") in OUTAGE:
                    continue
                if task.expects_file and (tid, rep) in files:
                    found.append(Item(model, task, rep, files[(tid, rep)], today=today))
                elif not task.expects_file:
                    found.append(Item(model, task, rep, None, rec.get("final_answer"), today=today))
            items += found[:samples]
    return items


def _graded(out: Path, judge_name: str) -> set[tuple]:
    """(model, task, rep) already in the grades file for this judge: a rerun resumes."""
    return {(r["model"], r["task"], r["rep"]) for r in (read_jsonl(out) if out.exists() else [])
            if r.get("judge") == judge_name}


def _graded_fields(parsed: dict) -> dict:
    g = parsed["grades"]
    return {"grades": g, "mean": round(sum(g.values()) / len(g), 3), "reasons": parsed["reasons"]}


def _render(items: list[Item], tmp: Path) -> list[tuple[Path | None, str, list[Path]]]:
    """Per item (neutral copy, text, page images); (None, "", []) for a final answer. The files are copied under
    neutral names first, then rendered together (one LibreOffice run for the images, one to recalculate the xlsx)."""
    copies = {}
    for n, item in enumerate(items):
        if item.file is not None:
            copies[n] = tmp / f"f{n:05d}{item.file.suffix}"
            neutral_copy(item.file, copies[n])
    images = render_images(list(copies.values()), tmp / "images") if copies else {}
    texts = render_texts(list(copies.values())) if copies else {}
    return [(c, texts.get(c, ""), images.get(c, [])) if (c := copies.get(n)) else (None, "", [])
            for n in range(len(items))]


async def judge_items(items: list[Item], judge: ModelConfig, out: Path, progress=print) -> None:
    done = _graded(out, judge.name)
    todo = [i for i in items if i.key not in done]
    progress(f"judge {judge.name}: {len(todo)} items to grade ({len(items) - len(todo)} already graded)")
    if not todo:
        return
    api_key = judge.api_key()
    with tempfile.TemporaryDirectory(prefix="obench-judge-") as tmp:
        rendered = _render(todo, Path(tmp))
        sem, lock = asyncio.Semaphore(judge.concurrency), asyncio.Lock()
        counter = {"n": 0}

        async def one(http, item, text, images):
            async with sem:
                body = {"model": judge.model, "messages": build_messages(item, text, images), **judge.params}
                c = await complete(http, judge.base_url, api_key, body, on_retry=lambda m: progress(f"  {m}"))
                parsed = parse_grades(c.content) if not c.error else None
                rec = {"model": item.model, "task": item.task.id, "rep": item.rep,
                       "file": item.file.name if item.file else None, "judge": judge.name,
                       "usage": c.usage, "cost": c.cost}
                if parsed:
                    rec.update(_graded_fields(parsed))
                else:
                    rec.update(error=c.error or "no valid grades in the answer", answer=c.content[-2000:])
                async with lock:
                    if parsed:  # failed items are not written, so the next run retries them
                        with out.open("a", encoding="utf-8") as f:
                            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    counter["n"] += 1
                    progress(f"  [{counter['n']}/{len(todo)}] {item.model} {item.task.id}-{item.rep}: "
                             + (f"{rec['mean']:.2f}" if parsed else f"FAILED ({rec['error'][:100]})"))

        timeout = httpx.Timeout(connect=30, read=900, write=60, pool=None)
        async with httpx.AsyncClient(timeout=timeout) as http:
            await asyncio.gather(*(one(http, item, text, images)
                                   for item, (_, text, images) in zip(todo, rendered, strict=True)))


# ------------------------------------------------------------------------------- grading by agent sessions --
# The same prompt can be graded by coding agents instead of an API call (e.g. Claude Code subagents, which can also
# check calculations with small scripts). export_items writes one folder per item under neutral ids, the mapping to
# models apart; import_grades reads the agents' grade.json files back into the grades format.

AGENT_INSTRUCTIONS = """# Grading package {package}

You are a reviewer in a blind review. Grade each item below on its own. For each item id:

1. Read `material/<id>/prompt.md` completely: it holds your instructions, the task, the checklist, the criteria and
   the file as text. Look at the page images in `material/<id>/` (`page-*.png`) if there are any; the delivered file
   itself is there too (`file.*`) if you want to inspect it.
2. Check calculations, dates and weekdays yourself; small Python scripts are welcome — save them in
   `material/<id>/checks/` so the grading can be traced.
3. Write `material/<id>/grade.json`: exactly the JSON object asked for at the end of prompt.md.

Do not open `mapping.json` or other packages, and do not guess which model made a file.

Items: {items}
"""


def export_items(items: list[Item], out: Path, package_size: int = 8, seed: int = 20261019) -> dict:
    """Write material/<id>/ (prompt.md, page images, neutral file copy), packages/<p>.md and mapping.json."""
    rng = random.Random(seed)
    order = list(items)
    rng.shuffle(order)
    out.mkdir(parents=True, exist_ok=True)
    mapping, by_task = {}, {}
    with tempfile.TemporaryDirectory(prefix="obench-export-") as tmp:
        for n, (item, (copy, text, images)) in enumerate(zip(order, _render(order, Path(tmp)), strict=True)):
            item_id = f"J{n + 1:04d}"
            folder = out / "material" / item_id
            folder.mkdir(parents=True, exist_ok=True)
            pngs = images[:MAX_IMAGES]
            messages = build_messages(item, text, [])
            note = f"\n\nPage images: {', '.join(f'page-{i}.png' for i in range(1, len(pngs) + 1))}" if pngs else ""
            (folder / "prompt.md").write_text(f"# Instructions\n\n{messages[0]['content']}\n\n"
                                              f"{messages[1]['content'][0]['text']}{note}\n", encoding="utf-8")
            for i, png in enumerate(pngs, 1):
                shutil.copyfile(png, folder / f"page-{i}.png")
            if copy:
                shutil.copyfile(copy, folder / f"file{copy.suffix}")
            mapping[item_id] = {"model": item.model, "task": item.task.id, "rep": item.rep,
                                "file": item.file.name if item.file else None}
            by_task.setdefault(item.task.id, []).append(item_id)
    packages, current = [], []
    for task_id in sorted(by_task):  # packages of one task where possible: the reviewer reads the task once
        for item_id in by_task[task_id]:
            current.append(item_id)
            if len(current) == package_size:
                packages.append(current)
                current = []
    if current:
        packages.append(current)
    (out / "packages").mkdir(exist_ok=True)
    for p, ids in enumerate(packages, 1):
        (out / "packages" / f"P{p:03d}.md").write_text(
            AGENT_INSTRUCTIONS.format(package=f"P{p:03d}", items=", ".join(ids)), encoding="utf-8")
    (out / "mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"items": len(mapping), "packages": len(packages)}


def import_grades(folder: Path, out: Path, judge_name: str) -> dict:
    """Append the agents' grades (material/<id>/grade.json) to out; returns counts of imported and missing items."""
    mapping = json.loads((folder / "mapping.json").read_text(encoding="utf-8"))
    done = _graded(out, judge_name)
    imported, missing, invalid = 0, [], []
    with out.open("a", encoding="utf-8") as f:
        for item_id, m in sorted(mapping.items()):
            if (m["model"], m["task"], m["rep"]) in done:
                continue
            path = folder / "material" / item_id / "grade.json"
            if not path.exists():
                missing.append(item_id)
                continue
            parsed = parse_grades(path.read_text(encoding="utf-8"))
            if not parsed:
                invalid.append(item_id)
                continue
            f.write(json.dumps({**m, "judge": judge_name, **_graded_fields(parsed), "item": item_id},
                               ensure_ascii=False) + "\n")
            imported += 1
    return {"imported": imported, "missing": missing, "invalid": invalid}
