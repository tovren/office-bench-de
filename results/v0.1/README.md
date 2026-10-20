# Results v0.1

Seven models, 50 tasks × 3 runs each, run on 19 and 20 October 2026 through the Vercel AI Gateway with the default
profile (reference date Tuesday, 13 October 2026), tool commit `641df3a`. The report is [report.md](report.md):

```sh
uv run obench report results/v0.1 --grades results/v0.1/grades.jsonl
```

- 49 tasks ran with harness commit `7885036`. Task `anfrage` was changed afterwards (version 2: the prompt asks for
  formulas, since version 1 did not but its checks required them) and its 21 runs were redone with the harness at
  `41aa661` plus that task change (committed as `ebdb89f`). The only change of the chat loop in between concerns a
  round limit before the last user message, which cannot happen in this single-message task. `meta.json` shows the
  later version.
- `grades.jsonl`: one line per graded file (`model`, `task`, `rep`, `file`, five grades, reasons in German),
  judge `claude-opus-5.5-agent`: Claude Opus 5.5 agent sessions with the export of `obench judge --export`, ten
  files per session, two files per model and task.
- Rescored on 20 October 2026 with the checks of v0.1.1 (same runs and files, no new model calls): `formula_empty`
  no longer flags an IF that leaves a row empty on purpose, and `total_row`, `line_item_formula` and
  `data_rows_min` look at the main table instead of the first sheet. Four runs change from failed to successful
  (DeepSeek `bueromaterial` 1 and `preisaenderung` 1, Qwen3.8-27B `preisaenderung` 0, Gemma `sparquote` 1); no run
  gets worse. Before: DeepSeek 86 %, Qwen3.8-27B 83 %, Gemma 61 %.
- The built files are not in the repository; they are the release asset `v0.1-files.zip`
  (`<model>/files/…`, unzip here to rerun `obench score`).
