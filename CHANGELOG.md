# Changelog

Each version is a release on GitHub. A new run is a new version; check fixes rescore the stored files of all
earlier runs without new model calls. Details per run: `results/<version>/README.md`.

## v0.3.2 (22 October 2026): quality review of v0.3

No new runs; success rates as in v0.3.1.

- Blind quality review of v0.3: 697 files as delivered (an empty "Test" workbook is graded as the file), two per
  model and task, Claude Opus 5.5 agent sessions with the instructions of v0.1 (`results/v0.3/grades.jsonl`).
- 30 v0.1 files mixed blind into the review as anchors (`results/v0.3/anchor-grades.jsonl`): +0.05 against their
  v0.1 grades, correlation 0.94, no grade more than one point apart.
- Quality against v0.1, paired by task without `quartal`: every model gains 0.07 to 0.22, significantly only
  Nemotron (+0.14) and Qwen3.8-Flash (+0.22); the order stays the same.
- The judge export renders page images in LibreOffice runs of 15 files with a retry per file; one run over all
  files had left 141 files without images (they were graded again with images).

| Model | Quality v0.3 | v0.1 |
|---|---:|---:|
| Claude Haiku 5.5 | 4.45 | 4.30 |
| DeepSeek V4 Flash | 4.33 | 4.27 |
| Nemotron 3.5 Super VL | 4.15 | 4.00 |
| Qwen3.8-Flash | 4.13 | 3.92 |
| Qwen3.8-27B | 4.03 | 3.91 |
| Gemma 4 31B | 3.72 | 3.63 |
| gpt-oss-120b | 3.67 | 3.57 |

## v0.3.1 (22 October 2026): check fixes, `quartal` version 2

All runs (v0.1, v0.2, v0.3) rescored from their stored files; only `quartal` ran again (21 runs in v0.3). Built
files of v0.3: `v0.3.1-files.zip`.

- `wartungsmail` v2: „abzumelden“ and „meldet euch … von den Systemen ab“ count as „abmelden“ (11 runs in v0.3 had
  failed on this).
- `richtlinie` v2: „zwei (2) Arbeitstage“, „09:00 Uhr bis 15:00 Uhr“ and „zwischen 9 und 15 Uhr“ count; „drei (3)
  Tage“ is forbidden too.
- `zeiterfassung` v2: the dot in „.xlsx“ no longer ends the sentence for „Makro geht nicht“.
- Reply topics ignore Markdown bold (`**bis zu drei** Tage`); `values_present` reads thousands separated by spaces
  (`143 200`).
- `quartal` v2: the Q3 numbers come as an attachment. Version 1 asked for slides „zu den Zahlen von Q3 2026“
  without giving any: Haiku asked for them and failed, Gemma, gpt-oss and Nemotron invented figures without saying
  so and passed. With the numbers, 17 of 21 runs pass; most failures leave the wrong customer out of the top five.
  v0.1 and v0.2 keep their version 1 results.
- The runner keeps the task selection of a resumed run (`reruns` in `meta.json`).

No run gets worse. Success v0.3 before → after: Haiku 96 → 98, DeepSeek 93 → 95, Nemotron 87 → 87, Qwen3.8-27B
85 → 86, Qwen3.8-Flash 85 → 86, gpt-oss-120b 69 → 72, Gemma 65 → 69 %.

## v0.3 (22 October 2026): run with Office Documents 0.3.1

Same tasks and checks as v0.1.1; only the tool changed (0.3.0 → 0.3.1).

- Sum rows below the items (net, VAT, gross) are kept: 0.3.0 replaced a formula in a row of a formula column with
  the line item formula, so the totals showed 0. The four tasks with such rows (`anfrage`, `preisaenderung`,
  `bueromaterial`, `angebot`) succeed in 70 of 84 runs (v0.2: 48, v0.1: 41); `preisaenderung` alone 8 → 20 of 21.
- The JSON repair handles swapped and extra closing brackets, a missing `{`, a stray quote after a number and a key
  without its opening quote: Nemotron goes from 49 calls with invalid JSON (and 3 runs at the round limit) to 1
  (and none).
- Paired by task against v0.2 (without `quartal`), only gpt-oss-120b (+10 points, +1 to +18) and Qwen3.8-27B (+8,
  0 to +16) are at the edge of what chance explains; the others are within ±4.
- Office Documents 0.3.2 (sends back a workbook without any rows) is vendored for future runs.

## v0.2 (22 October 2026): run with Office Documents 0.3.0

Same tasks and checks as v0.1.1; only the tool changed (0.1.0 → 0.3.0).

- The percent trap is gone: the tool spec says how percent cells are stored and sends back fractions in percent
  columns, `/100` on a percent cell and `*100` in a percent column. `anfrage` 10 of 21 runs right (v0.1: 2 of 21).
- Tool specs generated again with Open WebUI 0.11.4 (`get_tool_specs`); the v0.1 specs had kept the docstring
  indentation, the text is the same.
- New mutant outcome `prevented`: the tool itself sends back or repairs 8 of 202 mutants.
- Most changes against v0.1 are within run-to-run noise; the ranking is stable.

## v0.1.1 (20 October 2026): check fixes

v0.1 rescored from the same files.

- `formula_empty` no longer flags an IF that leaves a row empty on purpose (`=IF(A9="";"";C9*E9)`).
- `total_row`, `line_item_formula` and `data_rows_min` look at the main table (most data rows among the sheets
  with at least three columns) instead of the first sheet.
- `share_over_100` leaves out Plan, Soll, Ist, Diff and vs. as whole words; more placeholder words.

Four runs change from failed to successful, none gets worse.

## v0.1 (20 October 2026): first results

Seven models, 50 tasks × 3 runs with Office Documents 0.1.0, content check and blind quality review (696 files,
Claude Opus 5.5 agent sessions). `anfrage` is in version 2 (the prompt asks for formulas, since version 1 did
not but its checks required them); its 21 runs were redone before the release.
