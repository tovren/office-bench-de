"""Reference solutions (tasks/<id>/reference.json): the tool accepts them, and the content check finds no hard
defects in the files built from them. A hard defect here is a false alarm of a check, or a mistake in the reference.

Format: {"function": "create_excel_file", "arguments": {...}}, a solution as a very good model would send it; for
follow-up tasks the arguments of the last call, whose file the checks apply to, and "previous": {"function",
"arguments"}, the file of the previous turn; it is built too and the last file is checked against it (`retained`).
"""

import json
from pathlib import Path

import pytest

from officebench.checks.content import check_files, task_from_path
from officebench.checks.retained import compare, texts
from officebench.tasks import load_tasks
from officebench.tool import FILE_TYPES, build

TASKS = load_tasks()
IDS = sorted(i for i, t in TASKS.items() if t.reference_path.exists())
# File tasks from before the reference solutions; every newer file task needs one. Remove an id once its reference
# exists (test_file_tasks_have_a_reference fails until then).
WITHOUT_REFERENCE = {"angebot", "anweisung", "budget", "konzept", "praesentation", "protokoll", "quartal",
                     "reisekosten", "rundschreiben", "vergleich"}


def load(task_id: str) -> dict:
    return json.loads(TASKS[task_id].reference_path.read_text(encoding="utf-8"))


def test_file_tasks_have_a_reference():
    file_tasks = {i for i, t in TASKS.items() if t.expects_file}
    missing = sorted(file_tasks - WITHOUT_REFERENCE - set(IDS))
    assert not missing, f"reference.json missing for: {missing}"
    stale = sorted(WITHOUT_REFERENCE & (set(IDS) | (set(TASKS) - file_tasks)))
    assert not stale, f"remove from WITHOUT_REFERENCE (has a reference or is no file task): {stale}"


@pytest.mark.parametrize("task_id", IDS)
def test_reference_fits_the_task(task_id):
    task, ref = TASKS[task_id], load(task_id)
    assert {"function", "arguments"} <= set(ref) <= {"function", "arguments", "previous"}
    assert task.expects_file, f"{task_id} expects no file"
    assert FILE_TYPES[ref["function"]] == task.spec.file_type
    if "previous" in ref:
        assert task.spec.kind == "follow_up" and set(ref["previous"]) == {"function", "arguments"}


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> dict:
    """id -> (CallResult, path of the built file or None, path of the previous file or None); file names like in a
    run: <id>-0__r2c0__<name>, the previous file <id>-0__r0c0__<name>."""
    folder = tmp_path_factory.mktemp("references")

    def build_file(task_id: str, call: dict, round_: int):
        result = build(call["function"], call["arguments"])
        path = None
        if result.files:
            f = result.files[-1]
            path = folder / f"{task_id}-0__r{round_}c0__{f.name}"
            path.write_bytes(f.data)
        return result, path

    out = {}
    for task_id in IDS:
        ref = load(task_id)
        previous = build_file(task_id, ref["previous"], 0)[1] if "previous" in ref else None
        out[task_id] = (*build_file(task_id, ref, 2), previous)
    return out


@pytest.mark.parametrize("task_id", IDS)
def test_tool_accepts_reference(task_id, built):
    result, path, previous = built[task_id]
    assert result.done, result.content[:2000]
    assert path is not None, "the tool delivered no file"
    assert previous is not None or "previous" not in load(task_id), "no file for previous"
    assert path.suffix == f".{TASKS[task_id].spec.file_type}"
    assert task_from_path(path) == task_id  # the content check finds the task like for the files of a run


@pytest.fixture(scope="module")
def findings(built) -> dict:
    """id -> Findings; one content-check run (one LibreOffice call) for all reference files. The task comes from the
    file name, like for the files of a run."""
    paths = {path: (task_id, previous) for task_id, (_, path, previous) in built.items() if path is not None}
    result = check_files([(path, None, previous) for path, (_, previous) in paths.items()])
    return {paths[Path(p)][0]: f for p, f in result.items()}


@pytest.mark.slow
@pytest.mark.parametrize("task_id", IDS)
def test_content_check_without_hard_defects(task_id, findings):
    f = findings[task_id]
    lines = [f"[{m.severity}] {m.check}: {m}" for m in f.defects]
    assert f.ok, "hard defects in the reference solution (false alarm of a check?):\n" + "\n".join(lines)


@pytest.mark.parametrize("task_id", [i for i in IDS if "previous" in load(i)])
def test_follow_up_retains_previous_file(task_id, built):
    """The reference of a follow-up task keeps enough of the previous file to pass the task's `retained` without even
    a soft defect (0.9 if the task sets none; a follow-up that changes date and agenda keeps less than one that only
    adds a section)."""
    levels = TASKS[task_id].spec.checks.given().get("retained", 0.9)
    threshold = max(levels.values()) if isinstance(levels, dict) else levels
    _, path, previous = built[task_id]
    share, lost, _ = compare(texts(previous), texts(path))
    assert share >= threshold, lost
