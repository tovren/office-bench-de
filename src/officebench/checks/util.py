"""Small helpers shared by the checks: dash and space normalisation, shortening of quotes, month names."""

import re

DASH = re.compile(r"[‐‑‒–—−]")  # hyphen, non-breaking hyphen, figure dash, en dash, em dash, minus
SPACE = re.compile("[\u00a0\u2009\u202f]")  # no-break, thin and narrow no-break space
MONTH_NAMES = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
               "November", "Dezember"]


def normalize(text: str) -> str:
    """All dash variants become '-' (patterns then need only one kind)."""
    return DASH.sub("-", text)


def norm(text: str) -> str:
    """Like normalize, and no-break or thin spaces become ' ' (for the date patterns)."""
    return SPACE.sub(" ", normalize(text))


def short(s: str, n: int = 60) -> str:
    """s shortened to n characters, ending in '…'."""
    return s if len(s) <= n else s[:n - 1] + "…"
