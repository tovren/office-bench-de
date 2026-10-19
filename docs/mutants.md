# Mutants

`tasks/<id>/mutants.toml` holds broken variants of the task's `reference.json`. Every variant carries one typical
model error, and the content check must report it. The reference solution shows that a good file raises no false
alarm; the mutants show that the checks catch real errors.

A mutant can be marked as a known gap (`gap`): the checks miss the error today. It runs as a strict xfail, so the
test fails as soon as a check does catch it; then remove `gap`.

## Format

```toml
[[mutant]]
name = "power_by_area"                      # [a-z0-9_], unique per task
defect = "electricity allocated by floor area instead of by head count"
replace = [["D{row}/SUM(D$2:D$5)", "C{row}"]]   # substring in every string of the arguments, must match
number = [[220, 250]]                       # every number equal to 220 becomes 250, must match
set = [["sheets.0.chart.type", "bar"]]      # path (dots, list indices, * = all elements) -> new value; the last
                                            # key may be new if its dict exists
remove = ["sheets.0.columns.*.total"]       # delete a key or list element; paths apply one after the other
expected = ["values_present", "total_row"]  # one of these checks must report it
severity = "hard"                           # default; "soft" = a soft defect is enough (soft checks)
gap = "reason"                              # known gap: the checks miss it (strict xfail, fails once caught)
```

| Key | Required | Meaning |
|---|---|---|
| `name` | yes | `[a-z0-9_]`, unique within the file |
| `defect` | yes | the error the variant carries, in one sentence |
| `set` | no¹ | list of `[path, value]`: the path uses dots and list indices, `*` stands for all elements of a list or all values of a dict; the last key may be new if its dict exists |
| `replace` | no¹ | list of `[old, new]`: substring replacement in every string of the arguments; each pair must match somewhere |
| `number` | no¹ | list of `[old, new]`: every number value equal to `old` becomes `new` (not digits inside strings); each pair must match somewhere |
| `remove` | no¹ | list of paths (syntax as in `set`): delete the key or list element; the paths apply one after the other, so later indices see the earlier deletions |
| `expected` | yes | check names; one of them must report the defect. Allowed: keys of `[checks]`, names of general checks (`GENERAL_CHECKS`), `unreadable`, `wrong_file_type` |
| `severity` | no | `hard` (default): the reported defect must be hard; `soft`: a soft defect is enough (for soft checks) |
| `gap` | no | known gap with the reason and, ideally, how a check could catch it; the mutant then runs as a strict xfail |

¹ At least one of `set`, `replace`, `number`, `remove`. A task with `mutants.toml` needs a `reference.json`.

## Order of operations

The operations run in the order `set`, `replace`, `number`, `remove`, each on the arguments of the last call
(`arguments` in `reference.json`). A follow-up task keeps its `previous` call unchanged; only the file of the last
turn is mutated. The office tool must accept the variant, and the variant must differ from the reference.

## TOML 1.0

The files are read with `tomllib` (TOML 1.0), which allows line breaks inside arrays but not inside inline tables.
Write longer values as a multi-line array with one `[path, value]` pair per line and keep any inline table on one
line. Sub-tables of `[[mutant]]` do not work: the keys above must be lists.
