"""Calculations written as text (text_arithmetic): '80 × 8 € × 12 = 7.680 €', 'a + b = c', a product with € in a
table cell next to its amount ('0,2 PT/Woche × 48 × 85 EUR | 4.080'), and total rows of Word/slide tables
('Gesamt' = sum of the amounts above). German number formats; ranges like '15–30 €' are skipped (except in
total rows, where low and high ends are added separately)."""
import ast
import itertools
import operator
import re
from dataclasses import dataclass

from .core import Context, Document, Table
from .util import norm, normalize, short

TOKEN = re.compile(r"(?P<number>\d(?:[\d.,']*\d)?)|(?P<op>[×*·+/÷=≈]|(?<![\w])(?:x|à|mal)(?![\w])|(?<=\s)-(?=\s))"
                   r"|(?P<word>[^\s\d×*·+/÷=≈]+)")
TIMES = {"×", "*", "·", "x", "à", "mal"}
PYOP = {"×": "*", "*": "*", "·": "*", "x": "*", "à": "*", "mal": "*", "+": "+", "-": "-", "/": "/", "÷": "/"}
CURRENCY = re.compile(r"€|\bEUR\b|\bEuro\b|T€|k€|TEUR", re.I)
APPROX = re.compile(r"\b(?:ca|rund|etwa|ungefähr|circa)\b|~|≈", re.I)
SCALE = [(re.compile(r"^(?:T€|TEUR|Tsd\.?|k€|Tausend)", re.I), 1000.0),
         (re.compile(r"^(?:Mio\.?|Millionen)", re.I), 1e6)]
FILLER = re.compile(r"^(?:ca\.?|je|rund|etwa|circa|ungefähr|\(|~|Ø)$", re.I)
# Units that need a conversion the text does not write down (8 min × 65 €/h): such products are not checked.
CONVERSION = re.compile(r"\bmin\b|\bMin\.|Minute|Sekunde|\bsek\b", re.I)

# 'Summe', 'Gesamtkosten …' at the start of the label, or '… gesamt' / '… insgesamt' at its end after a word
# ('Investitionsbudget gesamt', 'Kosten (insgesamt)'; not 'SW-Seiten (288.000 gesamt)')
TOTAL_ROW = re.compile(r"^\s*(?:summe|gesamt|gesamtsumme|gesamtkosten|gesamtbetrag|total|zwischensumme|"
                       r"netto-?summe|endsumme|insgesamt)(?:\b|$)"
                       r"|^.*?(?:[^\W\d]\s+(?:ins)?gesamt|\((?:ins)?gesamt\))\s*:?\s*$", re.I)
AMOUNT = re.compile(r"^\s*(?:ca\.?\s*|rund\s+|etwa\s+|~\s*)?(?P<a>\d[\d.,']*)\s*"
                    r"(?:(?:-|bis)\s*(?P<b>\d[\d.,']*))?\s*(?P<unit>T€|TEUR|Tsd\.?\s*€?|k€|Mio\.?\s*€?|€|EUR|Euro)?\s*"
                    r"(?:/\s*\w+\.?)?\s*(?:\(.*\))?\s*$", re.I)
MONEY_HEADER = re.compile(r"€|\beur\b|euro|kosten|betrag|preis|summe|gesamt|budget|netto|brutto|ausgab|einnahm|jahr\b|"
                          r"einmalig|jährlich|laufend", re.I)


def time_factors(text: str) -> tuple:
    """A monthly or weekly rate next to a yearly amount is fine: '8 × 65 € pro Monat | 6.240'."""
    if re.search(r"woche|wöchentl", text, re.I):
        return (1, 44, 45, 46, 47, 48, 50, 52)
    if re.search(r"monat|mtl", text, re.I):
        return (1, 12)
    return (1,)


def number_values(s: str) -> list[float]:
    """Readings of a number written in German (or English) format; [] if it is no number (date, version ...)."""
    s = s.replace("'", "")
    if re.fullmatch(r"\d+", s):
        return [float(s)]
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", s):
        return [float(s.replace(".", "").replace(",", "."))]
    if re.fullmatch(r"\d{1,3},\d{3}", s):  # 7,680: German 7.68 or English 7680
        return [float(s.replace(",", ".")), float(s.replace(",", ""))]
    if re.fullmatch(r"\d+,\d+", s):
        return [float(s.replace(",", "."))]
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", s):
        return [float(s.replace(",", ""))]
    if re.fullmatch(r"\d+\.\d+", s):
        return [float(s)]
    return []


NUMBER = re.compile(r"(?<![\w.,])([-−]?)(\d(?:[\d.,']*\d)?)")
NUMERAL = re.compile(r"\d+(?:[.,']\d+)*")  # counts the numbers of a table cell


def numbers_in_text(text: str) -> list[float]:
    """All numbers of a text in their German (or English) readings, '−1.200' negative, '15-30' as 15 and 30; a list
    without spaces ('45,78,130') is split at the commas. Dates and versions are no numbers."""
    out = []
    for m in NUMBER.finditer(text or ""):
        values = number_values(m.group(2)) or [x for part in m.group(2).split(",") for x in number_values(part)]
        out += [-x for x in values] if m.group(1) else values
    return out


def format_number(x: float) -> str:
    """German format: 7.680 / 2.558,15 / 0,125 (shares keep up to four decimals)."""
    if abs(x - round(x)) < 1e-9:
        return f"{round(x):,}".replace(",", ".")
    if abs(x) < 1:
        text = f"{x:.4f}".rstrip("0")
        return text.replace(".", ",")
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@dataclass
class Tok:
    kind: str
    text: str
    start: int
    end: int
    values: tuple = ()


def tokens(text: str) -> list[Tok]:
    out = []
    for m in TOKEN.finditer(text):
        kind = m.lastgroup
        t = Tok(kind, m.group(0), m.start(), m.end())
        if kind == "number":
            t.values = tuple(number_values(t.text))
            if not t.values:
                t.kind = "word"
        out.append(t)
    # numbers of a range (15-30, 300 bis 400) are no operands
    for i in range(len(out) - 2):
        a, middle, b = out[i], out[i + 1], out[i + 2]
        if a.kind in ("number", "range") and b.kind == "number" and (
                middle.text == "bis" or (middle.text == "-" and middle.kind == "word" and a.end == middle.start
                                         and middle.end == b.start)):
            a.kind = b.kind = "range"
    return out


def _scale(units: list[Tok]) -> float:
    f = 1.0
    for u in units[:1]:
        for rx, value in SCALE:
            if rx.match(u.text):
                f *= value
        if u.text.startswith("%"):
            f /= 100
    return f


@dataclass
class Expression:
    text: str
    ops: list
    values: list  # list of tuples of readings per operand
    rhs: tuple | None  # readings of the right-hand side after = / ≈
    approx: bool
    currency: bool
    end: int
    decimals: int = 0  # most decimal places of a number written in the calculation

    def results(self) -> list[float]:
        out = []
        for combo in itertools.islice(itertools.product(*self.values), 32):
            expr = " ".join(f"{PYOP[op]} {w!r}" if op else repr(w)
                            for op, w in zip([None] + self.ops, combo, strict=True))
            try:
                out.append(evaluate(ast.parse(expr, mode="eval").body))
            except (ZeroDivisionError, ValueError, SyntaxError):
                continue
        return out


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def evaluate(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](evaluate(node.left), evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -evaluate(node.operand)
    raise ValueError("not an arithmetic expression")


def expressions(text: str) -> list[Expression]:
    """Calculations in one line: operand (unit words) (operator operand (unit words))* [= or ≈ result]."""
    text = norm(text)
    ts = tokens(text)
    out, i = [], 0

    def skip_units(j: int) -> int:
        """Skip up to four unit words after a number ('Personentage', 'EUR/Monat', 'PT/Woche')."""
        n = 0
        while j < len(ts) and n < 4:
            if ts[j].kind == "word" and not re.fullmatch(r"(?:und|oder|bzw\.?|bis|von)", ts[j].text):
                j += 1
            elif ts[j].text == "/" and j + 1 < len(ts) and ts[j + 1].kind == "word":
                j += 2
            else:
                break
            n += 1
        return j

    while i < len(ts):
        if ts[i].kind != "number":
            i += 1
            continue
        start = ts[i].start
        values, ops, currency, decimals = [], [], False, 0
        j = i
        while True:
            decimals = max(decimals, decimal_places(ts[j].text))
            e0 = j + 1
            e1 = skip_units(e0)
            unit = ts[e0:e1]
            currency = currency or any(CURRENCY.search(u.text) for u in unit)
            values.append(tuple(w * _scale(unit) for w in ts[j].values))
            if e1 < len(ts) and ts[e1].kind == "op" and ts[e1].text not in ("=", "≈"):
                k = e1 + 1
                while k < len(ts) and ts[k].kind == "word" and FILLER.match(ts[k].text):
                    k += 1
                if k < len(ts) and ts[k].kind == "number":
                    ops.append(ts[e1].text)
                    j = k
                    continue
            break
        end, rhs = ts[e1 - 1].end if e1 > 0 else ts[j].end, None
        if ops and e1 < len(ts) and ts[e1].text in ("=", "≈"):
            k = e1 + 1
            while k < len(ts) and ts[k].kind == "word" and FILLER.match(ts[k].text):
                k += 1
            if k < len(ts) and ts[k].kind == "number":
                r1 = skip_units(k + 1)
                rhs = tuple(w * _scale(ts[k + 1:r1]) for w in ts[k].values)
                decimals = max(decimals, decimal_places(ts[k].text))
                currency = currency or any(CURRENCY.search(u.text) for u in ts[k + 1:r1])
                end = ts[r1 - 1].end
        if ops:
            quote = text[start:end].strip(" ,;:(")
            if quote.count(")") > quote.count("("):
                quote = quote.rstrip(")")
            out.append(Expression(quote, ops, values, rhs, bool(APPROX.search(text[max(0, start - 6):end])),
                                  currency, end, decimals))
            i = j + 1
        else:
            i += 1
    return out


def amount(cell: str) -> tuple[float, float] | None:
    """(low, high) of an amount cell like '1.200 €', '23.000 – 39.000', 'ca. 43.700 EUR', '9.750 (intern)';
    (0, 0) for an empty or dash cell; None for text."""
    z = normalize(cell or "").strip()
    if z in ("", "-", "--", "0", "—"):
        return (0.0, 0.0)
    m = AMOUNT.match(z)
    if not m:
        return None
    a = number_values(m["a"])
    b = number_values(m["b"]) if m["b"] else a
    if not a or not b:
        return None
    f = 1000.0 if m["unit"] and re.match(r"T|k", m["unit"]) else 1e6 if m["unit"] and m["unit"][:1] == "M" else 1.0
    return a[0] * f, b[0] * f


def decimal_places(number: str) -> int:
    """Decimal places of a written number ('5,25' -> 2, '1.200' -> 0, '8.5' -> 1)."""
    if m := re.search(r",(\d+)$", number):
        return len(m[1])
    return len(m[1]) if (m := re.fullmatch(r"\d+\.(\d{1,2})", number)) else 0


def close(a: float, b: float, approx: bool = False, decimals: int = 0) -> bool:
    """b is a + rounding: 0.5 % (5 % with 'ca.'), at least half a unit of the finest written precision ('4 × 8,5 h +
    5,25 h = 39 h' is wrong: the operands have two decimals, the result 39,25 is no rounding of 39)."""
    tolerance = max(0.51 * (1 if approx else 10 ** -decimals), abs(b) * (0.05 if approx else 0.005))
    return abs(a - b) <= tolerance


def check_text_arithmetic(doc: Document, ctx: Context) -> dict:
    """text_arithmetic over paragraphs/cells, table rows (product with € next to its amount) and total rows."""
    if not ctx.enabled("text_arithmetic"):
        return {}
    wrong = []
    for where, paragraph in doc.paragraphs:
        for a in expressions(paragraph):
            if a.rhs is None:
                continue
            results = a.results()
            factors = time_factors(a.text)
            if results and not CONVERSION.search(a.text) and not any(
                    close(e * f, r, a.approx, a.decimals) for e in results for r in a.rhs for f in factors):
                wrong.append(f"„{short(a.text)}“ gives {format_number(results[0])} ({where})")
    for tab in doc.tables:
        if not tab.calc:
            continue
        for r, row in enumerate(tab.rows, 1):
            for c, cell in enumerate(row):
                for a in expressions(cell or ""):
                    if a.rhs is not None or not a.currency or not set(a.ops) <= TIMES or CONVERSION.search(a.text):
                        continue
                    # the product must be the whole calculation of the cell ('…, davon 18 %' is not)
                    if len(NUMERAL.findall(normalize(cell))) != len(NUMERAL.findall(a.text)):
                        continue
                    candidates = [b for cc, z in enumerate(row) if cc != c and (b := amount(z)) and b != (0.0, 0.0)
                                  and b[0] == b[1]]
                    results = a.results()
                    if not candidates or not results:
                        continue
                    factors = time_factors(cell)  # '80 Nutzer à 8 € pro Monat | 7.680' is fine
                    if not any(close(e * f, b[0], a.approx) for e in results for b in candidates for f in factors):
                        stated = " / ".join(format_number(b[0]) for b in candidates[:3])
                        wrong.append(f"„{short(a.text)}“ gives {format_number(results[0])}, the row says "
                                     f"{stated} ({tab.where}, row {r})")
                    break
        wrong += table_sums(tab)
    if wrong:
        ctx.report("text_arithmetic", "calculation does not add up: " + "; ".join(wrong[:3])
                   + (f" and {len(wrong) - 3} more" if len(wrong) > 3 else ""))
    return {}


def table_sums(tab: Table) -> list[str]:
    """Total rows ('Summe', 'Gesamt …') of a Word/slide table whose amount differs from the sum of the amounts above
    (rows since the last total, all rows above, or the last total plus the rows in between)."""
    rows = tab.rows
    if len(rows) < 4:
        return []
    width = max(len(z) for z in rows)
    if width == 0:
        return []
    header = [(rows[0][c] if c < len(rows[0]) else "") or "" for c in range(width)]
    rows = [list(z) + [""] * (width - len(z)) for z in rows]  # rows without cells or shorter rows
    totals = [r for r in range(1, len(rows))
              if (lab := next((z for z in rows[r] if (z or "").strip()), "")) and TOTAL_ROW.match(lab)]
    wrong = []
    for c in range(1, width):
        cells = [(rows[r][c] if c < len(rows[r]) else "") or "" for r in range(len(rows))]
        money = bool(MONEY_HEADER.search(header[c])) or sum(bool(CURRENCY.search(z)) for z in cells[1:]) >= 2
        if not money:
            continue
        last = 0
        for r in totals:
            target = amount(cells[r])
            if target is None or target == (0.0, 0.0):
                last = r
                continue
            between = [x for x in range(last + 1, r) if x not in totals]
            if last and not between:
                last = r
                continue  # right after another total: a figure of its own ('Gesamtkosten Jahr 2'), not a sum
            above = [x for x in range(1, r) if x not in totals]
            readings = [between, above] + ([[last] + between] if last else [])
            # a subtotal of the rows right above ('Monatliche Kosten gesamt' under one-off and monthly rows) may
            # match, but is no reading of its own for the report
            subtotals = [between[i:] for i in range(1, len(between) - 1)]
            fits, computed = False, None
            for n, row_nrs in enumerate(readings + subtotals):
                if any(not (rows[x][0] or "").strip() for x in row_nrs):
                    continue  # rows without a label are alternatives or continuations, not summands
                values = [amount(cells[x]) for x in row_nrs]
                if None in values or sum(1 for w in values if w != (0.0, 0.0)) < 2:
                    continue
                lo, hi = sum(w[0] for w in values), sum(w[1] for w in values)
                approx = any(APPROX.search(cells[x]) for x in row_nrs + [r])
                if n < len(readings):
                    computed = computed or (lo, hi)
                if close(lo, target[0], approx) and close(hi, target[1], approx):
                    fits = True
                    break
            if computed and not fits:
                expected = format_number(computed[0]) + (f"–{format_number(computed[1])}"
                                                          if computed[1] != computed[0] else "")
                wrong.append(f"„{short(rows[r][0] or 'total', 40)}“ = {short(cells[r].strip(), 30)}, "
                             f"the rows above add up to {expected} ({tab.where}, row {r + 1})")
            last = r
    return wrong
