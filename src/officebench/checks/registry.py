"""Tables of all checks: names, defect labels, severities and the file types a check applies to.

The task schema (officebench.tasks) accepts exactly the keys listed here, so a typo in a task file cannot silently
switch a check off. Severity: HARD = the task is not done or something is certainly wrong; SOFT = a quality issue or
an uncertain heuristic. A file passes the content check when it has no hard defects.
"""

from typing import Literal, NamedTuple

Severity = Literal["hard", "soft"]
HARD: Severity = "hard"
SOFT: Severity = "soft"
FILE_TYPES = ("docx", "xlsx", "pptx")


class GeneralCheck(NamedTuple):
    label: str  # defect label, used for counting
    severity: Severity
    description: str


class TaskCheck(NamedTuple):
    label: str | None  # None: the key configures other checks and has no defect of its own
    severity: Severity | None
    file_types: tuple[str, ...]  # FILE_TYPES for "every file type"


# Always on; a task switches single ones off with checks.disable.
GENERAL_CHECKS: dict[str, GeneralCheck] = {
    "foreign_script": GeneralCheck(
        "foreign script", HARD,
        "Chinese/Japanese/Korean or other foreign characters (Cyrillic, Arabic …) in the German text"),
    "english": GeneralCheck(
        "English text", SOFT, "text mostly English (more English than German function words)"),
    "control_tokens": GeneralCheck(
        "control tokens", HARD, "the model's control tokens in the text, e.g. <|\"|>"),
    "literal_newline": GeneralCheck(
        "literal \\n", HARD, "a literal \\n instead of a line break"),
    "markdown": GeneralCheck(
        "markdown remnants", SOFT, "markdown remnants: **bold**, ## heading, |---| table separators"),
    "placeholders": GeneralCheck(
        "placeholder", SOFT,
        "placeholders instead of content: [Name eintragen], System X, Max Mustermann, TT.MM.JJJJ, TBD"),
    "weekday": GeneralCheck(
        "wrong weekday", HARD,
        "weekday does not match the date (Montag, 13.10.2026); soft when the year is only inferred (Mo., 13.10.)"),
    "weekend": GeneralCheck(
        "date on a weekend", SOFT,
        "deadline or appointment falls on Saturday/Sunday (only dates after a deadline word or in a date column; "
        "not with a written-out weekday, not in periods)"),
    "calendar_week": GeneralCheck(
        "wrong calendar week", SOFT,
        "calendar week (also „Woche 41“ in a header) does not match the date or month next to it (ISO weeks)"),
    "past_dates": GeneralCheck(
        "date in the past", SOFT,
        "appointment before the task's dates_from (only when set; the document date and „Stand“ do not count)"),
    "text_arithmetic": GeneralCheck(
        "wrong calculation in text", SOFT,
        "a calculation in running text or a Word/slide table does not add up: 80 × 8 € × 12 = 7.860 €, "
        "total row ≠ sum"),
    "formula_errors": GeneralCheck(
        "formula error", HARD, "error value after recalculation (#VALUE!, #REF!, #NAME?, #DIV/0!, Err:…)"),
    "formula_empty": GeneralCheck(
        "formula without result", HARD, "formula cell without a value after recalculation"),
    "formula_as_text": GeneralCheck(
        "formula as text", HARD, "formula stored as a string (=SUM(…) or \"=B2-B3\")"),
    "number_as_text": GeneralCheck(
        "number as text", SOFT, "number stored as text („1.500 €“)"),
    "text_in_number_column": GeneralCheck(
        "text in number column", SOFT, "text in a column formatted as numbers"),
    "empty_number_column": GeneralCheck(
        "empty number column", SOFT,
        "number/currency column without a value; hard when all numbers of a sheet are 0 (empty template)"),
    "zero_sum": GeneralCheck(
        "sum is 0", HARD, "SUM result is 0 although the range holds values"),
    "sum_range": GeneralCheck(
        "incomplete sum range", SOFT,
        "SUM of the total row misses data rows, skips numbers stored as text or is not a SUM"),
    "empty_table": GeneralCheck(
        "incomplete table", SOFT,
        "table with only a header row, or an empty header cell above a column with values (first column excepted)"),
    "invalid_date": GeneralCheck(
        "invalid date", HARD, "text cell with a date that does not exist (31.11.2026, 2026-02-30)"),
    "date_as_text": GeneralCheck(
        "date as text", SOFT, "valid date stored as text in a date column („2026-07-01“)"),
    "share_over_100": GeneralCheck(
        "share over 100 %", SOFT,
        "share/rate in percent format above 100 % (utilisation, percent columns above 1,000 %), usually share × 100 "
        "in percent format"),
}

_ALL = FILE_TYPES
_XP = ("xlsx", "pptx")

# Keys of [checks]. Missing required parts are hard; "not checkable" and exceeded upper limits are soft.
TASK_CHECKS: dict[str, TaskCheck] = {
    "topics": TaskCheck("missing topic", HARD, _ALL),
    "topics_soft": TaskCheck("missing topic", SOFT, _ALL),
    "names": TaskCheck("missing names", HARD, _ALL),
    "count": TaskCheck("too few matches", HARD, _ALL),
    "words_min": TaskCheck("very short", HARD, _ALL),
    "words_max": TaskCheck("too long", SOFT, _ALL),
    "tables_min": TaskCheck("no table", HARD, _ALL),
    "forbidden": TaskCheck("forbidden content", HARD, _ALL),
    "values_present": TaskCheck("missing value", HARD, _ALL),
    "retained": TaskCheck("content not retained", HARD, _ALL),
    "numbers_sourced": TaskCheck("number without source", SOFT, _ALL),
    "disable": TaskCheck(None, None, _ALL),
    "headings_min": TaskCheck("too few headings", HARD, ("docx",)),
    "toc": TaskCheck("no table of contents", HARD, ("docx",)),
    "numbered_list": TaskCheck("no numbered list", HARD, ("docx",)),
    "numbered_headings": TaskCheck("sections not numbered", HARD, ("docx",)),
    "header_contains": TaskCheck("missing header text", HARD, ("docx",)),
    "sheets_min": TaskCheck("too few sheets", HARD, ("xlsx",)),
    "data_rows_min": TaskCheck("too few rows", HARD, ("xlsx",)),
    "month_rows_min": TaskCheck("too few rows", HARD, ("xlsx",)),
    "months": TaskCheck("missing months", HARD, ("xlsx",)),
    "dates_between": TaskCheck("date out of range", HARD, ("xlsx",)),
    "columns": TaskCheck("missing column", HARD, ("xlsx",)),
    "formulas_min": TaskCheck("no formula", HARD, ("xlsx",)),
    "total_row": TaskCheck("no total row", HARD, ("xlsx",)),
    "line_item_formula": TaskCheck("no line item formula", HARD, ("xlsx",)),
    "priced_items_min": TaskCheck("missing prices", HARD, ("xlsx",)),
    "calculations": TaskCheck("wrong calculation", HARD, ("xlsx",)),
    "value_ranges": TaskCheck("value out of range", HARD, ("xlsx",)),
    "sorted": TaskCheck("not sorted", HARD, ("xlsx",)),
    "groups": TaskCheck("summary does not match", HARD, ("xlsx",)),
    "column_format": TaskCheck("wrong number format", SOFT, ("xlsx",)),
    "workdays": TaskCheck("date not on a workday", SOFT, ("xlsx",)),
    "chart": TaskCheck("no chart", HARD, _XP),
    "chart_type": TaskCheck("wrong chart type", HARD, _XP),
    "chart_series_min": TaskCheck("too few chart series", HARD, _XP),
    "chart_values": TaskCheck("wrong chart values", HARD, _XP),
    "chart_series": TaskCheck("missing chart series", HARD, _XP),
    "slides": TaskCheck("slide count", HARD, ("pptx",)),
    "notes_min": TaskCheck("too few speaker notes", HARD, ("pptx",)),
    "side_by_side": TaskCheck("no side-by-side comparison", SOFT, ("pptx",)),
    "last_slide_topics": TaskCheck("not on the last slide", SOFT, ("pptx",)),
    "slides_added": TaskCheck("slides added", SOFT, ("pptx",)),
}

# Keys of [reply]: checks on the model's final text answer.
REPLY_CHECKS: dict[str, tuple[str, Severity]] = {
    "topics": ("missing topic in reply", HARD),
    "forbidden": ("forbidden content in reply", HARD),
    "words_max": ("reply too long", SOFT),
    "no_markdown": ("markdown in reply", SOFT),
}

# Keys of [behavior]: checks on the tool calls in the log.
BEHAVIOR_CHECKS: dict[str, tuple[str, Severity]] = {
    "tools_expected": ("tool not called", HARD),
    "tools_forbidden": ("unwanted tool call", HARD),
}

CHART_TYPES = ("column", "bar", "line", "pie")
COLUMN_FORMATS = ("percent", "date", "euro")


def task_checks_for(file_type: str | None) -> set[str]:
    """Keys of [checks] allowed for a file type (None: tasks without a file only get the every-type keys)."""
    return {k for k, c in TASK_CHECKS.items() if c.file_types == _ALL or (file_type in c.file_types)}
