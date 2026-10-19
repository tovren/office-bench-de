"""Task schema and loader.

Every task is a folder ``tasks/<id>/`` with ``task.toml`` (format: docs/task-format.md), optional ``attachments/``
with the extracted text of uploaded files, and for file tasks a ``reference.json`` (tool arguments of a correct
solution) and ``mutants.toml`` (broken variants of it that the checks must catch).

Prompts, attachments and judge checklists are German; keys and code are English. Unknown keys are an error, so a
typo cannot silently switch a check off.

    from officebench.tasks import load_tasks, select
    tasks = load_tasks()                      # {id: Task}, sorted by id
    for t in select("budget,sparquote"): ...  # ids, tags ("tag:chart") or "all"
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import tomllib
from datetime import date
from functools import cache
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

from officebench.checks.registry import CHART_TYPES, GENERAL_CHECKS, task_checks_for

ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = ROOT / "tasks"
EXTRA_TOOLS_DIR = ROOT / "extra_tools"
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
TAG_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

FileType = Literal["docx", "xlsx", "pptx"]
Kind = Literal["file", "follow_up", "no_file"]
Expect = Literal["file", "no_file", "any"]
NonNegInt = Annotated[StrictInt, Field(ge=0)]
Number = int | float


class TaskError(ValueError):
    pass


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _regex(value: str) -> str:
    try:
        re.compile(value)
    except re.error as e:
        raise ValueError(f"invalid regex {value!r}: {e}") from e
    return value


Regex = Annotated[str, Field(min_length=1)]


class PatternMin(_Model):
    """An alternative that has to match at least ``min`` times."""

    pattern: Regex
    min: Annotated[StrictInt, Field(ge=1)] = 1

    _check = field_validator("pattern")(_regex)


# A topic: one regex or a list of alternatives (regex or {pattern, min}). Case-insensitive, hyphen variants ignored.
TopicPattern = Regex | list[Regex | PatternMin]
Topics = dict[str, TopicPattern]


def _check_topics(topics: Topics | None) -> Topics | None:
    for value in (topics or {}).values():
        for alt in value if isinstance(value, list) else [value]:
            if isinstance(alt, str):
                _regex(alt)
    return topics


class HardSoft(_Model):
    """Two thresholds: below ``hard`` is a hard defect, below ``soft`` a soft one."""

    hard: Number | None = None
    soft: Number | None = None

    @model_validator(mode="after")
    def _order(self):
        if self.hard is None and self.soft is None:
            raise ValueError("needs hard and/or soft")
        if self.hard is not None and self.soft is not None and self.hard > self.soft:
            raise ValueError("hard must be ≤ soft")
        return self


class Count(_Model):
    name: str
    pattern: Regex
    min: NonNegInt | None = None
    max: NonNegInt | None = None

    _check = field_validator("pattern")(_regex)


def _check_sheet(value):
    if isinstance(value, str):
        _regex(value)
    return value


Sheet = Annotated[StrictInt, Field(ge=1)] | Regex  # position from 1 or a regex on the sheet name


class Calculation(_Model):
    """Recalculate a column row by row: ``result`` = ``formula`` over the named columns."""

    name: str
    columns: dict[str, Regex]
    formula: str
    result: str
    tolerance: Annotated[Number, Field(ge=0)] = 0.01
    sheet: Sheet | None = None

    _sheet = field_validator("sheet")(_check_sheet)

    @field_validator("columns")
    @classmethod
    def _columns(cls, v):
        for name, pattern in v.items():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                raise ValueError(f"{name!r} is not a valid name")
            _regex(pattern)
        return v

    @model_validator(mode="after")
    def _formula(self):
        if self.result not in self.columns:
            raise ValueError(f"result {self.result!r} is not in columns")
        try:
            tree = ast.parse(self.formula, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"formula {self.formula!r} is not a valid expression ({e.msg})") from e
        allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd,
                   ast.Constant, ast.Name, ast.Load)
        for node in ast.walk(tree):
            if not isinstance(node, allowed) or (isinstance(node, ast.Constant)
                                                 and not isinstance(node.value, (int, float))):
                raise ValueError(f"formula {self.formula!r} may only use + - * / brackets, numbers and column names")
            if isinstance(node, ast.Name) and node.id not in self.columns:
                raise ValueError(f"formula uses unknown name {node.id!r}")
        return self


class ValueRange(_Model):
    column: Regex
    min: Number | None = None
    max: Number | None = None

    _check = field_validator("column")(_regex)


class Sorted(_Model):
    column: Regex
    descending: StrictBool = False
    sheet: Sheet | None = None

    _check = field_validator("column")(_regex)
    _sheet = field_validator("sheet")(_check_sheet)


class GroupSource(_Model):
    sheet: Sheet
    group: Regex
    value: Regex | None = None

    _sheet = field_validator("sheet")(_check_sheet)
    _check = field_validator("group", "value")(lambda v: v if v is None else _regex(v))


class GroupTarget(_Model):
    sheet: Sheet
    group: Regex
    count: Regex | None = None
    value: Regex | None = None

    _sheet = field_validator("sheet")(_check_sheet)
    _check = field_validator("group", "count", "value")(lambda v: v if v is None else _regex(v))


class Group(_Model):
    """A summary per group on one sheet must match the list on another (count, sum)."""

    name: str
    source: GroupSource
    target: GroupTarget

    @model_validator(mode="after")
    def _parts(self):
        if self.target.count is None and self.target.value is None:
            raise ValueError("target needs count and/or value")
        if self.target.value is not None and self.source.value is None:
            raise ValueError("target.value needs source.value")
        return self


def _range(lo: int, hi: int):
    def check(v):
        if v is not None and not (len(v) == 2 and lo <= v[0] <= v[1] <= hi):
            raise ValueError(f"must be [from, to] with {lo} ≤ from ≤ to ≤ {hi}")
        return v
    return check


class Checks(_Model):
    """[checks]: content checks on the last delivered file. Allowed keys per file type: checks/registry.py."""

    # every file type
    topics: Topics | None = None
    topics_soft: Topics | None = None
    names: list[str] | None = None
    count: list[Count] | None = None
    words_min: NonNegInt | HardSoft | None = None
    words_max: NonNegInt | None = None
    tables_min: NonNegInt | None = None
    forbidden: Topics | None = None
    # a number per entry; a list inside is a set of alternatives ([-2.5, 2.5])
    values_present: Annotated[list[Number | Annotated[list[Number], Field(min_length=1)]],
                              Field(min_length=1)] | None = None
    retained: Annotated[Number, Field(ge=0, le=1)] | HardSoft | None = None
    numbers_sourced: StrictBool | None = None
    disable: list[str] | None = None
    # docx
    headings_min: NonNegInt | None = None
    toc: StrictBool | None = None
    numbered_list: StrictBool | None = None
    numbered_headings: StrictBool | None = None
    header_contains: Annotated[str, Field(min_length=1)] | None = None
    # xlsx
    sheets_min: NonNegInt | None = None
    data_rows_min: NonNegInt | None = None
    month_rows_min: NonNegInt | None = None
    months: list[StrictInt] | None = None
    dates_between: list[date] | None = None
    columns: list[Regex] | None = None
    formulas_min: NonNegInt | None = None
    total_row: StrictBool | None = None
    line_item_formula: StrictBool | None = None
    priced_items_min: NonNegInt | None = None
    calculations: list[Calculation] | None = None
    value_ranges: list[ValueRange] | None = None
    sorted: Sorted | None = None
    groups: list[Group] | None = None
    column_format: dict[Regex, Literal["percent", "date", "euro"]] | None = None
    workdays: StrictBool | Literal["BW"] | None = None  # "BW": also no public holidays in Baden-Württemberg
    # xlsx and pptx
    chart: StrictBool | None = None
    chart_type: str | list[str] | None = None
    chart_series_min: NonNegInt | None = None
    chart_values: Annotated[list[Annotated[list[Number], Field(min_length=1)]], Field(min_length=1)] | None = None
    chart_series: list[Regex] | None = None
    # pptx
    slides: list[StrictInt] | None = None
    notes_min: NonNegInt | None = None
    side_by_side: Annotated[Topics, Field(min_length=1)] | None = None
    last_slide_topics: Annotated[Topics, Field(min_length=1)] | None = None
    slides_added: StrictInt | list[StrictInt] | None = None

    _topics = field_validator("topics", "topics_soft", "forbidden", "side_by_side", "last_slide_topics")(
        _check_topics)
    _months = field_validator("months")(_range(1, 12))
    _slides = field_validator("slides")(_range(1, 1000))

    @field_validator("columns", "chart_series")
    @classmethod
    def _regexes(cls, v):
        for p in v or []:
            _regex(p)
        return v

    @field_validator("column_format")
    @classmethod
    def _formats(cls, v):
        for p in v or {}:
            _regex(p)
        if v is not None and not v:
            raise ValueError("needs at least one column")
        return v

    @field_validator("dates_between")
    @classmethod
    def _dates(cls, v):
        if v is not None and not (len(v) == 2 and v[0] <= v[1]):
            raise ValueError('must be ["YYYY-MM-DD", "YYYY-MM-DD"] in ascending order')
        return v

    @field_validator("chart_type")
    @classmethod
    def _chart_type(cls, v):
        for t in [v] if isinstance(v, str) else v or []:
            if t not in CHART_TYPES:
                raise ValueError(f"unknown chart type {t!r} (one of {CHART_TYPES})")
        return v

    @field_validator("slides_added")
    @classmethod
    def _slides_added(cls, v):
        if isinstance(v, list) and not (len(v) == 2 and v[0] <= v[1]):
            raise ValueError("must be a number or [from, to]")
        return v

    @field_validator("disable")
    @classmethod
    def _disable(cls, v):
        for name in v or []:
            if name not in GENERAL_CHECKS:
                raise ValueError(f"unknown general check {name!r}")
        return v

    def given(self) -> dict[str, Any]:
        """The keys set in the task file (as plain data)."""
        return self.model_dump(exclude_none=True, mode="json")


class Reply(_Model):
    """[reply]: checks on the model's final text answer."""

    topics: Topics | None = None
    forbidden: Topics | None = None
    words_max: Annotated[StrictInt, Field(ge=1)] | None = None
    no_markdown: StrictBool | None = None

    _topics = field_validator("topics", "forbidden")(_check_topics)


class Behavior(_Model):
    """[behavior]: checks on the tool calls (names of the task's extra tools)."""

    tools_expected: list[str] = []
    tools_forbidden: list[str] = []

    @model_validator(mode="after")
    def _disjoint(self):
        both = set(self.tools_expected) & set(self.tools_forbidden)
        if both:
            raise ValueError(f"{sorted(both)} both expected and forbidden")
        return self


class Judge(_Model):
    """[judge]: what the LLM judge looks for (German, concrete: what makes a 5)."""

    checklist: list[str] = []


class AttachmentRef(_Model):
    name: Annotated[str, Field(min_length=1, pattern=r"^[^/\\]+$")]  # file name as the user uploaded it
    file: Annotated[str, Field(min_length=1, pattern=r"^[^/\\]+$")]  # text file in attachments/


class TurnSpec(_Model):
    text: Annotated[str, Field(min_length=1)]
    expect: Expect | None = None
    attachments: list[AttachmentRef] = []


class TaskSpec(_Model):
    """The raw content of task.toml."""

    id: str
    title: str
    version: Annotated[StrictInt, Field(ge=1)]
    kind: Kind
    file_type: FileType | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    tags: list[Annotated[str, Field(pattern=TAG_PATTERN.pattern)]] = []
    extra_tools: list[str] = []
    dates_from: date | None = None  # appointments before this date are a defect (planning tasks only)
    turns: Annotated[list[TurnSpec], Field(min_length=1)]
    checks: Checks = Checks()
    reply: Reply = Reply()
    behavior: Behavior = Behavior()
    judge: Judge = Judge()

    @model_validator(mode="after")
    def _consistent(self):
        if not ID_PATTERN.match(self.id):
            raise ValueError(f"id {self.id!r} must match {ID_PATTERN.pattern}")
        if self.kind == "no_file":
            if self.file_type is not None:
                raise ValueError("kind = no_file has no file_type")
        elif self.file_type is None:
            raise ValueError(f"kind = {self.kind} needs file_type")
        if self.kind == "follow_up" and len(self.turns) < 2:
            raise ValueError("follow_up needs at least two turns")
        if self.kind != "follow_up" and len(self.turns) != 1:
            raise ValueError("only follow_up has several turns")
        if len(self.turns) > 1 and any(t.attachments for t in self.turns):
            raise ValueError("attachments only in tasks with exactly one turn")
        for t in self.turns:
            names = [a.name for a in t.attachments]
            if len(names) != len(set(names)):
                raise ValueError("attachment names must be unique within a turn")
        unknown = set(self.checks.given()) - task_checks_for(self.file_type)
        if unknown:
            raise ValueError(f"checks not available for {self.file_type or 'tasks without a file'}: {sorted(unknown)}")
        for name in self.behavior.tools_expected + self.behavior.tools_forbidden:
            if name not in self.extra_tools:
                raise ValueError(f"behavior: {name!r} is not one of the task's extra_tools")
        return self


class Attachment(_Model):
    name: str
    text: str


class Turn(_Model):
    text: str
    expect: Expect
    attachments: tuple[Attachment, ...] = ()


class Task(_Model):
    """A loaded task: the spec plus attachment texts and a content hash (written into every run log)."""

    spec: TaskSpec
    turns: tuple[Turn, ...]
    path: Path
    hash: str

    @property
    def id(self) -> str:
        return self.spec.id

    @property
    def expects_file(self) -> bool:
        return self.spec.kind != "no_file"

    @property
    def reference_path(self) -> Path:
        return self.path / "reference.json"

    @property
    def mutants_path(self) -> Path:
        return self.path / "mutants.toml"


def _fail(path: Path, message: str):
    raise TaskError(f"{path}: {message}")


def load_task(folder: Path) -> Task:
    path = folder / "task.toml"
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        _fail(path, str(e))
    try:
        spec = TaskSpec.model_validate(raw)
    except ValidationError as e:
        _fail(path, "\n" + str(e))
    if spec.id != folder.name:
        _fail(path, f"id {spec.id!r} must equal the folder name {folder.name!r}")
    for name in spec.extra_tools:
        if not (EXTRA_TOOLS_DIR / f"{name}.json").is_file():
            _fail(path, f"extra tool {name!r} missing in {EXTRA_TOOLS_DIR.name}/")
    turns = []
    default = "no_file" if spec.kind == "no_file" else "file"
    for t in spec.turns:
        attachments = []
        for a in t.attachments:
            file = folder / "attachments" / a.file
            try:
                text = file.read_bytes().decode("utf-8")
            except FileNotFoundError:
                _fail(path, f"attachment {a.file!r} missing in attachments/")
            except UnicodeDecodeError as e:
                _fail(path, f"attachment {a.file!r} is not UTF-8 ({e.reason} at byte {e.start})")
            if not text.strip():
                _fail(path, f"attachment {a.file!r} is empty")
            attachments.append(Attachment(name=a.name, text=text))
        turns.append(Turn(text=t.text.strip(), expect=t.expect or default, attachments=tuple(attachments)))
    content = json.dumps({"task": raw, "attachments": [[a.model_dump() for a in t.attachments] for t in turns]},
                         sort_keys=True, ensure_ascii=False, default=str)
    return Task(spec=spec, turns=tuple(turns), path=folder,
                hash=hashlib.sha256(content.encode()).hexdigest()[:12])


@cache
def _load_all(directory: Path) -> dict[str, Task]:
    return {f.name: load_task(f) for f in sorted(directory.iterdir()) if (f / "task.toml").is_file()}


def load_tasks(directory: Path = TASKS_DIR) -> dict[str, Task]:
    """All tasks by id, sorted by id."""
    return _load_all(Path(directory).resolve())


def select(selection: str | list[str] | None = None, directory: Path = TASKS_DIR) -> list[Task]:
    """Tasks for a selection: "all", ids, or "tag:<tag>" / "type:<docx|xlsx|pptx>" / "kind:<kind>".

    Parts can be combined with commas ("tag:chart,budget"); the result keeps the order of load_tasks().
    """
    tasks = load_tasks(directory)
    parts = selection if isinstance(selection, list) else (selection or "all").split(",")
    chosen: set[str] = set()
    for part in (p.strip() for p in parts if p.strip()):
        if part == "all":
            chosen |= set(tasks)
        elif part.startswith(("tag:", "type:", "kind:")):
            key, value = part.split(":", 1)
            match = {i for i, t in tasks.items()
                     if (key == "tag" and value in t.spec.tags) or (key == "type" and t.spec.file_type == value)
                     or (key == "kind" and t.spec.kind == value)}
            if not match:
                raise TaskError(f"no task matches {part!r}")
            chosen |= match
        elif part in tasks:
            chosen.add(part)
        else:
            raise TaskError(f"unknown task {part!r}")
    return [t for i, t in tasks.items() if i in chosen]


def selection_hash(tasks: list[Task]) -> str:
    """Hash over the ids and content hashes of a task selection."""
    text = ",".join(f"{t.id}:{t.hash}" for t in sorted(tasks, key=lambda t: t.id))
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def extra_tool(name: str) -> dict:
    """{"spec": OpenAI tool spec, "result": canned answer the harness returns} of an extra tool."""
    return json.loads((EXTRA_TOOLS_DIR / f"{name}.json").read_text(encoding="utf-8"))


def json_schema() -> dict:
    """JSON schema of task.toml (for editors: docs/task.schema.json)."""
    return TaskSpec.model_json_schema()


