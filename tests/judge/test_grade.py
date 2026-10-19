import json

import pytest

from officebench import tool
from officebench.judge import grade
from officebench.tasks import load_tasks


def make_run(tmp_path, model="m1"):
    """A model folder with one file task (two runs, one with an outage) and one task without a file."""
    folder = tmp_path / model
    (folder / "files").mkdir(parents=True)
    meta = {"model": {"name": model}, "profile": {"today": "2026-10-13"}, "tasks": ["versammlung", "wartungsmail"]}
    (folder / "meta.json").write_text(json.dumps(meta))
    ref = json.loads(load_tasks()["versammlung"].reference_path.read_text(encoding="utf-8"))
    data = tool.build(ref["function"], ref["arguments"]).files[0].data
    (folder / "files" / "versammlung-0__r0c0__Einladung.docx").write_bytes(b"old")
    (folder / "files" / "versammlung-0__r1c0__Einladung.docx").write_bytes(data)
    logs = [{"task": "versammlung", "rep": 0, "outcome": "answer"},
            {"task": "versammlung", "rep": 1, "outcome": "error", "error_kind": "provider"},
            {"task": "wartungsmail", "rep": 0, "outcome": "answer", "final_answer": "Sehr geehrte …"},
            {"task": "wartungsmail", "rep": 1, "outcome": "round_limit", "final_answer": None}]
    (folder / "log.jsonl").write_text("".join(json.dumps(r) + "\n" for r in logs))
    return folder


def test_select_items(tmp_path):
    items = grade.select_items([make_run(tmp_path)], samples=2)
    keys = [(i.task.id, i.rep, i.file.name if i.file else None, i.answer) for i in items]
    assert keys == [("versammlung", 0, "versammlung-0__r1c0__Einladung.docx", None),  # the last built file
                    ("wartungsmail", 0, None, "Sehr geehrte …"), ("wartungsmail", 1, None, None)]


def test_prompt_is_blind_and_complete(tmp_path):
    item = grade.select_items([make_run(tmp_path, "secret-model")], samples=1)[0]
    messages = grade.build_messages(item, "TEXT DER DATEI", [])
    text = messages[1]["content"][0]["text"]
    assert "secret-model" not in text and "TEXT DER DATEI" in text
    assert load_tasks()["versammlung"].turns[0].text.splitlines()[0] in text
    assert "Tuesday, 13.10.2026" in text and all(f"`{c}`" in text for c in grade.CRITERIA_IDS)
    no_answer = grade.build_messages(grade.Item("m", load_tasks()["wartungsmail"], 1, None, None), "", [])
    assert "No final answer" in no_answer[1]["content"][0]["text"]


@pytest.mark.parametrize("answer, ok", [
    ('Gut.\n```json\n{"language": {"grade": 5, "reason": "a"}, "content": {"grade": 4, "reason": "b"}, '
     '"completeness": {"grade": 5}, "structure": {"grade": 3}, "usefulness": {"grade": 4}}\n```', True),
    ('{"language": 5, "content": 4, "completeness": 5, "structure": 3, "usefulness": 4}', True),
    ('{"language": 6, "content": 4, "completeness": 5, "structure": 3, "usefulness": 4}', False),
    ('{"language": 5, "content": 4}', False),
    ("no json", False),
])
def test_parse_grades(answer, ok):
    parsed = grade.parse_grades(answer)
    assert (parsed is not None) is ok
    if ok:
        assert parsed["grades"] == {"language": 5, "content": 4, "completeness": 5, "structure": 3, "usefulness": 4}


@pytest.mark.slow
def test_export_and_import(tmp_path):
    items = grade.select_items([make_run(tmp_path)], samples=2)
    out = tmp_path / "export"
    assert grade.export_items(items, out, package_size=2) == {"items": 3, "packages": 2}
    mapping = json.loads((out / "mapping.json").read_text())
    docx_id = next(i for i, m in mapping.items() if m["task"] == "versammlung")
    material = out / "material" / docx_id
    prompt = (material / "prompt.md").read_text()
    assert "# Instructions" in prompt and "m1" not in prompt and (material / "file.docx").exists()
    assert list(material.glob("page-*.png"))
    packages = sorted((out / "packages").glob("P*.md"))
    assert all("grade.json" in p.read_text() for p in packages)
    (material / "grade.json").write_text(json.dumps({c: {"grade": 4, "reason": "ok"} for c in grade.CRITERIA_IDS}))
    grades = tmp_path / "grades.jsonl"
    r = grade.import_grades(out, grades, "agent-test")
    assert r["imported"] == 1 and len(r["missing"]) == 2 and not r["invalid"]
    rec = json.loads(grades.read_text())
    assert rec["model"] == "m1" and rec["task"] == "versammlung" and rec["mean"] == 4.0
    assert grade.import_grades(out, grades, "agent-test")["imported"] == 0  # already imported
