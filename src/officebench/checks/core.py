"""Shared types of the checks: defects (Defect), findings (Findings), the document model and the check context.

The tables of all checks (names, labels, severities) are in registry.py.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from .registry import GENERAL_CHECKS, HARD, SOFT, TASK_CHECKS

if TYPE_CHECKING:
    from ..tasks import Task

REFERENCE_DATE = date(2026, 10, 13)  # reference date of the benchmark ("Heute ist Dienstag, 13. Oktober 2026.")
NOT_CHECKABLE = "not checkable"
CRASHED = "check crashed"  # an exception inside one check: soft, the other findings stay
# Defects of the file as a whole (not from a single check).
FILE_DEFECTS = {"unreadable": HARD, "wrong_file_type": HARD, "unknown_file_type": HARD, "not_recalculated": HARD}


class Defect(str):
    """A defect: a short English sentence with the location; .label (type for counting), .severity (hard/soft) and
    .check (name of the check that found it). A str, so lists of defects print and compare as their messages."""

    def __new__(cls, label: str, text: str, severity: str = HARD, check: str | None = None):
        obj = super().__new__(cls, text)
        obj.label = label
        obj.severity = severity
        obj.check = check or label
        return obj

    def __getnewargs__(self):
        return self.label, str(self), self.severity, self.check

    @property
    def hard(self) -> bool:
        return self.severity == HARD


@dataclass
class Findings:
    defects: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    @property
    def hard(self) -> list:
        return [m for m in self.defects if getattr(m, "severity", HARD) == HARD]

    @property
    def soft(self) -> list:
        return [m for m in self.defects if getattr(m, "severity", HARD) != HARD]

    @property
    def ok(self) -> bool:
        """No hard defects ("content ok")."""
        return not self.hard

    @property
    def clean(self) -> bool:
        """No defects at all."""
        return not self.defects


@dataclass
class Table:
    """A table as rows of cell texts (Word, slide or sheet). calc=False: no row-wise calculation check (sheets have
    checks.calculations instead)."""
    where: str
    rows: list
    calc: bool = True


@dataclass
class Document:
    """The visible text of a file in reading order, for the text-based checks."""
    paragraphs: list = field(default_factory=list)  # [(where, text)]: paragraphs, cells, slide texts, notes
    tables: list = field(default_factory=list)  # [Table]
    # numbers for values_present (xlsx: cell values, pptx: text and chart values); None = numbers in the text
    numbers: list | None = None
    # xlsx: [(where, number, percent format)] of number cells without formula (numbers_sourced)
    constants: list | None = None
    slides: list | None = None  # pptx: [Slide] in order (side_by_side, last_slide_topics)

    @property
    def text(self) -> str:
        return "\n".join(t for _, t in self.paragraphs)


@dataclass
class Slide:
    """Text of one slide (titles, shapes, tables; notes apart) and whether it shows two columns side by side: two
    text shapes next to each other or a table with at least two columns and two rows."""
    number: int
    text: str = ""
    notes: str = ""
    two_columns: bool = False


@dataclass
class Context:
    """Everything a checker needs besides the file: task, reference date, the collected defects and, for follow-up
    tasks, the file of the previous turn (retained)."""
    task: Task | None = None
    today: date = REFERENCE_DATE
    defects: list = field(default_factory=list)
    previous: Path | None = None
    # checks.given() dumps the pydantic model; the checkers ask for single keys hundreds of times per file
    _checks: tuple = field(default=(None, {}), init=False, repr=False, compare=False)

    @property
    def checks(self) -> dict:
        """The task's [checks] as plain data (only the keys set in the task; {} without a task)."""
        if self._checks[0] is not self.task:
            self._checks = (self.task, self.task.spec.checks.given() if self.task is not None else {})
        return self._checks[1]

    @property
    def dates_from(self) -> date | None:
        return self.task.spec.dates_from if self.task is not None else None

    def enabled(self, name: str) -> bool:
        """Is the general check `name` on for this task?"""
        if name in self.checks.get("disable", ()):
            return False
        return name != "past_dates" or self.dates_from is not None

    def get(self, key: str, default=None):
        return self.checks.get(key, default)

    def report(self, check: str, text: str, label: str | None = None, severity: str | None = None) -> Defect:
        """Add a defect of check `check` (label and severity default to the tables in registry.py)."""
        if check in GENERAL_CHECKS:
            std_label, std_severity, _ = GENERAL_CHECKS[check]
        elif check in TASK_CHECKS:
            std_label, std_severity, _ = TASK_CHECKS[check]
        else:
            std_label, std_severity = check, FILE_DEFECTS.get(check, HARD)
        m = Defect(label or std_label, text, severity or std_severity, check)
        self.defects.append(m)
        return m

    def not_checkable(self, check: str, text: str) -> Defect:
        return self.report(check, f"not checkable: {text}", label=NOT_CHECKABLE, severity=SOFT)

    @contextmanager
    def guarded(self, check: str):
        """Run one check; an exception becomes a soft defect instead of making the whole file 'unreadable'."""
        try:
            yield
        except Exception as e:  # noqa: BLE001 - any bug in one check must not hide the others
            self.report(check, f"check crashed: {type(e).__name__}: {str(e)[:100]}", label=CRASHED, severity=SOFT)
