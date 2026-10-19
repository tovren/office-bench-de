"""Charts of xlsx and pptx files (DrawingML chart parts): types and data series with name and values, and the
[checks] keys on them: chart, chart_type, chart_series_min, chart_values, chart_series."""
import re
from dataclasses import dataclass, field

from .arithmetic import format_number
from .core import Context
from .util import normalize

CHART_TYPE = {"barChart": None, "bar3DChart": None, "lineChart": "line", "line3DChart": "line", "pieChart": "pie",
              "pie3DChart": "pie", "doughnutChart": "pie", "ofPieChart": "pie", "areaChart": "area",
              "area3DChart": "area", "scatterChart": "scatter", "radarChart": "radar", "bubbleChart": "bubble"}
VALUE_TOLERANCE = 0.01  # chart_values: absolute per value (after the unit factor)
SHARE_TOLERANCE = 0.006  # per share v_i / Σv when the series is a conversion (percent instead of counts)
UNIT_FACTORS = (1.0, 1000.0, 0.001)  # same unit, € instead of Tsd. € and back: then the values must match exactly


@dataclass
class Series:
    """One data series: name (series title), chart type, numbers (empty and text points left out), in xlsx the
    header cell above (or left of) the referenced values, and the category label of each number ([] if unknown)."""
    name: str
    type: str
    values: list = field(default_factory=list)
    header: str = ""
    categories: list = field(default_factory=list)

    @property
    def display(self) -> str:
        return f"„{self.name}“" if self.name else "unnamed"


@dataclass
class Chart:
    types: list  # one entry per chart type element (a combo chart has several)
    series: list  # [Series]

    @property
    def series_count(self) -> int:
        return len(self.series)


def _children(el, *names) -> list:
    """Descendants along a path of local names (any namespace prefix: openpyxl writes none, python-pptx c:)."""
    from lxml import etree

    nodes = [el]
    for name in names:
        nodes = [c for n in nodes for c in n if isinstance(c.tag, str) and etree.QName(c).localname == name]
    return nodes


def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _cache(ref) -> list:
    """Points of a strCache/numCache/numLit in index order (missing indices stay None)."""
    pts = {}
    for cache in _children(ref, "strCache") + _children(ref, "numCache") + ([ref] if _children(ref, "pt") else []):
        for pt in _children(cache, "pt"):
            try:
                pts[int(pt.get("idx", len(pts)))] = _text(next(iter(_children(pt, "v")), None))
            except ValueError:
                continue
    return [pts.get(i) for i in range(max(pts) + 1)] if pts else []


def _number(v: str | None) -> float | None:
    """Number of a cached point ('8.0'); None for empty or text points."""
    try:
        return float(v) if v else None
    except ValueError:
        return None


def _series(ser, kind: str, resolve) -> Series:
    name, header = "", ""
    for tx in _children(ser, "tx"):
        for ref in _children(tx, "strRef"):
            formula = _text(next(iter(_children(ref, "f")), None))
            found = resolve(formula) if resolve and formula else None
            if found:
                name = next((str(v).strip() for v in found[0] if v not in (None, "")), "")
            name = name or " ".join(x for x in _cache(ref) if x)
        name = name or _text(next(iter(_children(tx, "v")), None))
    points = []  # numbers in point order, None for empty and text points
    for val in _children(ser, "val") + _children(ser, "yVal"):
        for ref in _children(val, "numRef") + _children(val, "numLit"):
            formula = _text(next(iter(_children(ref, "f")), None))
            found = resolve(formula) if resolve and formula else None
            # cells as the chart shows them: text (also a number stored as text) is no point
            cells = [float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
                     for v in (found[0] if found else [])]
            if any(x is not None for x in cells):
                points, header = cells, found[1]
            else:
                points = list(map(_number, _cache(ref)))
    values = [x for x in points if x is not None]
    categories = _categories(ser, resolve)
    if len(categories) == len(points):
        categories = [c for c, x in zip(categories, points, strict=False) if x is not None]
    else:
        categories = []
    return Series(name, kind, values, header, categories)


def _categories(ser, resolve) -> list:
    """Category labels of a series in point order (text; numbers and dates as written), [] if it has none."""
    for cat in _children(ser, "cat") + _children(ser, "xVal"):
        for ref in (_children(cat, "strRef") + _children(cat, "numRef") + _children(cat, "multiLvlStrRef")
                    + _children(cat, "strLit") + _children(cat, "numLit")):
            formula = _text(next(iter(_children(ref, "f")), None))
            found = resolve(formula) if resolve and formula else None
            if found and any(v not in (None, "") for v in found[0]):
                return ["" if v is None else v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else
                        format_number(v) if isinstance(v, float) else str(v).strip() for v in found[0]]
            if ref.tag.endswith("multiLvlStrRef"):
                levels = _children(ref, "multiLvlStrCache", "lvl")
                return [x or "" for x in _cache(levels[0])] if levels else []
            points = _cache(ref)
            if points:
                return [x or "" for x in points]
    return []


def chart_info(xml: bytes | str, resolve=None) -> Chart:
    """Chart types (column, bar, line, pie, area …) and data series of one chart part.

    resolve: function formula -> ([cell values], header text) or None. xlsx resolves references like
    'Blatt 1'!$B$2:$B$7 against the recalculated sheet with it (openpyxl writes no cache); without resolve or when
    it finds nothing, the cached values count (python-pptx writes numCache/strCache)."""
    from lxml import etree

    root = etree.fromstring(xml.encode() if isinstance(xml, str) else xml)
    types, series = [], []
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        name = etree.QName(el).localname
        if name in CHART_TYPE:
            kind = CHART_TYPE[name]
            if kind is None:  # bar chart: direction col = column, bar = bar
                direction = next((c.get("val") for c in _children(el, "barDir")), "col")
                kind = "column" if direction == "col" else "bar"
            types.append(kind)
            series += [_series(ser, kind, resolve) for ser in _children(el, "ser")]
    return Chart(types, series)


def _values_text(values: list, n: int = 10) -> str:
    return "; ".join(format_number(x) for x in values[:n]) + (" …" if len(values) > n else "")


def _matches(expected: list, values: list) -> bool:
    """Same values in the same order, also in Tsd. or as € instead of Tsd. €; or a conversion such as percent instead
    of counts: every share v_i / Σv within SHARE_TOLERANCE (rounded percentages still pass). A series in the same
    unit with one value off (131 instead of 130) does not pass."""
    if len(expected) != len(values):
        return False
    if all(abs(x - y) <= VALUE_TOLERANCE for x, y in zip(expected, values, strict=False)):
        return True
    sa, sb = sum(expected), sum(values)
    if not (sa and sb):
        return False
    unit = next((g for g in UNIT_FACTORS if abs(sb / sa / g - 1) <= 0.02), None)
    if unit is not None:
        tolerance = VALUE_TOLERANCE * max(1.0, unit)
        return all(abs(y - unit * x) <= tolerance for x, y in zip(expected, values, strict=False))
    return all(abs(x / sa - y / sb) <= SHARE_TOLERANCE for x, y in zip(expected, values, strict=False))


MONTHS = {"jan": 1, "feb": 2, "mär": 3, "mae": 3, "mar": 3, "apr": 4, "mai": 5, "may": 5, "jun": 6, "jul": 7, "aug": 8,
          "sep": 9, "okt": 10, "oct": 10, "nov": 11, "dez": 12, "dec": 12}
_MONTH = re.compile(r"\b(jan(?:uar)?|feb(?:ruar)?|märz?|maerz|mar(?:ch)?|apr(?:il)?|mai|may|jun[ie]?|jul[iy]?|"
                    r"aug(?:ust)?|sep(?:t(?:ember)?)?|o[ck]t(?:ober)?|nov(?:ember)?|de[zc](?:ember)?)"
                    r"\.?(?![\w-])", re.I)
_QUARTER = re.compile(r"\bQ\s?([1-4])\b|\b([1-4])\.\s?Quartal|\bQuartal\s?([1-4])\b", re.I)
_HALF_YEAR = re.compile(r"\bH([12])\b|\b([12])\.\s?Halbjahr", re.I)
_WEEK = re.compile(r"\bKW\s?(\d{1,2})\b", re.I)
_DATE = re.compile(r"\b(\d{4})-(\d\d)-(\d\d)\b|\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})?")


def _period_key(category) -> tuple | None:
    """Sort key of a category that names a period (Q1 2026, Januar, 2025, KW 42, 2026-10-01), else None."""
    t = normalize(str(category or ""))
    if not t.strip():
        return None
    if m := _DATE.search(t):
        if m[1]:
            return int(m[1]) % 100, int(m[2]), int(m[3])
        if 1 <= int(m[5]) <= 12 and 1 <= int(m[4]) <= 31:
            return int(m[6] or 0) % 100, int(m[5]), int(m[4])
    for rx, months in ((_QUARTER, 3), (_HALF_YEAR, 6), (_MONTH, 1), (_WEEK, 0)):
        if m := rx.search(t):
            value = next(g for g in m.groups() if g)
            nr = MONTHS[value.lower()[:3]] if rx is _MONTH else int(value)
            rest = t[:m.start()] + " " + t[m.end():]
            year = re.search(r"(?<![\d.,])(?:19|20)?(\d\d)(?![\d.,])", rest)
            return int(year[1]) if year else 0, nr * months if months else nr, 0
    if m := re.fullmatch(r"\D{0,12}?(?<!\d)((?:19|20)\d\d)(?!\d)\D{0,15}", t.strip()):
        return int(m[1]) % 100, 0, 0
    return None


def _equal(expected: list, series: Series) -> bool:
    """Does a series show the expected values? In order; categories that name periods (quarters, months, years) are
    put into time order first and never compared by size. Other categories may be reversed or sorted by size (a pie
    chart from the largest share); a series in any other order has swapped values."""
    values = series.values
    if len(expected) != len(values):
        return False
    if _matches(expected, values):
        return True
    time = [_period_key(c) for c in series.categories]
    if time and None not in time and len(set(time)) == len(time):
        return _matches(expected, [v for _, v in sorted(zip(time, values, strict=False))])
    if _matches(expected[::-1], values):
        return True
    by_size = values == sorted(values) or values == sorted(values, reverse=True)
    return by_size and _matches(sorted(expected), sorted(values))


def _distance(expected: list, values: list) -> float:
    """How far a series is from the expected numbers (for naming the most similar one)."""
    if not values:
        return float("inf")
    sa, sb = sum(map(abs, expected)) or 1.0, sum(map(abs, values)) or 1.0
    shares = min(sum(abs(x / sa - y / sb) for x, y in zip(a, b, strict=False))
                 for a, b in ((expected, values), (sorted(expected), sorted(values))))
    return abs(len(expected) - len(values)) + shares


def _chart_values(charts: list, ctx: Context) -> None:
    series = [s for c in charts for s in c.series]
    for expected in ctx.checks["chart_values"]:
        expected = [float(x) for x in expected]
        if any(_equal(expected, s) for s in series):
            continue
        similar = min(series, key=lambda s: _distance(expected, s.values), default=None)
        found = (f"most similar series {similar.display}: {_values_text(similar.values)}"
                 if similar and similar.values else "no series with numbers found")
        ctx.report("chart_values", f"no chart series with the values {_values_text(expected, 12)} ({found})")


def _chart_series(charts: list, allowed: list | None, ctx: Context) -> None:
    series = [s for c in charts for s in c.series]
    for pattern in ctx.checks["chart_series"]:
        hits = [s for s in series if any(t and re.search(pattern, normalize(t), re.I) for t in (s.name, s.header))]
        if any(not allowed or s.type in allowed for s in hits):
            continue
        if hits:
            text = (f"chart series „{pattern}“ only in a chart of type {', '.join(sorted({s.type for s in hits}))} "
                    f"(expected {' or '.join(allowed)})")
        else:
            names = ", ".join(f"{s.display} ({s.type})" for s in series[:6]) + (" …" if len(series) > 6 else "")
            text = f"no chart series „{pattern}“ (series: {names or 'none'})"
        ctx.report("chart_series", text)


def check_charts(charts: list, ctx: Context) -> None:
    """chart, chart_type, chart_series_min, chart_values, chart_series for the [Chart] of a file. Without any chart
    only one defect (chart) is reported: every other chart key would fail for the same reason."""
    c = ctx.checks
    if not charts:
        if c.get("chart") or any(s in c for s in ("chart_type", "chart_series_min", "chart_values", "chart_series")):
            ctx.report("chart", "no chart")
        return
    allowed = None
    if "chart_type" in c:
        allowed = [c["chart_type"]] if isinstance(c["chart_type"], str) else list(c["chart_type"])
        found = sorted({t for ch in charts for t in ch.types})
        if not set(found) & set(allowed):
            ctx.report("chart_type", f"no chart of type {' or '.join(allowed)} (found: {', '.join(found) or '?'})")
    if "chart_series_min" in c:
        n = max(ch.series_count for ch in charts)
        if n < c["chart_series_min"]:
            ctx.report("chart_series_min", f"chart with only {n} data series (expected ≥ {c['chart_series_min']})")
    if "chart_values" in c:
        with ctx.guarded("chart_values"):
            _chart_values(charts, ctx)
    if "chart_series" in c:
        with ctx.guarded("chart_series"):
            _chart_series(charts, allowed, ctx)
