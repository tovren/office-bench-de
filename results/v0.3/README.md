# Results v0.3

Seven models, 50 tasks × 3 runs each, run on 22 October 2026 through the Vercel AI Gateway with the default profile
(reference date Tuesday, 13 October 2026), Office Documents 0.3.1 (tool commit `0386886`), harness commit
`d9df0fc`. The tasks and checks are those of v0.1.1; only the tool changed against v0.2. The report is
[report.md](report.md):

```sh
uv run obench report results/v0.3
```

- No blind quality review: `grades.jsonl` is missing on purpose. The quality grades of v0.1 are in
  [../v0.1/README.md](../v0.1/README.md).
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
  `c072769`, which `meta.json` now shows; the other tasks ran with `d9df0fc`). Changes: `wartungsmail` v2
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
