"""Order rules of chart_values (_equal): periods in time order, other categories reversed or sorted by size."""
import pytest

from officebench.checks.charts import Series, _equal


@pytest.mark.parametrize("values, categories, ok", [
    ([27, 14, 13, 7], ["Zufrieden", "Sehr zufrieden", "Teils", "Unzufrieden"], True),  # pie sorted by size
    ([7, 13, 27, 14], ["Unzufrieden", "Teils", "Zufrieden", "Sehr zufrieden"], True),  # reversed
    ([14, 27, 7, 13], ["Sehr zufrieden", "Zufrieden", "Teils", "Unzufrieden"], False),  # two values swapped
    ([14, 27, 13, 7], [], True),
    ([3980, 4210, 4650], ["Q1", "Q2", "Q3"], False),  # quarters swapped
    ([4650, 3980, 4210], ["Q3 2026", "Q2 2026", "Q1 2026"], True),  # quarters in another order, values with them
    ([4650, 3980, 4210], ["Q3 2026", "Q1 2026", "Q2 2026"], False),
    ([4210, 3980, 4650], ["Jan", "Feb", "Mär"], True),
])
def test_chart_values_order(values, categories, ok):
    expected = [14, 27, 13, 7] if len(values) == 4 else [4210, 3980, 4650]
    assert _equal([float(x) for x in expected], Series("", "pie", [float(x) for x in values], "", categories)) is ok
