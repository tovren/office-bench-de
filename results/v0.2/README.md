# Results v0.2

Seven models, 50 tasks × 3 runs each, run on 22 October 2026 through the Vercel AI Gateway with the default profile
(reference date Tuesday, 13 October 2026), Office Documents 0.3.0 (tool commit `c90f89f`), harness commit
`bb4bfe8`. The tasks and checks are those of v0.1.1; only the tool changed. The report is [report.md](report.md):

```sh
uv run obench report results/v0.2
```

- No blind quality review: `grades.jsonl` is missing on purpose. The quality grades of v0.1 are in
  [../v0.1/README.md](../v0.1/README.md).
- The tool specs were generated again with Open WebUI 0.11.4 (`get_tool_specs`). The v0.1 specs had kept the
  docstring indentation in the three function descriptions, which Open WebUI strips; the text is the same.
- Replaying all 660 Excel calls of v0.1 with 0.3.0: 43 calls that 0.1.0 accepted are sent back (34 for percent
  columns, 9 for other real errors: total rows overwritten by the column formula, `=C-B` instead of `=B-C`,
  arithmetic on a text column, a reference outside the table, a time difference without `*24`), and 33 calls that
  0.1.0 sent back are accepted (SUMIFS, NETWORKDAYS, DATE, references to other sheets).
- Changes against v0.1, paired by task (difference in success, 95 % bootstrap interval): Haiku +4.7 points (−0.7 to
  +10.0), DeepSeek +4.0 (−0.7 to +9.3), Qwen3.8-Flash +5.3 (0.0 to +11.3), Nemotron +0.7 (−6.0 to +7.3),
  Qwen3.8-27B −5.3 (−12.0 to +1.3), gpt-oss-120b −6.0 (−14.0 to +1.3), Gemma 0.0 (−8.7 to +8.7). `anfrage`
  alone: 2 → 10 of 21 runs.
- The built files are not in the repository; they are the release asset `v0.2-files.zip`
  (`<model>/files/…`, unzip here to rerun `obench score`).
