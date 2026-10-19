"""numbers_sourced: numbers, times and dates in the file that are neither in the messages nor in the attachments of
the task and do not simply follow from them. A heuristic (soft) for invented numbers in tasks that bring given notes
or data into a document.

Source: the text of all user messages and attachments. Supported is
- a number that is in the source or follows within one paragraph of the source: sum of a selection of the numbers,
  sum, difference, product, quotient and "a % of b" of two numbers, × and ÷ 12 or 100; a number with % also as the
  share a/b or the change (b − a)/a in percent. Compared at the precision it is written in (4 % fits 4,23 %), with
  "Mio"/"Tsd." after it also in euros (1,48 Mio = 1.480.000) and exactly as a multiple (480.000 = 480 from
  "in Tausend Euro");
- a number that follows in the same way from supported numbers of the file: sum of a run of numbers of a table
  column, pair of a supported number of the same location (paragraph, table row, slide, row of a sheet) and a
  supported or given number; with decimals also a pair with a column sum or of two supported numbers of the whole
  file (repeated as long as something is added: 480 and 576 -> +96 -> +20 %);
- a time from the source (also "10 Uhr" as 10:00);
- a date from the source, the reference date ± 14 days (yesterday, by Friday, next Monday), a date of the source or
  the reference date plus/minus a number of the source in days (± 1 day for the counting convention), first and last
  day of the months mentioned, the days of a calendar week mentioned. Dates without a year: day and month.
Not checked: integers up to 12 (enumerations, slides, months), years, calendar weeks, formula cells (xlsx).
"""
import bisect
import itertools
import re
from datetime import date, timedelta
from functools import lru_cache

from .arithmetic import format_number
from .core import Context, Document
from .dates import MONTH_RX, YearContext, dates_in, month_number, week_mentions, week_range
from .util import norm, short

SMALL = 12  # integers up to this are not checked
TIME = re.compile(r"(?<![\d.,:])(?P<h>[01]?\d|2[0-3])(?::(?P<m>[0-5]\d)(?:\s*Uhr\b)?|\.(?P<m2>[0-5]\d)\s*Uhr\b"
                  r"|\s*Uhr\b)")
NUMBER = re.compile(r"(?<![\w.,])([-−]?)(\d(?:[\d.,']*\d)?)")
# A scale word or a percent sign right after a number: '1,48 Mio €', '480 Tsd. €', '4,2 %'.
SCALE = re.compile(r"\s*(?:(?P<mio>Mio\b\.?|Millionen)|(?P<tsd>Tsd\b\.?|Tausend|T€|TEUR|k€))", re.I)
PERCENT = re.compile(r"\s*(?:%|Prozent)", re.I)
CONSTANTS = (12.0, 100.0)
DAYS_AROUND_TODAY = 14
SUBSETS_UP_TO = 12  # up to so many numbers in a source paragraph: sums of every selection, else of runs
DOCUMENT_PAIRS_UP_TO = 150  # pairs over the whole document only up to so many supported numbers
COLUMN_UP_TO = 60  # sums of runs only in columns with up to so many numbers


def readings(token: str) -> list[tuple[float, int]]:
    """(value, decimals as written) for each reading of a number in German or English format (like
    arithmetic.number_values); [] for no number (version, date)."""
    s = token.replace("'", "")
    if re.fullmatch(r"\d+", s):
        return [(float(s), 0)]
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", s):
        whole, _, frac = s.partition(",")
        return [(float(whole.replace(".", "") + "." + (frac or "0")), len(frac))]
    if re.fullmatch(r"\d{1,3},\d{3}", s):
        return [(float(s.replace(",", ".")), 3), (float(s.replace(",", "")), 0)]
    if re.fullmatch(r"\d+,\d+", s):
        return [(float(s.replace(",", ".")), len(s.split(",")[1]))]
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", s):
        whole, _, frac = s.partition(".")
        return [(float(whole.replace(",", "") + "." + (frac or "0")), len(frac))]
    if re.fullmatch(r"\d+\.\d+", s):
        return [(float(s), len(s.split(".")[1]))]
    return []


def decimal_places(x: float) -> int:
    text = f"{abs(x):.6f}".rstrip("0")
    return len(text.split(".")[1]) if "." in text else 0


def _is_year(f) -> bool:
    return bool(re.fullmatch(r"(?:19|20)\d\d", f.text.lstrip("-−"))) and 1990 <= f.values[0][0] <= 2100


def _ignored(f) -> bool:
    """Small integers (lists, slides, months) and years are not checked."""
    return any(n == 0 and 0 <= w <= SMALL for w, n in f.values) or _is_year(f)


class Hit:
    """A number, time or date in a text unit; scale: factor of a scale word after the number (Mio, Tsd.); percent:
    written with %."""
    __slots__ = ("kind", "text", "values", "time", "date", "where", "scale", "percent")

    def __init__(self, kind, text, where, values=(), time=None, date=None, scale=1.0, percent=False):
        self.kind, self.text, self.where, self.values = kind, text, where, list(values)
        self.time, self.date, self.scale, self.percent = time, date, scale, percent

    def both(self) -> list[float]:
        """The values, also with the scale word applied (480 Tsd. -> 480 and 480.000)."""
        return [abs(w) * s for w, _ in self.values for s in dict.fromkeys((1.0, self.scale))]


def hits_in_text(text: str, where: str, yc: YearContext | None, today: date) -> list[Hit]:
    """Numbers, times and dates of one text unit; dates and calendar weeks are masked before numbers are read.
    yc: year context for dates without a year (then date = (date, has year)); None keeps (day, month, year)."""
    text = norm(text)
    mask = list(text)
    out = []

    def blank(a, e):
        mask[a:e] = " " * (e - a)

    for f in dates_in(text):
        blank(f.start, f.end)
        if yc is not None:
            d = yc.date(f)
            yc.see(f)
            out.append(Hit("date", f.text, where, date=(d, f.year is not None) if d else None))
        else:
            out.append(Hit("date", f.text, where, date=(f.day, f.month, f.year)))
    for kw in week_mentions(text, today):
        blank(kw.start, kw.end)
    rest = "".join(mask)
    for m in TIME.finditer(rest):
        out.append(Hit("time", m.group(0).strip(), where, time=(int(m["h"]), int(m["m"] or m["m2"] or 0))))
        blank(m.start(), m.end())
    rest = "".join(mask)
    for m in NUMBER.finditer(rest):
        values = readings(m.group(2)) or [x for part in m.group(2).split(",") for x in readings(part)]
        if not values:
            continue
        sk = SCALE.match(rest, m.end())
        scale = 1e6 if sk and sk["mio"] else 1e3 if sk and sk["tsd"] else 1.0
        out.append(Hit("number", m.group(0), where, values=values, scale=scale,
                       percent=bool(PERCENT.match(rest, m.end()))))
    return out


# --------------------------------------------------------------------------------------- derivations --

def _pair_values(a: float, b: float) -> tuple[list[float], list[float]]:
    """(amounts, percentages) that follow from two numbers."""
    amounts = [a + b, abs(a - b), a * b, a * b / 100]
    percents = []
    if b:
        amounts.append(a / b)
        percents += [100 * a / b, 100 * (a - b) / b]
    if a:
        amounts.append(b / a)
        percents += [100 * b / a, 100 * (b - a) / a]
    return amounts, percents


def _pairs(a_list, b_list) -> tuple[list[float], list[float]]:
    """Sorted (amounts, amounts and percentages) from one number of each list and from the constants."""
    amounts, percents = set(), set()
    for a in a_list:
        for b in b_list:
            if a is b:
                continue
            x, p = _pair_values(a, b)
            amounts.update(map(abs, x))
            percents.update(map(abs, p))
        amounts.update(abs(a * c) for c in CONSTANTS)
        amounts.update(abs(a / c) for c in CONSTANTS)
    return sorted(amounts), sorted(amounts | percents)


def _subset_sums(numbers: list[float]) -> set[float]:
    big = [x for x in numbers if not (x == int(x) and x <= SMALL)]
    if len(big) <= SUBSETS_UP_TO:
        return {sum(t) for n in range(2, len(big) + 1) for t in itertools.combinations(big, n)}
    return {sum(big[i:j]) for i in range(len(big)) for j in range(i + 2, len(big) + 1)}


class Source:
    """What the task gives: numbers (as given, with derived amounts, with derived percentages), times, dates."""

    def __init__(self, texts: tuple, today: date):
        self.today = today
        self.times: set[tuple] = set()
        self.dates: set[date] = {today}
        yc = YearContext(today)
        given, amounts, percents, integers = set(), set(), set(), set()
        months = {(today.year, today.month)}
        for text in texts:
            for paragraph in re.split(r"\n\s*\n", text):
                values = []
                for f in hits_in_text(paragraph, "", yc, today):
                    if f.kind == "number" and not _is_year(f):
                        values += f.both()
                    elif f.kind == "time":
                        self.times.add(f.time)
                    elif f.kind == "date" and f.date:
                        self.dates.add(f.date[0])
                        months.add((f.date[0].year, f.date[0].month))
                values = list(dict.fromkeys(values))
                given.update(values)
                b, p = _pairs(values, values)
                amounts.update(b)
                percents.update(p)
                amounts.update(_subset_sums(values))
                integers.update(int(w) for w in values if w == int(w) and 0 < w <= 400)
                text_n = norm(paragraph)
                for m in MONTH_RX.finditer(text_n):
                    months.add((int(m["j"]) if m["j"] else yc.ref.year, month_number(m["m"])))
                for kw in week_mentions(text_n, today):
                    if span := week_range(kw.a, kw.b, kw.year_a or today.year, kw.year_b if kw.year_a else None):
                        start, end = span
                        self.dates.update(start + timedelta(days=i) for i in range((end - start).days + 1))
        self.times.update((int(w), 0) for w in given if w == int(w) and 0 <= w <= 23)
        for d in set(self.dates):
            for n in integers | {0}:
                for t in (n - 1, n, n + 1):
                    self.dates.update((d + timedelta(days=t), d - timedelta(days=t)))
        self.dates.update(today + timedelta(days=i) for i in range(-DAYS_AROUND_TODAY, DAYS_AROUND_TODAY + 1))
        for year, month in list(months):
            for y, mo in ((year, month), (year + (month == 12), month % 12 + 1)):
                self.dates.add(date(y, mo, 1))
                self.dates.add(date(y + (mo == 12), mo % 12 + 1, 1) - timedelta(days=1))
        self.days_months = {(d.day, d.month) for d in self.dates}
        self.given = sorted(map(abs, given))
        self.amounts = sorted(given | amounts)
        self.percents = sorted(given | amounts | percents)


@lru_cache(maxsize=64)
def source(texts: tuple, today: date) -> Source:
    return Source(texts, today)


def source_texts(task) -> tuple:
    """Messages and attached texts of a task (attachments first, as the runner sends them)."""
    out = []
    for turn in getattr(task, "turns", ()) or ():
        out += [a.text for a in getattr(turn, "attachments", ()) or ()]
        out.append(getattr(turn, "text", "") or "")
    return tuple(out)


# -------------------------------------------------------------------------------------------- check --

def _fits(f: Hit, amounts: list[float], percents: list[float] | None = None) -> bool:
    """Is one reading of the number in the sorted list (percentages: in the second list) at its written precision?
    Also with its scale word (1,48 Mio = 1.480.000) and exactly as a multiple of a thousand or million (480.000)."""
    pool = percents if f.percent and percents is not None else amounts
    for value, decimals in f.values:
        x = abs(value)
        tolerance = 0.5 * 10 ** -decimals + 1e-9
        for target, tol in ((x, tolerance), (x * f.scale, tolerance * f.scale), (x / 1e3, tolerance / 1e3),
                            (x / 1e6, tolerance / 1e6)):
            i = bisect.bisect_left(pool, target - tol)
            if i < len(pool) and pool[i] <= target + tol:
                return True
    return False


def _date_sourced(d, q: Source) -> bool:
    day, month, year = d
    if year is None:
        return (day, month) in q.days_months
    try:
        return date(year, month, day) in q.dates
    except ValueError:
        return True


def _unit(where: str) -> str:
    """Unit of a location for derived numbers: xlsx cells by row ('Blatt!C5' -> 'Blatt!row 5'), else the location."""
    m = re.match(r"^(.*)!\$?[A-Z]{1,3}\$?(\d+)$", where)
    return f"{m.group(1)}!row {m.group(2)}" if m else where


def _constant(where: str, value: float, percent: bool) -> Hit:
    """A number cell without formula; a percent cell 0,22 reads as 22 %."""
    nk = decimal_places(value)
    if percent:
        return Hit("number", format_number(100 * value) + " %", where,
                   values=[(100 * value, max(nk - 2, 0)), (value, nk)], percent=True)
    return Hit("number", format_number(float(value)), where, values=[(float(value), nk)])


def unsourced(doc: Document, q: Source) -> list[Hit]:
    """Numbers, times and dates of the document without support in the source (see module docstring)."""
    units: dict[str, list[Hit]] = {}
    for where, text in doc.paragraphs:
        units.setdefault(_unit(where), []).extend(hits_in_text(text, where, None, q.today))
    for where, value, percent in doc.constants or ():
        units.setdefault(_unit(where), []).append(_constant(where, value, percent))
    open_ = []
    sourced: dict[str, list[float]] = {}  # unit -> supported numbers (small integers included)
    for unit, hits in units.items():
        for f in hits:
            if f.kind == "date":
                if f.date is not None and not _date_sourced(f.date, q):
                    open_.append((unit, f))
            elif f.kind == "time":
                if f.time not in q.times:
                    open_.append((unit, f))
            elif _is_year(f):
                continue
            elif _ignored(f) or _fits(f, q.amounts, q.percents):
                sourced.setdefault(unit, []).extend(f.both())
            else:
                open_.append((unit, f))
    columns = _column_sums(doc)
    changed = True
    while changed and any(f.kind == "number" for _, f in open_):
        changed = False
        everything = [x for values in sourced.values() for x in values]
        wide = _pairs(everything + q.given, everything) if len(everything) <= DOCUMENT_PAIRS_UP_TO else None
        rest = []
        for unit, f in open_:
            neighbours = sourced.get(unit, [])
            with_decimals = f.kind == "number" and max(n for _, n in f.values) >= 1  # few accidental hits with decimals
            ok = f.kind == "number" and (_fits(f, columns) or bool(neighbours) and _fits(
                f, *_pairs(neighbours, everything + q.given + (columns if with_decimals else []))) or with_decimals
                and bool(wide) and _fits(f, *wide))
            if ok:
                sourced.setdefault(unit, []).extend(f.both())
                changed = True
            else:
                rest.append((unit, f))
        open_ = rest
    return [f for _, f in open_]


def _column_sums(doc: Document) -> list[float]:
    """Sorted sums of every run of at least two consecutive numbers in a table column (total rows, subtotals)."""
    sums = set()
    for tab in doc.tables:
        columns: dict[int, list[float]] = {}
        for row in tab.rows:
            for c, cell in enumerate(row):
                values = [-f.values[0][0] if f.text.startswith(("-", "−")) else f.values[0][0]
                          for f in hits_in_text(cell or "", "", None, date(2000, 1, 1)) if f.kind == "number"]
                if len(values) == 1:
                    columns.setdefault(c, []).append(values[0])
        for values in columns.values():
            if len(values) > COLUMN_UP_TO:
                continue
            for i in range(len(values)):
                total = values[i]
                for w in values[i + 1:]:
                    total += w
                    sums.add(abs(total))
    return sorted(sums)


def check_numbers_sourced(doc: Document, ctx: Context) -> dict:
    """numbers_sourced = true: soft defect with up to five examples; metric 'unsourced_numbers' (distinct texts)."""
    q = source(source_texts(ctx.task), ctx.today)
    examples = {}
    for f in unsourced(doc, q):
        examples.setdefault(f.text.strip(), f.where)
    if examples:
        parts = [f"„{short(t, 30)}“ ({where})" for t, where in examples.items()]
        ctx.report("numbers_sourced", f"{len(examples)} numbers or dates without a source in prompt or attachment: "
                   + ", ".join(parts[:5]) + (" …" if len(parts) > 5 else ""))
    return {"unsourced_numbers": len(examples)}
