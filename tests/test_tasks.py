import json
import tomllib
from pathlib import Path

import pytest

from officebench import tasks as reg
from officebench.checks.registry import GENERAL_CHECKS, TASK_CHECKS
from officebench.tasks import TaskError, load_task, load_tasks, select

MINIMAL = """
id = "{id}"
title = "Test"
version = 1
kind = "file"
file_type = "xlsx"

[[turns]]
text = "Mach mir eine Tabelle."
"""


def write_task(tmp_path: Path, body: str, task_id: str = "probe") -> Path:
    folder = tmp_path / task_id
    folder.mkdir()
    (folder / "task.toml").write_text(MINIMAL.format(id=task_id) + body, encoding="utf-8")
    return folder


def test_all_tasks_load():
    tasks = load_tasks()
    assert len(tasks) == 50
    assert all(t.turns for t in tasks.values())


def test_minimal_task(tmp_path):
    t = load_task(write_task(tmp_path, ""))
    assert t.turns[0].expect == "file"
    assert t.expects_file


@pytest.mark.parametrize("body, message", [
    ("\n[checks]\ntopic = { a = 'x' }\n", "topic"),                         # typo in a check key
    ("\n[checks]\ntopics = { a = '(' }\n", "invalid regex"),
    ("\n[checks]\ntoc = true\n", "not available for xlsx"),                # docx-only check on xlsx
    ("\n[checks]\nmonths = [7, 3]\n", "from ≤ to"),
    ("\n[checks]\nretained = { hard = 0.9, soft = 0.5 }\n", "hard must be ≤ soft"),
    ("\n[checks]\ndisable = ['nope']\n", "unknown general check"),
    ("\n[checks]\nchart_type = 'donut'\n", "unknown chart type"),
    ("\n[[checks.calculations]]\nname = 'x'\ncolumns = { a = 'a' }\nformula = 'a * b'\nresult = 'a'\n",
     "unknown name 'b'"),
    ("\n[[checks.calculations]]\nname = 'x'\ncolumns = { a = 'a' }\nformula = '__import__(1)'\nresult = 'a'\n",
     "may only use"),
    ("\n[behavior]\ntools_expected = ['send_email']\n", "not one of the task's extra_tools"),
    ("\nsurprise = 1\n", "surprise"),
])
def test_invalid_tasks_are_rejected(tmp_path, body, message):
    with pytest.raises(TaskError, match=message):
        load_task(write_task(tmp_path, body))


def test_id_must_match_folder(tmp_path):
    folder = write_task(tmp_path, "")
    folder.rename(tmp_path / "other")
    with pytest.raises(TaskError, match="folder name"):
        load_task(tmp_path / "other")


def test_missing_attachment(tmp_path):
    body = MINIMAL.format(id="probe").replace(
        'text = "Mach mir eine Tabelle."',
        'text = "Mach mir eine Tabelle."\nattachments = [{ name = "a.pdf", file = "a.txt" }]')
    folder = tmp_path / "probe"
    folder.mkdir()
    (folder / "task.toml").write_text(body, encoding="utf-8")
    with pytest.raises(TaskError, match="missing"):
        load_task(folder)


def test_hash_covers_attachments(tmp_path):
    body = MINIMAL.format(id="probe").replace(
        'text = "Mach mir eine Tabelle."',
        'text = "Mach mir eine Tabelle."\nattachments = [{ name = "a.pdf", file = "a.txt" }]')
    folder = tmp_path / "probe"
    (folder / "attachments").mkdir(parents=True)
    (folder / "task.toml").write_text(body, encoding="utf-8")
    (folder / "attachments" / "a.txt").write_text("eins", encoding="utf-8")
    first = load_task(folder).hash
    (folder / "attachments" / "a.txt").write_text("zwei", encoding="utf-8")
    assert load_task(folder).hash != first


def test_select():
    assert [t.id for t in select("budget,sparquote")] == ["budget", "sparquote"]
    assert all(t.spec.file_type == "pptx" for t in select("type:pptx"))
    assert all(t.spec.kind == "no_file" for t in select("kind:no_file"))
    with pytest.raises(TaskError):
        select("does_not_exist")


def test_extra_tools_exist_and_are_used():
    used = {n for t in load_tasks().values() for n in t.spec.extra_tools}
    files = {p.stem for p in reg.EXTRA_TOOLS_DIR.glob("*.json")}
    assert used == files
    for name in files:
        tool = reg.extra_tool(name)
        assert set(tool) == {"spec", "result"}
        assert tool["spec"]["function"]["name"] == name


MUTANT_KEYS = {"name", "defect", "set", "replace", "number", "remove", "expected", "severity", "gap",
               "prevented"}


def test_mutant_files_are_well_formed():
    known = set(TASK_CHECKS) | set(GENERAL_CHECKS) | {"unreadable", "wrong_file_type"}
    for t in load_tasks().values():
        if not t.mutants_path.exists():
            continue
        assert t.reference_path.exists(), t.id
        mutants = tomllib.loads(t.mutants_path.read_text(encoding="utf-8"))["mutant"]
        names = [m["name"] for m in mutants]
        assert len(names) == len(set(names)), t.id
        for m in mutants:
            assert set(m) <= MUTANT_KEYS and {"name", "defect", "expected"} <= set(m), (t.id, m["name"])
            assert set(m["expected"]) <= known, (t.id, m["name"])


def test_references_are_tool_calls():
    for t in load_tasks().values():
        if t.reference_path.exists():
            ref = json.loads(t.reference_path.read_text(encoding="utf-8"))
            assert ref["function"] == {"docx": "create_word_file", "xlsx": "create_excel_file",
                                       "pptx": "create_powerpoint_file"}[t.spec.file_type], t.id
