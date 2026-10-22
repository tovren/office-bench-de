# Results v0.3

Seven models, 50 tasks × 3 runs each, run on 22 October 2026 through the Vercel AI Gateway with the default profile
(reference date Tuesday, 13 October 2026), Office Documents 0.3.1 (tool commit `0386886`), harness commit
`d9df0fc`. The tasks and checks are those of v0.1.1; only the tool changed against v0.2. The report is
[report.md](report.md):

```sh
uv run obench report results/v0.3 --grades results/v0.3/grades.jsonl
```

- `grades.jsonl`: blind quality review of the files as delivered (an empty "Test" workbook is graded as the
  file), one line per graded file (`model`, `task`, `rep`, `file`, five grades, reasons in German or English),
  judge `claude-opus-5.5-agent`: Claude Opus 5.5 agent sessions with the export of `obench judge --export`, ten
  files per session, two files per model and task, the same instructions as v0.1. `quartal` is graded in version 2.
- `anchor-grades.jsonl`: 30 files of v0.1 mixed blind into the same review, to see whether the judge drifted. Against
  their v0.1 grades: mean +0.05 (absolute difference 0.15, correlation 0.94); per criterion 22 to 28 of 30 grades
  equal, none more than one point apart.
- Quality against v0.1, paired by task without `quartal` (difference of the mean grade, 95 % bootstrap interval):
  Haiku 4.30 → 4.45 (+0.15, −0.02 to +0.31), DeepSeek 4.27 → 4.33 (+0.07, −0.04 to +0.18), Nemotron 4.01 → 4.15
  (+0.14, +0.03 to +0.27), Qwen3.8-Flash 3.92 → 4.14 (+0.22, +0.08 to +0.38), Qwen3.8-27B 3.91 → 4.03 (+0.13, 0.00
  to +0.27), Gemma 3.64 → 3.72 (+0.08, −0.04 to +0.19), gpt-oss-120b 3.57 → 3.67 (+0.09, −0.02 to +0.20). All
  models gain a little, which is about +0.05 more than the anchors drifted; the order stays the same.
- What changed in the tool: formulas sent in the rows of a formula column (sum rows below the items) are kept
  instead of being replaced by the column formula, with checks for circular references, subtotals counted twice
  and references to empty rows; the JSON repair handles swapped and extra closing brackets, a missing `{`, a
  stray quote after a number and a key without its opening quote.
- Replaying all 2,923 tool calls of v0.1 and v0.2 with 0.3.1 before this run: 73 of the 139 calls that 0.3.0 sent
  back for broken JSON text build the file (Nemotron 51 of 68, Qwen3.8-27B 17 of 32), 24 files get the sum
  formulas the model sent, and 6 calls that 0.3.0 accepted are sent back, all for real errors (rows counted
  wrong, circular references, subtotals counted twice).
- Changes against v0.2, paired by task (difference in success, 95 % bootstrap interval): Haiku 0.0 points
  (−4.7 to +4.7), DeepSeek +2.0 (−1.3 to +5.3), Nemotron +0.7 (−4.7 to +6.7), Qwen3.8-27B +6.0 (−1.3 to +14.0),
  Qwen3.8-Flash −3.3 (−8.7 to +2.0), gpt-oss-120b +8.7 (0.0 to +18.0), Gemma +2.7 (−5.3 to +10.7). The four tasks
  with sum rows (`anfrage`, `preisaenderung`, `bueromaterial`, `angebot`): 70 of 84 runs (v0.2: 48).
- **v0.3.1 (22 October 2026, after the run):** four checks missed correct answers and were fixed, and `quartal`
  got its numbers; all runs were rescored from the stored files, only `quartal` ran again (21 runs, harness
  `c072769`, listed under `reruns` in `meta.json`; the other tasks ran with `d9df0fc`). Changes: `wartungsmail` v2
  („abzumelden“ and „meldet euch … ab“ count as „abmelden“, +11 runs), `richtlinie` v2 („zwei (2) Arbeitstage“,
  „09:00 Uhr bis 15:00 Uhr“, +5), `zeiterfassung` v2 (the dot in „.xlsx“ ended the sentence for „Makro geht
  nicht“, +2), reply topics ignore Markdown bold (`homeoffice`, +2), `values_present` reads thousands separated by
  spaces („143 200“), and `quartal` v2 with the Q3 numbers as an attachment (version 1: 17 of 21 successful, version
  2: 17 of 21). Before: Haiku 96, DeepSeek 93, Nemotron 87, Qwen3.8-27B 85, Qwen3.8-Flash 85, gpt-oss 69,
  Gemma 65 %; after: 98, 95, 87, 86, 86, 72, 69 %. Haiku's two remaining file failures besides a wrong weekday are
  the empty second workbooks (`budget`, `inventar`); Office Documents 0.3.2 sends a workbook without data rows
  back.
- The built files are not in the repository; they are the release asset `v0.3.1-files.zip` (`v0.3-files.zip`
  has the `quartal` version 1 files; `<model>/files/…`, unzip here to rerun `obench score`).
