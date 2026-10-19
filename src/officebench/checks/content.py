"""Content check: objective checks of the docx/xlsx/pptx files the office tool built.

    obench check FILE_OR_FOLDER... [--task ID] [--only-defects] [--today YYYY-MM-DD] [--previous PATH]

As a module:
    check_file(path, task, today=None, previous=None) -> list of Defect (short English sentences with .label,
        .severity, .check)
    check_files([(path, task) or (path, task, previous), ...], today=None) -> {path: Findings} (one LibreOffice run
        for all xlsx; previous = file of the previous turn for `retained`)
    missing_topics(text, topics) -> names of the missing topics of a `topics` block
    forbidden_found(text, forbidden) -> names of the entries of a `forbidden` block that occur

All task-specific checks come from [checks] of the task (docs/task-format.md); the general checks (GENERAL_CHECKS)
always run and can be switched off per task with `disable`. Every defect is hard (task not done or certainly wrong)
or soft (quality issue, uncertain heuristic); Findings.ok = no hard defects, Findings.clean = none at all. Without a
task only the general checks run; the task is otherwise taken from the file name ("budget-3__…"). xlsx files are
recalculated with headless LibreOffice (xlsx -> xlsx in a temp folder, then openpyxl data_only=True).
"""

import argparse
import re
import sys
import tempfile
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from officebench.tasks import Task, load_tasks

from .arithmetic import check_text_arithmetic
from .core import REFERENCE_DATE, Context, Defect, Findings
from .dates import check_dates
from .docx import check_docx
from .pptx import check_pptx
from .registry import GENERAL_CHECKS, HARD, SOFT
from .retained import check_retained
from .sources import check_numbers_sourced
from .text import (
    check_forbidden,
    check_tables_general,
    check_text_general,
    check_text_task,
    check_values,
    forbidden_found,
    missing_topics,
)
from .xlsx import SOFFICE, check_xlsx, recalculate

CHECKERS = {".xlsx": "xlsx", ".docx": "docx", ".pptx": "pptx"}
UNSOURCED = "unsourced_numbers"  # metric of check_numbers_sourced
__all__ = ["GENERAL_CHECKS", "REFERENCE_DATE", "HARD", "SOFT", "Defect", "Findings", "missing_topics",
           "forbidden_found", "check_file", "check_files", "task_from_path", "recalculate", "main"]


def task_from_path(path) -> str | None:
    """Task id from a file name of the harness ('budget-3__…', also ids with underscores)."""
    m = re.match(r"^([a-z][a-z0-9_]*)-\d+__", Path(path).name)
    return m.group(1) if m and m.group(1) in load_tasks() else None


def _date(today) -> date:
    if today is None or today == "":
        return REFERENCE_DATE
    if isinstance(today, datetime):
        return today.date()
    if isinstance(today, date):
        return today
    return date.fromisoformat(str(today)[:10])


def _task(t, path: Path) -> Task | None:
    """Task for an id, a Task, or None (then from the path)."""
    if t is not None and not isinstance(t, str):
        return t
    task_id = t or task_from_path(path)
    if task_id is None:
        return None
    tasks = load_tasks()
    if task_id not in tasks:
        raise ValueError(f"unknown task {task_id!r}; known: {', '.join(tasks)}")
    return tasks[task_id]


def check_one(path: Path, ctx: Context, recalculated: dict) -> Findings:
    suffix = path.suffix.lower()
    kind = CHECKERS.get(suffix)
    if kind is None:
        ctx.report("unknown_file_type", f"unknown file type {path.suffix}")
        return Findings(ctx.defects, {})
    try:  # opening and reading the file; the checks inside are guarded one by one (soft "check crashed")
        if kind == "xlsx":
            metrics, doc = check_xlsx(path, ctx, recalculated)
        elif kind == "docx":
            metrics, doc = check_docx(path, ctx)
        else:
            metrics, doc = check_pptx(path, ctx)
    except Exception as e:
        ctx.defects.clear()
        ctx.report("unreadable", f"file not readable: {type(e).__name__}: {str(e)[:120]}")
        metrics, doc = {}, None
    if doc is not None:
        text_metrics = {}
        with ctx.guarded("text"):
            check_text_general(doc, ctx)
        with ctx.guarded("empty_table"):
            check_tables_general(doc, ctx)
        with ctx.guarded("topics"):
            text_metrics = check_text_task(doc, ctx)
        if "forbidden" in ctx.checks:
            with ctx.guarded("forbidden"):
                check_forbidden(doc, ctx)
        if "values_present" in ctx.checks:
            with ctx.guarded("values_present"):
                check_values(doc, ctx)
        if ctx.checks.get("numbers_sourced"):
            with ctx.guarded("numbers_sourced"):
                text_metrics.update(check_numbers_sourced(doc, ctx))
        with ctx.guarded("dates"):
            check_dates(doc, ctx)
        with ctx.guarded("text_arithmetic"):
            check_text_arithmetic(doc, ctx)
        if kind == "docx":
            metrics = {**text_metrics, **metrics}
        elif kind == "pptx":
            metrics.update(text_metrics)
        elif UNSOURCED in text_metrics:
            metrics[UNSOURCED] = text_metrics[UNSOURCED]
        if "retained" in ctx.checks:
            with ctx.guarded("retained"):
                metrics.update(check_retained(path, doc if kind != "xlsx" else None, ctx))
    task = ctx.task
    if task is not None and task.spec.file_type and suffix != f".{task.spec.file_type}":
        ctx.report("wrong_file_type", f"wrong file type {path.suffix} (expected .{task.spec.file_type})")
        ctx.defects.insert(0, ctx.defects.pop())
    return Findings(ctx.defects, metrics)


def check_files(entries, today=None, soffice: str = SOFFICE) -> dict:
    """[(path, task id / Task / None[, previous file])] -> {path: Findings}; one LibreOffice run recalculates all xlsx
    (the previous file of a follow-up task needs none: `retained` reads its stored values).

    today: reference date (date or 'YYYY-MM-DD'; default 2026-10-13) for dates without a year and the calendar.
    """
    day = _date(today)
    entries = [(Path(e[0]), e[1], Path(e[2]) if len(e) > 2 and e[2] else None) for e in entries]
    found = {}
    with tempfile.TemporaryDirectory(prefix="obench-check-") as tmp:
        recalculated = recalculate([p for p, *_ in entries if p.suffix.lower() == ".xlsx"], Path(tmp), soffice)
        for p, t, previous in entries:
            ctx = Context(_task(t, p), day, previous=previous)
            found[p] = check_one(p, ctx, recalculated)
    return found


def check_file(path, task=None, today=None, previous=None) -> list:
    """Defects of one file (Defect with .label, .severity, .check)."""
    return check_files([(path, task, previous)], today=today)[Path(path)].defects


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="obench check", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="files or folders (recursive *.docx/*.xlsx/*.pptx)")
    ap.add_argument("--task", help="task for all files (otherwise from the file name)")
    ap.add_argument("--only-defects", action="store_true", help="do not list files without defects")
    ap.add_argument("--today", help="reference date YYYY-MM-DD (default 2026-10-13)")
    ap.add_argument("--previous", type=Path, help="file of the previous turn (follow-up task) for `retained`")
    a = ap.parse_args(argv)
    files = []
    for p in map(Path, a.paths):
        if p.is_dir():
            files += sorted(q for q in p.rglob("*") if q.suffix.lower() in CHECKERS and not q.name.startswith("~$"))
        else:
            files.append(p)
    found = check_files([(p, a.task, a.previous) for p in files], today=a.today)
    labels = Counter()
    for p, f in found.items():
        labels.update(d.label for d in f.defects)
        if f.clean and a.only_defects:
            continue
        metrics = ", ".join(f"{k} {v}" for k, v in f.metrics.items())
        print(f"{p} [{a.task or task_from_path(p) or '-'}]: {'ok' if f.ok else 'NOT ok'}, "
              f"{len(f.hard)} hard, {len(f.soft)} soft | {metrics}")
        for d in f.defects:
            print(f"    - [{d.severity}] {d}")
    ok = sum(1 for f in found.values() if f.ok)
    clean = sum(1 for f in found.values() if f.clean)
    print(f"\n{len(found)} files, {ok} ok (no hard defects), {clean} without any defect. Most common defects: "
          + (", ".join(f"{k} ({v})" for k, v in labels.most_common(8)) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
