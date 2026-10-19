# Task format

Every task is a folder `tasks/<id>/`. The loader (`src/officebench/tasks.py`) validates it against a strict schema:
unknown keys are an error, so a typo cannot silently switch a check off. Keys and comments are English; prompts,
attachments, patterns and judge checklists are German.

```
tasks/<id>/
  task.toml          the task: header, turns, checks, judge checklist (this document)
  attachments/       optional: extracted text of the files the user uploads, one UTF-8 file each
  reference.json     file tasks: tool arguments of a correct solution
  mutants.toml       file tasks: broken variants of reference.json that the checks must catch (docs/mutants.md)
extra_tools/<name>.json   tools offered to the model in addition to the office tool (see "Extra tools")
```

`reference.json` is the tool call of a correct solution: `{"function": "create_excel_file", "arguments": {…}}`
(`create_word_file`, `create_excel_file` or `create_powerpoint_file`, matching `file_type`). Follow-up tasks add
`"previous": {"function": …, "arguments": …}`, the file of the earlier turn.

Check the task files with

```
obench tasks validate                  # all tasks; --select "budget,tag:chart" for a selection
obench tasks schema > docs/task.schema.json   # JSON schema of task.toml, for editor completion and validation
```

`--select` takes `all`, task ids, `tag:<tag>`, `type:<docx|xlsx|pptx>` and `kind:<kind>`, separated by commas.

## Header

| Key | Required | Meaning |
|---|---|---|
| `id` | yes | equal to the folder name; `[a-z][a-z0-9_]*` |
| `title` | yes | short name for reports |
| `version` | yes | integer ≥ 1; increase it on every change to the prompt, attachments or checks |
| `kind` | yes | `file` (one file is expected), `follow_up` (several user messages, the last file counts), `no_file` (no tool call expected) |
| `file_type` | with `file`/`follow_up` | `docx`, `xlsx` or `pptx`; not allowed with `no_file` |
| `difficulty` | no | `easy`, `medium`, `hard` |
| `tags` | no | free keywords for stratification, `[a-z][a-z0-9_]*`, e.g. `["table", "chart", "long", "vague", "extra_tools"]` |
| `extra_tools` | no | names from `extra_tools/<name>.json` that are sent as additional tools |
| `dates_from` | no | ISO date; appointments/deadlines in the document before this date are a defect (set only for planning tasks; see the general check `past_dates`) |

## Turns

```toml
[[turns]]
text = "Erstelle mir ein Word-Dokument: …"
expect = "file"          # file | no_file | any   (default: file for kind = file/follow_up, otherwise no_file)

[[turns]]                # only with kind = "follow_up": the next user message, after the model has finished
text = "Füg noch eine Spalte Sparquote in Prozent hinzu."
expect = "file"
```

`follow_up` needs at least two turns; the other kinds have exactly one.

**Attachments** (`attachments`, optional): files the user uploads with the message.

```toml
[[turns]]
text = "Anbei meine Notizen von der Teamrunde gestern. Mach mir daraus ein Protokoll als Word-Dokument."
attachments = [{ name = "Notizen Teamrunde 12.10.docx", file = "notizen_teamrunde.txt" }]
```

- `name`: the file name as the user uploaded it (no path, unique within the turn). `file`: a file in
  `attachments/` with the text a document loader would extract from it (UTF-8, not empty). It goes into the request
  unchanged, including blank lines and the trailing newline. Parts such as PDF pages are joined with a single space.
- Attachments are given to the model as extracted text in front of the user message (details in docs/harness.md).
- Only in tasks with **exactly one turn**.
- The attachment content is part of the task hash: every change to an attachment file gives a new hash (increase
  `version` anyway). The judge sees the attachment text below the task.

The system prompt does not come from the task but from the run profile. The reference date ("today") is also set
there and written to the log; it is Tuesday, 13 October 2026.

## Checks (`[checks]`)

They apply to the last delivered file. Every violated check produces a defect with the check name, a label and a
severity (`hard` = task not done or certainly wrong; `soft` = quality issue or uncertain heuristic). "Content ok"
means: no hard defects. "Defect-free" means: no defects at all. Which keys exist per file type, with label and
severity, is listed in `TASK_CHECKS` in `src/officebench/checks/registry.py`; the schema accepts exactly those keys
for the task's `file_type` (`no_file` tasks only the keys for all file types).

### All file types (on the whole text of the file)

| Key | Type | Meaning |
|---|---|---|
| `topics` | table name → pattern | every topic must occur. Pattern = regex (case-insensitive, hyphen variants ignored) or a list of alternatives; an alternative is a regex or `{ pattern = "…", min = 2 }` (at least that many matches, multiline) |
| `topics_soft` | like `topics` | points that belong to good work but are not explicitly asked for in the prompt (e.g. the customer name in a quote); missing is soft |
| `names` | list | these words must occur as whole words (case-sensitive) |
| `count` | list of `{ name, pattern, min, max }` | count the paragraphs/lines/cells the pattern matches (e.g. questions). Below `min`: hard, above `max`: soft |
| `words_min` | number or `{ hard = 250, soft = 500 }` | word count of the whole text; as a number hard, in two levels: below `hard` hard, below `soft` soft |
| `words_max` | number | at most this many words (soft) |
| `tables_min` | number | docx: tables; pptx: tables on slides (in both cases only tables with at least one filled row below the header) |
| `forbidden` | table name → pattern | format and matching like `topics`, but every match is a hard defect "forbidden content" (name, quote, location): points dropped in a follow-up, source markers „[1]“ from a retrieval template |
| `values_present` | list of numbers or number lists | every number is in the file (tolerance 0.005): xlsx as a cell value (stored or recalculated, also a number stored as text; percent cell 12,5 % also as 12.5), docx/pptx as a number in the text or in tables (German format), pptx also as a chart value. A list inside the list is a set of alternatives: `[[-2.5, 2.5], 7.5]` (decline „−2,5 %“ or „2,5 %“). Missing ones: one hard defect "missing value" with the first five |
| `numbers_sourced` | bool | numbers, times and dates in the file that are neither in the messages nor in the attachments and do not simply follow from them (see below): soft defect "number without source" with up to five examples, metric "numbers without source" (distinct texts). Only for tasks in which every number comes from the request |
| `retained` | share or `{ hard = 0.5, soft = 0.8 }` | follow-ups: this much of the content of the previous file is in the new one again (see below); as a number hard, in two levels like `words_min` |
| `disable` | list | general checks switched off for this task (names see below) |

```toml
[checks]
forbidden = { Parkplatz = 'parkplatz', Quellenmarker = '\[\d+\]' }
values_present = [45, 78, 130, 112]
retained = { hard = 0.6, soft = 0.85 }
```

`numbers_sourced` is a heuristic. A number is sourced if it appears in the source (messages and attachments) or
follows within one paragraph of the source (sum of a selection, sum, difference, product, quotient, „a % von b“ of
two numbers, × and ÷ 12 or 100; with % also share and change in percent), compared at the written precision (4 %
matches 4,23 %), with „Mio“/„Tsd.“ after it also in euros and exactly as a multiple (480.000 = 480). Also sourced is
what follows from sourced numbers of the file: the sum of a run in a table column, a pair with a sourced number in
the same location (paragraph, table row, slide, row of a sheet), with decimals also a pair across the whole file.
Dates: from the source, reference date ± 14 days, a date of the source or the reference date ± a number of the
source in days (± 1), first and last day of named months, days of named calendar weeks. Times: from the source (also
„10 Uhr“). Not checked: integers up to 12, years, calendar weeks, formula cells. The more numbers a paragraph of the
source has, the more small numbers and percentages count as derivable: in a sample with eleven invented figures in
the reference solutions, the check found 5 to 11; dates, times and phone numbers always.

`retained` compares with the file of the previous file turn (the file last built in an earlier turn). Units: docx
paragraphs and table cells, pptx paragraphs of shapes, table cells and notes (each line by line), xlsx cells with
text or constants (no formulas: references shift when a column is added). Normalised (lower case, whitespace
collapsed, punctuation at the edges removed); units under 3 characters and numbers up to 2 digits do not count,
equal units only once. Retained means: occurs again or is at least 90 % similar (`difflib`) to a unit of the new
file. Metric "retained" in %, the defect shows two lost units as examples; without a previous file soft "not
checkable".

### docx

| Key | Type | Meaning |
|---|---|---|
| `headings_min` | number | paragraphs with a heading style |
| `toc` | bool | TOC field present (hard); only a hand-made table of contents („Inhaltsverzeichnis“ with typed entries): soft |
| `numbered_list` | bool | at least one numbered list (style „List Number“ or numbering) |
| `numbered_headings` | bool | numbered sections: at least two paragraphs with a heading style carry a number, typed („1. Geltungsbereich“, „2.1“, „§ 3“, „IV.“, „Abschnitt 2“) or as Word numbering (also via the style, no bullets). With fewer than two headings it is not checked (`headings_min` reports that) |
| `header_contains` | text | the text must be in a page header |

### xlsx (values after recalculation with LibreOffice)

| Key | Type | Meaning |
|---|---|---|
| `sheets_min` | number | number of sheets |
| `data_rows_min` | number | data rows on the first sheet (without header and total rows) |
| `month_rows_min` | number | this many data rows **or** columns with month names in the header |
| `months` | `[from, to]` | all months from–to (1–12) occur in cells (name, abbreviation, date) |
| `dates_between` | `["YYYY-MM-DD", "YYYY-MM-DD"]` | date values in data rows lie in this range: hard in date columns (header with Datum, Kauf, Start, Ende, Termin, Frist, …tag such as Stichtag/Bereitschaftstag), soft in other columns; validity columns („Garantie bis“) and dates in running text do not count |
| `columns` | list of regexes | each must match a header cell (or row label) of a sheet |
| `formulas_min` | number | real formula cells in total |
| `total_row` | bool | SUM formula in a total row (or total column) of the first sheet; running totals (`=SUM(D$2:D3)`) do not count |
| `line_item_formula` | bool | formula with `*` or PRODUCT in the data rows of the first sheet |
| `priced_items_min` | number | data rows of the first sheet with a unit price > 0 |
| `chart` | bool | at least one chart |
| `chart_type` | text or list | `column`, `bar`, `line`, `pie`; one of them must occur |
| `chart_series_min` | number | data series in the largest chart |
| `chart_values` | list of number lists | each list is a series of some chart: same length and same values (tolerance 0.01, also × 1000 or ÷ 1000: € instead of Tsd. €) or converted (every share v/Σv equal within 0.006: percent instead of count, rounded); in the same unit a matching share is not enough, 131 instead of 130 is wrong; first in order; if the categories name periods (Q1, Juli, 2025, KW 42), ordered by them in time and never by size; otherwise also reversed or, if the series is sorted by size, both sorted (pie chart by size). Other orders count as swapped values. Values from the cells the chart points to (recalculated), otherwise from the cache |
| `chart_series` | list of regexes | each matches the name of a series (series title or the header above the values); together with `chart_type` the series itself must be of one of these types |
| `calculations` | list (see below) | recalculate values row by row (date as Excel serial number, percent as share or, with % in the header, × 100) |
| `value_ranges` | list of `{ column, min, max }` | numbers in the column (regex on the header) lie in the range |
| `sorted` | `{ column = regex, descending = true, sheet = 'kunde' }` | numbers (also dates) of the column in the data rows (without total rows) of the first sheet with this column are sorted, equal values allowed; `descending` optional (default false); `sheet` optional (position from 1 or regex on the sheet name) limits the search to these sheets; if several columns match, one is enough |
| `groups` | list (see below) | a summary per group on one sheet matches the list on another (count, sum) |
| `column_format` | table regex → `"percent"`, `"date"` or `"euro"` | the values of the data rows in columns with a matching header (otherwise in rows with a matching label, transposed table) have this number format; numbers and dates stored as text count as wrong, notes such as „laufend“ do not. Soft defect "wrong number format" with share and example; no matching column: soft "not checkable" |
| `workdays` | `true` or `"BW"` | dates in the data rows are not on Saturday/Sunday, with `"BW"` also not on public holidays in Baden-Württemberg (Easter calculated). Counted are date cells and, in columns with a date in the header, serial numbers 2000–2099. Not: calendars with one row per day (three consecutive days across a weekend in one column; lists Monday to Friday are checked), columns such as purchase date, warranty, holiday, „Stand“, rows and sheets about days off (Feiertag, Wochenende, Betriebsurlaub; a weekday name alone in its cell does not count). Soft |

```toml
[checks]
chart_type = "line"
chart_series = ['sparquote']          # the line chart shows the savings rate, not income/expenses
chart_values = [[45, 78, 130, 112]]
sorted = { column = 'umsatz', descending = true }
```

```toml
[[checks.calculations]]
name = "Gesamtpreis = Menge × Einzelpreis"
columns = { menge = "menge|anzahl|stunden|std", preis = "^(?!.*(gesamt|summe)).*(preis|satz)", gesamt = "gesamt" }
formula = "menge * preis"     # + - * / brackets, numbers and the names from columns
result = "gesamt"             # name whose (recalculated) value is compared with the formula
tolerance = 0.01              # absolute, default 0.01
sheet = 1                     # optional: sheet (position from 1) or regex on the sheet name; otherwise all sheets
```

Columns are found via the header row; if nothing matches, via the row labels (transposed table, e.g. months as
columns). Columns not found give a soft defect "not checkable", wrong values a hard one. Total rows are only checked
where the inputs and the result are SUM formulas (not MIN/MAX/AVERAGE rows); if a sum is missing there, that is a
soft defect "total row incomplete". Percent: percent cells count as a share (12,5 % = 0.125). If the result cell has
no percent format and the header of the result column (when transposed: the row label) contains `%` or „Prozent“,
the value × 100 also counts (tolerance × 100): „Sparquote in %“ = 17,31 with `=J2/D2*100` is right, 1.731 % (percent
format and × 100) stays wrong.

```toml
[[checks.groups]]
name = "Übersicht je Gerätetyp"
source = { sheet = 1, group = 'typ|kategorie', value = 'preis|wert' }                                # value optional
target = { sheet = 2, group = 'typ|kategorie', count = 'anzahl|stück', value = 'wert|summe|gesamt' }  # count/value: at least one
```

`sheet` = position from 1 or regex on the sheet name. Source: data rows grouped by the text of the group column
(lower case, letters and digits only), rows counted, values summed. Target: data rows (without total rows) with a
group text; a row belongs to a source group if the text is equal or one, with at least 4 characters, is the start
of the other (Laptop/Laptops). Values in the target after recalculation (LibreOffice computes COUNTIF across
sheets). If several columns match, the group uses the one with the most texts, count and value the one with the
most numbers; count and value never from the group column („Gesamtwert je Typ“), the value not from the count
column. A different count (exact) or sum (tolerance max(0.01; 0.1 %)) and source groups missing in the target: one
hard defect "summary does not match" with up to three examples. Sheet or column not found: soft "not checkable".

### pptx

| Key | Type | Meaning |
|---|---|---|
| `slides` | `[min, max]` | number of slides |
| `chart`, `chart_type`, `chart_series_min`, `chart_values`, `chart_series` | like xlsx | charts on slides (values and names from the chart cache) |
| `notes_min` | number | slides whose speaker notes have at least 5 words |
| `side_by_side` | table name → pattern (like `topics`) | one slide shows two columns (two text boxes next to each other, each with at least 2 words and 15 % of the slide width, title excluded, or a table with at least two rows with two filled cells) and its text contains every topic. Soft: the shape is a heuristic, and the prompt usually only says „gegenübergestellt“ |
| `last_slide_topics` | like `topics` | every topic is in the text of the last slide (without notes); a short closing slide after it („Vielen Dank“, „Fragen?“, at most 15 words) is skipped. Soft: two closing slides or an extended existing closing slide usually fulfil the request too |
| `slides_added` | number or `[from, to]` | follow-up: this many slides more than in the file of the previous file turn. Soft (extending an existing closing slide instead of appending one usually fulfils the request too); without a previous file soft "not checkable" |

### Validation on load

`obench tasks validate` checks: `id` equal to the folder name; `kind`, `file_type` and the number of turns
consistent; attachments only with one turn, names unique per turn, files present, UTF-8 and not empty; every
`extra_tools` name has a file in `extra_tools/`; only the `[checks]` keys of the task's file type. Within the keys:
regexes in all patterns (also `value_ranges.column`, `calculations.sheet`, `chart_series`, `sorted.column`, `groups`,
`column_format`), lists for `names`/`columns`/`disable` (`disable` only with names of general checks), integers for
the `…_min`/`…_max`, number lists for `values_present` (also lists as alternatives)/`chart_values`, `retained` as a
share 0–1 or `{ hard, soft }` with hard ≤ soft (likewise `words_min`), `months`/`slides` as `[from, to]`,
`slides_added` as a number or `[from, to]`, `dates_between` as two ISO dates in ascending order, `chart_type` from
`column`/`bar`/`line`/`pie`, `calculations.formula` as an expression of `+ - * /`, brackets, numbers and the names
from `columns` (and `result` one of those names), required parts of `groups` and `target.value` only with
`source.value`, the formats of `column_format`, `workdays` as `true` or `"BW"`, `numbers_sourced` as bool.

### General checks (always on, each can be switched off with `disable`)

Maintained in `GENERAL_CHECKS` in `src/officebench/checks/registry.py`. Dates without a year get the year of the last
date before them in the text, otherwise that of the reference date (13.10.2026), and the following year if they
would otherwise lie more than 120 days before it. For the weekday, from 60 days before onwards both years count.

| Name | Label | Severity | Example |
|---|---|---|---|
| `foreign_script` | foreign script | hard | „eine直观e Anbindung“, Cyrillic „единоAnna“ |
| `english` | English text | soft | more English than German function words (the, and … against der, und …) |
| `control_tokens` | control tokens | hard | `<\|"\|>`, `<\|channel\|>` in the text |
| `literal_newline` | literal \n | hard | `Zeile 1\nZeile 2` as text (not in paths such as `\\nas01\backup`) |
| `markdown` | markdown remnants | soft | `**fett**`, `## Überschrift`, `\|---\|` at the start of a line |
| `placeholders` | placeholder | soft | „[Name eintragen]“, „[Unterschrift]“, „System X“, „Max Mustermann“, „TT.MM.JJJJ“, „TBD“, „XX €“, „IT-Desk 0000“, „IBAN [ ]“, „um [ ] Tsd. €“, „Protokollführer: KI-Assistent“. Not: „[ ]“ as a checkbox at the start or end of a line |
| `weekday` | wrong weekday | hard; soft when the year is inferred | „Dienstag, 26. Oktober 2026“ (Monday); „Di., 19.10.“; „12.10.2026 (Mittwoch)“; row „Di \| 26.10.2026“. Not: „Mo–Fr 12.10.–16.10.“ |
| `calendar_week` | wrong calendar week | soft | „Woche 41“ in the header of minutes dated 12.10.2026 (KW 42), „KW 1–6 (Dezember 2026 – Januar 2027)“, „26.10.2026 (KW 45)“, „KW 53/2027“ (does not exist); table row „44 \| 02.11.2026 \| 06.11.2026“ under the header „KW“ (KW 45), „Kick-off in KW 42“ in the row with start 19.10.2026. Right: „KW 52–1 (Dez.–Jan.)“, „KW 53 (28.12.2026–03.01.2027)“, the week of the start, of the end or in between. Only a KW directly next to a date/month or in a table row with date cells: a KW column or a cell „KW 44“ against all date cells of the row, a KW in the running text of a cell only against columns such as Start/Beginn/Von/Ende/Zeitraum/Datum (not Frist, bis, Plan, Soll/Ist) |
| `past_dates` | date in the past | soft | only with `dates_from`: „Start in KW 19/2026“, „Kick-off am 01.10.2026“. Not: „Stand: 01.10.2026“, „Protokoll vom …“, titles, a period that ends after `dates_from` |
| `text_arithmetic` | wrong calculation in text | soft | „80 × 8 € × 12 = 7.860 €“; table row „0,2 PT/Woche × 48 × 85 EUR \| 4.080“; row „Gesamt …“ or „… gesamt“ ≠ sum of the amounts above it (ranges „23.000 – 39.000“ added separately, a subtotal of the rows directly above counts); tolerance 0.5 %, at least the written precision („4 × 8,5 h + 5,25 h = 39 h“ is wrong). Not: ranges „15–30 € × 5–10“, a monthly amount next to an annual amount |
| `formula_errors` | formula error | hard | `#VALUE!`, `#REF!`, `#NAME?`, `#DIV/0!`, `Err:502` after recalculation |
| `formula_empty` | formula without result | hard | formula cell stays empty after recalculation |
| `formula_as_text` | formula as text | hard | text cell „=B2-B3“ or „"=SUM(B3:B4)"“ |
| `number_as_text` | number as text | soft | text cell „1.500 €“ (not in columns Pos./Nr./Jahr/KW …) |
| `text_in_number_column` | text in number column | soft | „siehe oben“ in a column formatted as numbers |
| `empty_number_column` | empty number column | soft / hard | column „Gesamtpreis (€)“ without a value (soft); all numbers entered on a sheet are 0, i.e. an empty template (hard) |
| `zero_sum` | sum is 0 | hard | `=SUM(H2:H7)` gives 0 because the range holds numbers or formulas stored as text (a column of zeros only is not a defect) |
| `sum_range` | incomplete sum range | soft | total row `=SUM(B2:B6)`, data up to B7; the sum skips numbers stored as text; row „Summe“ computes `=AVERAGE(…)`; column „Summe“ `=SUM(F2:G2)` leaves out E2. Not: columns left of the range with a key or quantity in the header (Fläche, Anteil, %, Mitarbeitende, Menge, Stunden …) or in a different number format than the summed ones (percent instead of euro) |
| `empty_table` | incomplete table | soft | Word/slide table with only a header row („Thema \| Beschluss“); empty header cell above a column with values (first column excepted) |
| `weekend` | date on a weekend | soft | „Abgabe bis 17.10.2026“, cell „18.10.2026“ in a column „Frist“/„Termin“/„Datum“. Not: a written-out weekday („Samstag, 17.10.“), periods, vacation/celebration/„in Kraft“, validity before the date („gilt ab 01.11.“, „gelten bis zum 31.10.“, „gültig bis“; but „bis 25.10., damit das Angebot noch gilt“ counts), purchase or warranty dates, dates from the prompt |
| `invalid_date` | invalid date | hard | xlsx: text cell „2026-11-31“ or „30.02.2026“ (with a four-digit year in any column, otherwise in date columns) |
| `date_as_text` | date as text | soft | xlsx: valid date stored as text („2026-07-01“, „01.07.2026“) in a date column (header with Datum, Start, …tag, or mostly date or date-text cells); not if `column_format` already checks the column as a date |
| `share_over_100` | share over 100 % | soft | xlsx: cell in percent format above 100 % in a column Anteil/Quote/Verteilung (6.954 % instead of 69,5 %), above 1.000 % with Auslastung/Belegung/Prozent/„%“ in the header. Not: Veränderung, Abweichung, Wachstum, Zielerreichung, Erfüllung, Plan/Soll/Ist, Vorjahr |

### Severities

Severity of the `[checks]` keys: missing required parts and wrong values are hard (also `chart_type`,
`chart_values`, `chart_series`, `value_ranges`, `dates_between`, `calculations`, `count.min`, `words_min`,
`forbidden`, `values_present`, `notes_min`, `sorted`, `groups`, `retained` below `hard`); soft are `words_max`,
`count.max`, `topics_soft`, `retained` below `soft`, `last_slide_topics`, `slides_added`, the heuristics
`side_by_side`, `column_format`, `workdays` and `numbers_sourced`, everything "not checkable", and with
`calculations` an incomplete total row (additive formula, one value missing). Without a chart, every chart key gives
a hard defect "no chart". An unreadable file, a wrong or unknown file type and "not recalculated" (LibreOffice) are
hard. If a single check crashes, there is only a soft defect "check crashed"; the other findings remain.
`calculations` treats date cells as Excel serial numbers (days) and percent cells as shares (12,5 % = 0.125); with %
in the header and without percent format, × 100 also counts (see above).

## Reply (`[reply]`, optional)

Checks on the model's last text answer (final reply). `topics` and `forbidden` count for success in every task: in
`no_file` tasks instead of the file, in `file`/`follow_up` tasks in addition to the content check. The soft checks
give defects that are reported with the result but do not count for success. Labels and severities: `REPLY_CHECKS`
in `src/officebench/checks/registry.py`.

| Key | Type | Meaning |
|---|---|---|
| `topics` | like above | must occur in the reply (hard) |
| `forbidden` | like `topics` | must not occur in the reply, e.g. source markers `'\[\d+\]'` (hard) |
| `words_max` | number | at most this many words in the whole final reply, lead-in and closing sentences included (soft "reply too long") |
| `no_markdown` | bool | no `**fett**`, `## Überschrift` or table separators in the reply when the text ends up elsewhere (Outlook): soft "markdown in reply". Soft because the chat renders markdown and selecting and copying keeps the formatting; only the copy button delivers the asterisks. A key of its own instead of `forbidden` so that the severity is right and the patterns are maintained in one place (the same as the general check `markdown`) |

## Behavior (`[behavior]`, optional)

Checks on the tool calls in the log, so neither on the file nor on the reply. Hence a table of its own: the content
check only sees files and also runs without a log, and `[reply]` checks text. Every violation is hard and makes the
task fail. Labels and severities: `BEHAVIOR_CHECKS` in `src/officebench/checks/registry.py`.

| Key | Type | Meaning |
|---|---|---|
| `tools_expected` | list | the model calls these extra tools at least once (in any turn, even if the call fails), e.g. `["web_search"]` |
| `tools_forbidden` | list | the model never calls these extra tools, e.g. `["create_calendar_event", "send_email"]`: an email or an appointment that nobody asked for is an action with consequences |

Names must be in the task's `extra_tools`; the validator rejects other names and a name in both lists.

## Judge (`[judge]`)

| Key | Type | Meaning |
|---|---|---|
| `checklist` | list | concrete points (German) on which the judge bases the criteria (what makes a 5) |

## Extra tools

`extra_tools/<name>.json`: `{"spec": {OpenAI tool spec}, "result": "text the harness returns as the result"}`. The
function name in `spec` equals `<name>`. Every file is used by at least one task. This lets a task test whether the
model picks the right tool among several, or calls one it was not asked to (`[behavior]`).
