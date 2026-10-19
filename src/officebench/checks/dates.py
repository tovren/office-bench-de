"""Dates in running text: weekday matches date (weekday), calendar week matches the date or month next to it
(calendar_week), no dates before the task's dates_from (past_dates), no deadlines on a weekend (weekend).

Dates: 12.10.2026, 12.10.26, 12.10., 12. Oktober 2026, 12. Okt., 2026-10-12; months: Dezember 2026, Okt.;
calendar weeks: KW 44, KW 44/2026, KW 42-44 2026, KW 49/2026-KW 03/2027, KW 52-1 (ISO weeks).
Units are paragraphs, cells, slide texts in reading order; a date without a year takes the year of the last date
with a year before it (else of `today`), the next year if it would lie more than 120 days before that reference date
(YearContext.date); the weekday check accepts both years once it lies more than 60 days before the reference
(YearContext.candidates).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from .core import Context, Document
from .registry import SOFT
from .util import norm

MONTHS = {"jan": 1, "jän": 1, "feb": 2, "mär": 3, "mrz": 3, "mae": 3, "apr": 4, "mai": 5, "jun": 6, "jul": 7,
          "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dez": 12}
MONTH = (r"(?:Januar|Jänner|Februar|März|Maerz|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember|"
         r"Jan|Jän|Feb|Mär|Mrz|Apr|Jun|Jul|Aug|Sept|Sep|Okt|Nov|Dez)")
WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
WEEKDAY_LONG = {w.lower(): i for i, w in enumerate(WEEKDAYS)} | {"sonnabend": 5}
WEEKDAY_SHORT = {"Mo": 0, "Di": 1, "Mi": 2, "Do": 3, "Fr": 4, "Sa": 5, "So": 6}
# English names for the explanations in defect texts (the German list above matches document text).
_WEEKDAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_W = r"A-Za-zÄÖÜäöüß"

DATE_RX = re.compile(
    # a year after "12.10." only directly (two digits) or as four digits, never a time: "11.12. 17:00", "11.12. 17 Uhr"
    r"(?<![\d.])(?P<t1>\d{1,2})\.\s?(?P<m1>\d{1,2})\.(?:(?P<j1>\d{4}|\d{2})|\s(?P<j1b>\d{4}))?"
    r"(?(j1)(?!\d|\.\d|\s*(?::\d|Uhr|h\b)))(?(j1b)(?!\d|\.\d|\s*(?::\d|Uhr|h\b)))(?!\d)"
    rf"|(?<![\d.])(?P<t2>\d{{1,2}})\.\s*(?P<m2>{MONTH})\.?(?:\s+(?P<j2>\d{{4}}))?(?![{_W}])"
    r"|(?<![\d.-])(?P<j3>\d{4})-(?P<m3>\d{2})-(?P<t3>\d{2})(?!\d)", re.I)
MONTH_RX = re.compile(rf"(?<![{_W}])(?P<m>{MONTH})\.?(?![{_W}])(?:\s+(?P<j>\d{{4}}))?", re.I)
WEEKDAY_RX = re.compile(rf"(?<![{_W}-])(?:(?P<lang>(?i:Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonnabend|"
                        rf"Sonntag))|(?P<kurz>Mo|Di|Mi|Do|Fr|Sa|So))(?![{_W}])\.?")
_YEAR = r"(?:\s*[/']\s*(?P<{0}>\d{{4}}|\d{{2}})(?!\d)|\s+(?P<{0}2>20\d\d)(?!\d))?"
WEEK_RX = re.compile(r"(?<![\w])(?:KW|Kw|kw|Kalenderwoche|Kal\.-Woche)\.?\s*(?P<a>\d{1,2})(?!\d)" + _YEAR.format("ja")
                     + r"(?:\s*(?:-|bis)\s*(?:(?:KW|Kw|kw)\.?\s*)?(?P<b>\d{1,2})(?!\d|\.\d)" + _YEAR.format("jb")
                     + ")?")
# Text right before a date that marks it as the document's own date or a past reference, not a deadline.
NOT_A_DEADLINE = re.compile(r"(?:stand|datum|erstellt|version|fassung|vom|seit|zuletzt|bisher|aktualisiert|sitzung|"
                            r"besprechung|protokoll|geändert|ausgabe)\b[^.\n]{0,25}$", re.I)
# A sentence in the past ('wurde am 05.10.2026 erarbeitet', 'hat am 15. September 2026 beauftragt') reports a fact.
PAST_TENSE = re.compile(r"\b(?:wurden?|wurde|hat|haben|hatte|hatten|war|waren|fand|fanden|erfolgte|bereits|"
                        r"zuletzt|bisher)\b", re.I)
FILLER = re.compile(rf"^\s*[(,:;/-]?\s*(?:(?:ca\.|etwa|Anfang|Mitte|Ende|Start|Beginn|ab|vom|am|bis|von)\s+)*"
                    rf"(?:(?:{'|'.join(WEEKDAYS)}|Mo|Di|Mi|Do|Fr|Sa|So)\.?,?\s+)?")

# Location markers written by the docx/pptx readers ("table 1, row 2", "slide 2, table row 3", "title", "title
# slide"): the cells of a table row share the label left of them; a title is the document's name, not a deadline.
_ROW = " row "
_TITLE = "title"


def month_number(name: str) -> int:
    n = name.lower()
    return 3 if n.startswith("mär") or n.startswith("mae") else MONTHS.get(n[:3], 0)


def _year(s: str | None) -> int | None:
    """Year of a date; None if missing or implausible (1900–2100), so arithmetic never leaves the date range."""
    if not s:
        return None
    y = int(s)
    y = y if y >= 100 else 2000 + y
    return y if 1900 <= y <= 2100 else None


@dataclass
class DateMatch:
    """A date found in text; year None = no year written."""
    day: int
    month: int
    year: int | None
    start: int
    end: int
    text: str

    def with_year(self, year: int) -> date | None:
        try:
            return date(year, self.month, self.day)
        except ValueError:
            return None


def dates_in(text: str) -> list[DateMatch]:
    """All valid dates in an (already normalised) text."""
    out = []
    for m in DATE_RX.finditer(text):
        if m["t1"]:
            d, mo, y = int(m["t1"]), int(m["m1"]), _year(m["j1"] or m["j1b"])
        elif m["t2"]:
            d, mo, y = int(m["t2"]), month_number(m["m2"]), _year(m["j2"])
        else:
            d, mo, y = int(m["t3"]), int(m["m3"]), int(m["j3"])
        if not (1 <= mo <= 12 and 1 <= d <= 31) or (y is not None and not 1990 <= y <= 2100):
            continue
        f = DateMatch(d, mo, y, m.start(), m.end(), m.group(0).strip())
        if f.with_year(y or 2024) is None:  # 31.02. etc. (2024 is a leap year: 29.02. stays)
            continue
        out.append(f)
    return out


class YearContext:
    """Year for dates without one: the reference is the last date with a year before it in reading order, else
    `today`."""

    def __init__(self, today: date):
        self.ref = today

    def see(self, f: DateMatch):
        if f.year:
            self.ref = f.with_year(f.year) or self.ref

    def date(self, f: DateMatch) -> date | None:
        """The date in the reference year, or in the next year if it would lie more than 120 days before the
        reference (a deadline in January after an October meeting)."""
        if f.year:
            return f.with_year(f.year)
        d = f.with_year(self.ref.year)
        if d and d < self.ref - timedelta(days=120):
            d = f.with_year(self.ref.year + 1)
        return d

    def candidates(self, f: DateMatch) -> list[date]:
        """Possible dates of a date without a year: the reference year; also the next year if the date would lie
        more than 60 days before the reference (a weekday fits either reading)."""
        if f.year:
            return [d] if (d := f.with_year(f.year)) else []
        d0 = f.with_year(self.ref.year)
        years = (self.ref.year, self.ref.year + 1) if d0 and d0 < self.ref - timedelta(days=60) else (self.ref.year,)
        return [d for y in years if (d := f.with_year(y))]


def _fmt(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _is_a(d: date) -> str:
    return f"{_fmt(d)} is a {_WEEKDAYS_EN[d.weekday()]}"


def _examples(found: list, n: int = 3) -> str:
    parts = [f"„{t}“{(' – ' + z) if z else ''} ({where})" for t, z, where in found[:n]]
    return "; ".join(parts) + (f" and {len(found) - n} more" if len(found) > n else "")


# ------------------------------------------------------------------------------------------- weekday --

def _weekday(m: re.Match) -> int:
    return WEEKDAY_LONG[m["lang"].lower()] if m["lang"] else WEEKDAY_SHORT[m["kurz"]]


def weekday_pairs(text: str) -> list[tuple[int, DateMatch, str]]:
    """(weekday 0-6, date, quoted text) for 'Montag, 12.10.2026', 'Mo., 12.10.', '12.10.2026 (Montag)'."""
    pairs = []
    for m in WEEKDAY_RX.finditer(text):
        before = text[max(0, m.start() - 20):m.start()]
        if re.search(WEEKDAY_RX.pattern + r"\s*(?:-|bis|/)\s*$", before):  # second day of a range like Mo-Fr
            continue
        after = re.match(r"[\s,]*(?:den\s+|dem\s+|der\s+)?", text[m.end():])
        pos = m.end() + after.end()
        d = DATE_RX.match(text, pos)
        if d and d.start() == pos and (found := dates_in(text[pos:d.end()])) and found[0].start == 0:
            f = found[0]
            f.start, f.end = f.start + pos, f.end + pos
            pairs.append((_weekday(m), f, text[m.start():d.end()].strip()))
    for f in dates_in(text):
        if w := re.match(r"\s*\(\s*" + WEEKDAY_RX.pattern + r"\s*\)", text[f.end:]):
            pairs.append((WEEKDAY_LONG[w["lang"].lower()] if w["lang"] else WEEKDAY_SHORT[w["kurz"]], f,
                          text[f.start:f.end + w.end()].strip()))
    return pairs


def _only_weekday(cell: str) -> int | None:
    m = WEEKDAY_RX.fullmatch(cell.strip())
    return _weekday(m) if m else None


def _only_date(cell: str) -> DateMatch | None:
    c = cell.strip()
    found = dates_in(c)
    return found[0] if len(found) == 1 and found[0].start == 0 and found[0].end >= len(c.rstrip(".")) else None


# ---------------------------------------------------------------------------------------- calendar week --

@dataclass
class WeekMention:
    """A calendar week or week range 'KW a[/year_a]-b[/year_b]'; years None when not written."""
    a: int
    b: int
    year_a: int | None
    year_b: int | None
    text: str
    start: int
    end: int


def week_mentions(text: str, today: date) -> list[WeekMention]:
    out = []
    for m in WEEK_RX.finditer(text):
        a, b = int(m["a"]), int(m["b"]) if m["b"] else None
        ya, yb = _year(m["ja"] or m["ja2"]), _year(m["jb"] or m["jb2"])
        if m["ja"] and len(m["ja"]) == 2 and abs(ya - today.year) > 2 and b is None:
            ya, b = None, int(m["ja"])  # KW 44/45 = weeks 44 and 45, not 2045
        if b is None:
            b, yb = a, ya
        if ya is None and yb is not None:
            ya = yb - 1 if b < a else yb
        if yb is None and ya is not None:
            yb = ya + 1 if b < a else ya
        out.append(WeekMention(a, b, ya, yb, m.group(0).strip(), m.start(), m.end()))
    return out


def week_range(a: int, b: int, year_a: int, year_b: int | None = None) -> tuple[date, date] | None:
    year_b = year_b or (year_a + 1 if b < a else year_a)
    try:
        return date.fromisocalendar(year_a, a, 1), date.fromisocalendar(year_b, b, 7)
    except ValueError:
        return None


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    end = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return date(year, month, 1), end


@dataclass
class Period:
    """What stands next to a calendar week: days (day, month, year) or months (month, year), first and last."""
    kind: str  # "days" | "months"
    parts: list  # [(day|None, month, year|None)]
    text: str


def period_at_start(text: str) -> Period | None:
    """A date, date range or month (range) right at the start of `text` (after filler like '(', 'ab', 'Anfang')."""
    separator = re.match(r"\s*([(,:;/-]?)", text).group(1)
    f = FILLER.match(text)
    rest_start = f.end() if f else 0
    rest = text[rest_start:]
    found = dates_in(rest)
    if found and found[0].start == 0:
        parts = [found[0]]
        if len(found) > 1 and re.fullmatch(r"\s*(?:-|bis)\s*", rest[found[0].end:found[1].start]):
            parts.append(found[1])
        last_year = parts[-1].year
        tuples = [(x.day, x.month, x.year or last_year) for x in parts]
        return Period("days", tuples, text[:rest_start] + rest[:parts[-1].end])
    m = MONTH_RX.match(rest)
    if m and separator in ("(", ",", "/"):  # 'KW 45: Juni-Termine abstimmen' is a topic, not a date
        parts = [(None, month_number(m["m"]), _year(m["j"]))]
        end = m.end()
        m2 = re.match(r"\s*(?:-|bis|/)\s*", rest[end:])
        if m2 and (m3 := MONTH_RX.match(rest, end + m2.end())):
            parts.append((None, month_number(m3["m"]), _year(m3["j"])))
            end = m3.end()
        if parts[0][2] is None and parts[-1][2] is not None:
            parts[0] = (None, parts[0][1], parts[-1][2] - (parts[0][1] > parts[-1][1]))
        return Period("months", parts, text[:rest_start] + rest[:end])
    return None


def _nearest(day: int | None, month: int, ref: date) -> int:
    """Year that puts day/month closest to `ref`."""
    best = None
    for y in (ref.year - 1, ref.year, ref.year + 1):
        try:
            d = date(y, month, day or 15)
        except ValueError:
            continue
        if best is None or abs((d - ref).days) < abs((best - ref).days):
            best = d
    return best.year if best else ref.year


def week_fits(kw: WeekMention, z: Period, context_year: int) -> tuple[bool, str]:
    """Does the week range fit the date/month next to it for some reading of missing years? -> (ok, explanation)."""
    if kw.year_a:
        years = [kw.year_a]
    else:
        named = [y for _, _, y in z.parts if y]
        years = list(dict.fromkeys(named + [context_year, context_year + 1, context_year - 1]))
    explanation, min_gap = "", None
    for year in years:
        span = week_range(kw.a, kw.b, year, kw.year_b if kw.year_a else None)
        if span is None:
            continue
        first, last = span
        ok, gap = True, 0
        for day, month, y in (z.parts[0], z.parts[-1]):
            y = y or _nearest(day, month, first)
            if z.kind == "days":
                try:
                    d = date(y, month, day)
                except ValueError:
                    ok = False
                    break
                ok = ok and first <= d <= last
                gap += max((first - d).days, (d - last).days, 0)
            else:
                m0, m1 = _month_bounds(y, month)
                ok = ok and m0 <= last and m1 >= first
                gap += max((m0 - last).days, (first - m1).days, 0)
        if ok:
            return True, ""
        # explain with the reading closest to the stated period
        if min_gap is None or gap < min_gap:
            numbers = f"KW {kw.a}" + (f"–{kw.b}" if kw.b != kw.a else "")
            explanation, min_gap = f"{numbers}/{year} = {first:%d.%m.}–{_fmt(last)}", gap
    return False, explanation


def _week_invalid(kw: WeekMention) -> str | None:
    for nr, year in ((kw.a, kw.year_a), (kw.b, kw.year_b or kw.year_a)):
        if not 1 <= nr <= 53:
            return f"KW {nr} does not exist"
        if nr == 53 and year and date(year, 12, 28).isocalendar()[1] == 52:
            return f"KW 53/{year} does not exist ({year} has 52 calendar weeks)"
    return None


# Header of a table column with calendar weeks ('KW', 'Kalenderwoche', 'KW (ISO)').
WEEK_HEADER = re.compile(r"(?:KW|Kalenderwoche|Kal\.?-?\s?Woche)\.?(?:\s*\(?(?:Nr\.?|ISO)\)?)?", re.I)


def _week_cell(cell: str, today: date) -> WeekMention | None:
    """The calendar week of a cell that holds only one: '45', '45/2026', '45-46', 'KW 45'."""
    text = cell if re.match(r"(?:KW|Kalenderwoche)", cell, re.I) else f"KW {cell}"
    kws = week_mentions(text, today)
    if len(kws) == 1 and kws[0].start == 0 and kws[0].end >= len(text.rstrip(".")):
        return kws[0]
    return None


# Header of a column with the start or end of a period (for a calendar week in running text in the same row); not
# deadlines ('Frist', 'Umsetzung bis') or plan dates next to actual ones.
PERIOD_HEADER = re.compile(r"start|beginn|anfang|\bvon\b|\bab\b|ende\b|zeitraum|datum|zeitfenster", re.I)
NOT_PERIOD_HEADER = re.compile(r"frist|fällig|deadline|erledig|umsetzung|abgabe|\bbis\b|plan|soll|\bist\b", re.I)


def _row_weeks(cells: list, header: list, today: date) -> tuple[list, bool]:
    """Calendar weeks of a table row and whether they stand in running text: the cells of a KW column and cells
    with only a calendar week; without such a cell the calendar weeks in the text of cells without a date or month
    ('Kick-off in KW 42 und Bedarfsaufnahme'). Invalid weeks (KW 54) are left to the check of the text."""
    own = [kw for i, c in enumerate(cells) if c and (i < len(header) and WEEK_HEADER.fullmatch(header[i])
                                                     or WEEK_RX.match(c)) and (kw := _week_cell(c, today))]
    in_text = not own
    if in_text:
        own = [kw for c in cells if not dates_in(c) and not MONTH_RX.search(c) for kw in week_mentions(c, today)]
    return [kw for kw in own if not _week_invalid(kw)], in_text


def _week_overlaps(kw: WeekMention, dates: list, context_year: int) -> tuple[bool, str]:
    """Does the week range overlap the period from the earliest to the latest date of the row for some reading of
    missing years? Start and end of a task may lie in different weeks; a week of either (or between) fits."""
    if kw.year_a:
        years = [kw.year_a]
    else:
        named = [f.year for f in dates if f.year] or [context_year]
        years = list(dict.fromkeys(y for n in named for y in (n, n - 1, n + 1)))
    explanation, min_gap = "", None
    for year in years:
        span = week_range(kw.a, kw.b, year, kw.year_b if kw.year_a else None)
        if span is None:
            continue
        first, last = span
        days = [d for f in dates if (d := f.with_year(f.year or _nearest(f.day, f.month, first)))]
        if not days:
            continue
        earliest, latest = min(days), max(days)
        if earliest <= last and latest >= first:
            return True, ""
        gap = max((first - latest).days, (earliest - last).days)
        if min_gap is None or gap < min_gap:
            numbers = f"KW {kw.a}" + (f"–{kw.b}" if kw.b != kw.a else "")
            explanation, min_gap = f"{numbers}/{year} = {first:%d.%m.}–{_fmt(last)}", gap
    return min_gap is None, explanation


def _sentence(text: str, start: int, end: int) -> str:
    """The sentence around text[start:end] (dots inside dates do not end it)."""
    begin = max((m.end() for m in re.finditer(r"[.!?]\s+(?=[A-ZÄÖÜ])|\n", text[:start])), default=0)
    m = re.search(r"[.!?]\s+(?=[A-ZÄÖÜ])|\n", text[end:])
    return text[begin:end + (m.start() if m else len(text))]


# Words right before a date that make it a deadline or appointment (for weekend).
DEADLINE_BEFORE = re.compile(r"(?:\bbis|spätestens|frist|fällig|deadline|termin|abgabe|\bam|\bstart|beginn|go-?live|"
                             r"kick-?off|treffen|besprechung|meeting|sitzung|schulung|workshop|lieferung|abschluss|"
                             r"abnahme|rückmeldung|einreich\w*|anmeld\w*)\b[^.\n]{0,25}$", re.I)
# Sentences where a weekend date is intended (holiday, closed office, a party on Saturday …, a rule that comes into
# force).
WEEKEND_OK = re.compile(r"urlaub|\bfrei\b|geschlossen|wochenende|samstag|sonntag|feier|\bfest\b|ferien|in kraft", re.I)
# Validity right before the date ('gilt ab 01.11.', 'gelten bis zum 31.10.', 'gültig bis 30.10.'): the start or end of a
# period, not a deadline; 'bis 25.10.2026, damit das Angebot noch gilt' stays a deadline.
VALID_BEFORE = re.compile(r"\b(?:gilt|gelten|galt|gültig\w*)\b[^.;:()\n]{0,80}$", re.I)
# Table columns with deadlines/appointments; purchase or birth dates are not appointments.
DEADLINE_HEADER = re.compile(r"frist|fällig|termin|deadline|\bbis\b|wann|abgabe|^\s*(?:datum|tag|start|beginn)\b|"
                             r"reisedatum|fahrtdatum|sitzung", re.I)
NOT_DEADLINE_HEADER = re.compile(r"garantie|ablauf|gültig|kauf|geburt|anschaff", re.I)
WEEK_IN_HEADING = re.compile(
    r"(?<![\w])(?:(?:KW|Kalenderwoche)\s*(?P<kw>\d{1,2})|Woche\s+(?P<w>\d{2}))(?![\d.])(?!\s*[-/]\s*\d)")


def _prompt_dates(ctx: Context) -> set:
    """Dates the task itself names, in a message or in the files attached to it (a weekend date given by the user is
    not the model's mistake). Attachments first: the runner puts their text in front of the message."""
    yc, out = YearContext(ctx.today), set()
    for turn in getattr(ctx.task, "turns", ()) or ():
        texts = [getattr(a, "text", "") or "" for a in getattr(turn, "attachments", ()) or ()]
        for text in texts + [getattr(turn, "text", "") or ""]:
            for f in dates_in(norm(text)):
                if d := yc.date(f):
                    out.add(d)
                yc.see(f)
    return out


def _in_period(text: str, f: DateMatch, found: list) -> bool:
    return any(re.fullmatch(r"\s*(?:-|bis|und)\s*", text[g.end:f.start]) for g in found if g.end <= f.start) or \
        any(re.fullmatch(r"\s*(?:-|bis|und)\s*", text[f.end:g.start]) for g in found if g.start >= f.end) or \
        bool(re.match(r"\s*-", text[f.end:])) or bool(re.search(r"\bvom\s*$|\d\.\s*-\s*$", text[:f.start]))


def _week_in_heading(doc: Document, ctx: Context) -> list:
    """'Teambesprechung – Woche 41' near the top while the document's own date (12.10.2026) is in KW 42."""
    head = doc.paragraphs[:6]
    own = next((d for _, t in head for f in dates_in(norm(t)) if f.year and (d := f.with_year(f.year))), None)
    if own is None:
        return []
    out = []
    for where, raw in head:
        text = norm(raw)
        for m in WEEK_IN_HEADING.finditer(text):
            if period_at_start(text[m.end():m.end() + 80]) or re.search(r"\(\s*$", text[:m.start()]):
                continue  # a week with its own date is checked in the main loop
            nr = int(m["kw"] or m["w"])
            if 1 <= nr <= 53 and nr != own.isocalendar()[1]:
                out.append((m.group(0), f"the document is dated {_fmt(own)} (KW {own.isocalendar()[1]})", where))
    return out


# ------------------------------------------------------------------------------------------------ run --

def check_dates(doc: Document, ctx: Context) -> dict:
    """weekday, calendar_week, past_dates, weekend over all units in reading order (plus table rows)."""
    yc = YearContext(ctx.today)
    wrong_hard, wrong_soft, week_wrong, past, weekend = [], [], [], [], []
    dates_from = ctx.dates_from if ctx.enabled("past_dates") else None
    given = _prompt_dates(ctx) if ctx.enabled("weekend") else set()
    if ctx.enabled("calendar_week"):
        week_wrong += _week_in_heading(doc, ctx)
    before_in_row: dict[str, str] = {}  # table cells: the cells before in the same row ('Datum | 12.10.2026')
    for where, raw in doc.paragraphs:
        text = norm(raw)
        found = dates_in(text)
        before = before_in_row.get(where, "") if _ROW in where else ""
        if _ROW in where:
            before_in_row[where] = f"{before} {text}"[-200:]
        if ctx.enabled("weekday"):
            for wd, f, quote in weekday_pairs(text):
                for g in [g for g in found if g.end <= f.start]:
                    yc.see(g)
                if f.year:
                    d = f.with_year(f.year)
                    if d and d.weekday() != wd:
                        wrong_hard.append((quote, _is_a(d), where))
                else:
                    candidates = yc.candidates(f)
                    if candidates and all(d.weekday() != wd for d in candidates):
                        d = yc.date(f) or candidates[0]
                        wrong_soft.append((quote, _is_a(d), where))
        if ctx.enabled("calendar_week"):
            for kw in week_mentions(text, ctx.today):
                if reason := _week_invalid(kw):
                    week_wrong.append((kw.text, reason, where))
                    continue
                z = period_at_start(text[kw.end:kw.end + 80])
                quote = text[kw.start:kw.end] + (z.text if z else "")
                if z and quote.count("(") > quote.count(")") and text[kw.end + len(z.text):].lstrip().startswith(")"):
                    quote += ")"
                if z is None and (paren := re.search(r"\(\s*$", text[:kw.start])):
                    # '26.10.2026 (KW 44)': the date in front of the parenthesis. Reusing `before` is inherited
                    # from the old code: past_dates below then looks at this text instead of the row's earlier cells.
                    before = text[:paren.start()].rstrip()
                    preceding = [g for g in dates_in(before) if g.end == len(before)]
                    if preceding:
                        g = preceding[-1]
                        z = Period("days", [(g.day, g.month, g.year)], g.text)
                        quote = text[g.start:kw.end] + ")"
                if z is None:
                    continue
                ok, explanation = week_fits(kw, z, yc.ref.year)
                if not ok:
                    week_wrong.append((quote.strip(" ,;:"), explanation, where))
        if dates_from:
            for f in found:
                d = f.with_year(f.year) if f.year else None
                sentence = _sentence(text, f.start, f.end)
                if d and d < dates_from and not NOT_A_DEADLINE.search(f"{before} {text[:f.start]}") \
                        and not where.startswith(_TITLE) and not PAST_TENSE.search(sentence):
                    # the start of a range that ends after dates_from is a running period, not a past deadline
                    following = [g for g in found if g.start > f.end and re.fullmatch(r"\s*(?:-|bis)\s*",
                                                                                       text[f.end:g.start])]
                    if following and (e := yc.date(following[0])) and e >= dates_from:
                        continue
                    past.append((f.text, "", where))
            for kw in week_mentions(text, ctx.today):
                if kw.year_a and (span := week_range(kw.b, kw.b, kw.year_b or kw.year_a)) and span[1] < dates_from \
                        and not NOT_A_DEADLINE.search(text[:kw.start]) \
                        and not PAST_TENSE.search(_sentence(text, kw.start, kw.end)):
                    past.append((kw.text, "", where))
        with_weekday = {f.start for _, f, _ in weekday_pairs(text)} if ctx.enabled("weekend") else set()
        for f in found:
            d = yc.date(f)
            if ctx.enabled("weekend") and d and d.weekday() >= 5 and f.start not in with_weekday and d not in given \
                    and DEADLINE_BEFORE.search(text[:f.start]) \
                    and not WEEKEND_OK.search(_sentence(text, f.start, f.end)) \
                    and not VALID_BEFORE.search(text[:f.start]) \
                    and not _in_period(text, f, found) and not where.startswith(_TITLE):
                weekend.append((f.text, _is_a(d), where))
            yc.see(f)
    # Table columns with deadlines/appointments: a cell with only a date on a weekend.
    if ctx.enabled("weekend"):
        for table in doc.tables:
            if len(table.rows) < 2:
                continue
            header = [norm(c or "").strip() for c in table.rows[0]]
            for col, name in enumerate(header):
                if not DEADLINE_HEADER.search(name) or NOT_DEADLINE_HEADER.search(name):
                    continue
                for r, row in enumerate(table.rows[1:], 2):
                    cell = norm(row[col] if col < len(row) and row[col] else "").strip()
                    f = _only_date(cell)
                    if f is None or WEEKEND_OK.search(" ".join(c or "" for c in row)):
                        continue
                    d = f.with_year(f.year) if f.year else yc.date(f)
                    if d and d.weekday() >= 5 and d not in given:
                        weekend.append((f.text, _is_a(d), f"{table.where}, row {r}, column „{name[:25]}“"))
    # Table rows: a cell with only a weekday next to a cell with only a date; calendar weeks of the row (KW column,
    # cell with only 'KW 44', 'KW 44' in the text of a cell) against the cells with only a date.
    for table in doc.tables:
        header, seen_dates = [], False  # header: the last row with two filled cells and no date before the data
        for r, row in enumerate(table.rows, 1):
            cells = [norm(c or "").strip() for c in row]
            dates = [f for c in cells if (f := _only_date(c))]
            if not dates:
                if not seen_dates and sum(1 for c in cells if c) >= 2:
                    header = cells
                continue
            seen_dates = True
            where = f"{table.where}, row {r}"
            wds = [w for c in cells if (w := _only_weekday(c)) is not None]
            f = dates[0]
            if ctx.enabled("weekday") and len(dates) == 1 and len(wds) == 1 and f.year \
                    and (d := f.with_year(f.year)) and d.weekday() != wds[0]:
                wrong_hard.append((f"{WEEKDAYS[wds[0]]} | {f.text}", _is_a(d), where))
            if ctx.enabled("calendar_week"):
                kws, in_text = _row_weeks(cells, header, ctx.today)
                if in_text:  # a week in running text only against start/end dates, not deadlines or plan dates
                    dates = [f for i, c in enumerate(cells) if i < len(header) and PERIOD_HEADER.search(header[i])
                             and not NOT_PERIOD_HEADER.search(header[i]) and (f := _only_date(c))]
                span = dates[0].text if len(dates) == 1 else f"{dates[0].text} … {dates[-1].text}" if dates else ""
                for kw in kws if dates else []:
                    ok, explanation = _week_overlaps(kw, dates, ctx.today.year)
                    if not ok:
                        week_wrong.append((f"{kw.text} | {span}", explanation, where))
    if wrong_hard:
        ctx.report("weekday", f"weekday does not match the date: {_examples(wrong_hard)}")
    if wrong_soft:
        ctx.report("weekday", f"weekday does not match the date (year inferred): {_examples(wrong_soft)}",
                   severity=SOFT)
    if week_wrong:
        ctx.report("calendar_week", f"calendar week does not match: {_examples(week_wrong)}")
    if weekend:
        ctx.report("weekend", f"deadline or appointment on a weekend: {_examples(weekend)}"
                              + (f" ({len(weekend)}×)" if len(weekend) > 1 else ""))
    if past:
        ctx.report("past_dates", f"dates before {_fmt(dates_from)}: {_examples(past)}"
                                 + (f" ({len(past)}×)" if len(past) > 1 else ""))
    return {}


__all__ = ["check_dates", "dates_in", "weekday_pairs", "week_mentions", "week_fits", "period_at_start"]
