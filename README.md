# office-bench-de

How well do language models write German office documents through a tool call? 50 everyday office tasks in
German (offers, minutes, budgets, rotas, slides from a report, letters, follow-up changes), each answered by the
model with a Word, Excel or PowerPoint file built by the
[Office Documents](https://github.com/tovren/open-webui-plugins) tool for Open WebUI, or with a plain chat answer.

Every delivered file goes through a deterministic content check (Excel files are recalculated by LibreOffice first)
and, separately, a blind quality review on five criteria. Everything is public: tasks, reference solutions, checks,
run logs and grades.

## Results v0.1

50 tasks × 3 runs per model, run through the Vercel AI Gateway in October 2026.

| Model | Success | pass^3 | Content ok | Quality (1–5) | Cost of 150 runs |
|---|---:|---:|---:|---:|---:|
| Claude Haiku 5.5 (thinking medium) | 91 % (84–97) | 80 % | 90 % | 4.30 (4.11–4.47) | $0.71 |
| DeepSeek V4 Flash (thinking high) | 87 % (79–95) | 80 % | 89 % | 4.27 (4.12–4.40) | $0.17 |
| Nemotron 3.5 Super VL (thinking on) | 85 % (76–93) | 76 % | 86 % | 4.00 (3.85–4.17) | $0.50 |
| Qwen3.8-27B (thinking medium) | 84 % (75–92) | 68 % | 85 % | 3.91 (3.73–4.08) | $0.27 |
| Qwen3.8-Flash (thinking medium) | 83 % (74–91) | 64 % | 82 % | 3.92 (3.74–4.08) | $0.46 |
| gpt-oss-120b (reasoning medium) | 66 % (54–77) | 46 % | 67 % | 3.57 (3.38–3.76)\* | $0.36 |
| Gemma 4 31B | 62 % (49–75) | 52 % | 57 % | 3.63 (3.45–3.81) | $0.38 |

- **Success**: the run delivered what the task asks for (the file, every follow-up turn, no hard defect in the
  content check, reply and behavior checks where the task has them). 95 % intervals from a bootstrap over tasks.
- **pass^3**: chance that three fresh runs of a task all succeed: how reliable a model is, not just how good.
- **Content ok**: file tasks only (43 of 50): the delivered file has no hard defect.
- **Quality**: mean of five blind grades (language, content and calculations, completeness, structure, usefulness)
  for two files per model and task, 696 files in total, graded by Claude Opus 5.5 agent sessions that could check
  calculations and dates with scripts. \*gpt-oss-120b delivered no file at all in two tasks; those are missing from
  its quality grade, not counted as a 1.
- **Cost**: as reported by the gateway, for all 150 runs; prices depend on the provider.

Full report with per-task results, defects, tool errors and paired comparisons:
[results/v0.1/report.md](results/v0.1/report.md).

### What stands out

- **Haiku and DeepSeek are level.** The quality difference is 0.03 (95 %: −0.11 to 0.16); DeepSeek costs a quarter.
  The clear gaps are DeepSeek → Nemotron (0.26) and Qwen → Gemma (0.27); the models between them overlap.
- **Calling the tool is not the problem.** Every model except gpt-oss-120b ends with a file in 99–100 % of the file
  tasks, often after a rejected first call that the tool's error message helped to fix. The failures are in the
  content: wrong or missing numbers, missing topics, dates on weekends, invented figures.
- **gpt-oss-120b** hits the limit of 8 tool rounds in 8 runs and delivers no file at all in two slide tasks; most of its
  rejected calls fail the tool's own content validation and are not fixed.
- **Gemma 4 31B** gets files built but loses content: missing values and topics, missing total rows.
- **Qwen3.8-Flash** builds more files than needed in 34 of 150 runs (a new file for each small fix).
- **Percent columns are a trap.** In `anfrage` only 2 of 21 runs get the net total right. The tool stores a percent
  value of 5 as 0.05, as Excel does, but its spec does not say that formulas then see 0.05, so models divide by
  100 a second time (or send 0.05, which becomes 0.05 %). See [docs/open-issues.md](docs/open-issues.md).

What is measured is always the combination of model, this tool and this harness (system prompt, attachment
template, round limit), not the model alone.

## Quick start

```sh
git clone https://github.com/tovren/office-bench-de && cd office-bench-de
uv sync                                   # Python >= 3.11
uv run obench tasks list                  # the 50 tasks

export AI_GATEWAY_API_KEY=...             # or any OpenAI-compatible endpoint, see configs/models/local-example.toml
uv run obench run configs/models/deepseek-v4-flash-high.toml --probe        # 2 tasks, 1 run: is the setup right?
uv run obench run configs/models/deepseek-v4-flash-high.toml --out runs/my-run
uv run obench report runs/my-run > runs/my-run/report.md                    # scores the runs, then reports
```

Scoring needs LibreOffice (`soffice`); the quality review also needs `pdftoppm` (poppler-utils). To compare your
model with the published results:

```sh
uv run obench report results/v0.1 runs/my-run
```

A full run of 150 task runs took 7 to 40 minutes per model through the gateway (4 at a time).

## How it works

| | |
|---|---|
| [docs/task-format.md](docs/task-format.md) | tasks: `task.toml`, attachments, reference solution, the checks a task can use |
| [docs/harness.md](docs/harness.md) | what the model is sent, how tool calls are executed, retries, the run log, model configs |
| [docs/scoring.md](docs/scoring.md) | success, content ok, pass^k, outages, the statistics behind the intervals |
| [docs/judge.md](docs/judge.md) | the blind quality review, by API or by agent sessions, and its calibration |
| [docs/mutants.md](docs/mutants.md) | 202 broken variants of the reference solutions that test the checks themselves |
| [docs/open-issues.md](docs/open-issues.md) | known limits and checks that are still missing |

- **Tasks** (`tasks/<id>/`): 43 tasks that end with a file (18 Excel, 16 Word, 9 PowerPoint), 6 of them follow-ups
  over several turns, and 7 tasks where the right answer is no file (a question, an e-mail text, an
  extra tool such as web search or a calendar entry). The reference date is Tuesday, 13 October 2026.
- **The tool** is vendored unchanged (`src/officebench/tool/`, plugin commit `641df3a`), with the function specs
  frozen as Open WebUI 0.11.4 sends them. The model only fills in JSON arguments; fixed code builds the file.
- **The content check** has over 40 checks: required values and topics, formulas and their results after
  recalculation, total rows, weekdays and public holidays, numbers without a source, placeholders, retained
  content in follow-ups and more. A hard defect means the file is not usable as delivered; soft defects are
  reported but do not decide success. Each task's reference solution passes its checks, and the checks catch 186
  of 202 mutants.
- **The quality review** grades blind: neutral ids, neutral file timestamps, one file per request.

## Data

`results/v0.1/` holds, per model, `meta.json` (model config, profile, tool and task hashes), `log.jsonl` (every
round: tokens, cost, provider, tool calls and their results; reasoning is not stored) and `results.jsonl` (the
scored runs), plus `grades.jsonl` (all 696 grades with reasons, in German) and the report. The built files
(1,147 documents plus the raw arguments of every tool call, 32 MB zipped) are a release download: unzip them into `results/v0.1/` to rerun the content check.

## License

MIT, see [LICENSE](LICENSE). The vendored Office Documents tool is MIT as well.
