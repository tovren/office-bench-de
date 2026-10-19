"""Shared helpers of the content-check tests: tasks with given [checks], filtering defects, building files with the
real office tool. Imported by the test modules in tests/ (pytest puts this folder on sys.path)."""

import json
from pathlib import Path

from officebench.tasks import Task, TaskSpec
from officebench.tool import build

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CONTENT = FIXTURES / "content"


def make_task(file_type: str | None = "docx", dates_from: str | None = None, turns: tuple = (), **checks) -> Task:
    """A task with these [checks] (validated like a task file); `turns` are the loaded turns the checks read."""
    spec = TaskSpec.model_validate({"id": "test", "title": "Test", "version": 1,
                                    "kind": "file" if file_type else "no_file", "file_type": file_type,
                                    "dates_from": dates_from, "turns": [{"text": "Test"}], "checks": checks})
    return Task(spec=spec, turns=turns, path=Path("test"), hash="test")


def only(defects, check: str, severity: str | None = None) -> list:
    """The defects of one check (optionally of one severity)."""
    return [m for m in defects if m.check == check and (severity is None or m.severity == severity)]


def build_call(call: dict, target: Path) -> tuple:
    """Run {"function", "arguments"} with the real tool; the last built file goes to `target` + its suffix.
    Returns (CallResult, path or None)."""
    result = build(call["function"], call["arguments"])
    if not result.files:
        return result, None
    built = result.files[-1]
    path = target.with_name(target.name + Path(built.name).suffix)
    path.write_bytes(built.data)
    return result, path


def build_fixture(name: str, folder: Path) -> Path:
    """Build tests/fixtures/content/<name>.json with the real tool; returns the file <folder>/<name>.<suffix>."""
    call = json.loads((CONTENT / f"{name}.json").read_text(encoding="utf-8"))
    result, path = build_call(call, folder / name)
    assert path is not None, result.content[:1000]
    return path
