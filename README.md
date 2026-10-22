# office-bench-de

How well do language models write German office documents through a tool call? 50 everyday office tasks in
German (offers, minutes, budgets, rotas, slides from a report, letters, follow-up changes), each answered by the
model with a Word, Excel or PowerPoint file built by the
[Office Documents](https://github.com/tovren/open-webui-plugins) tool for Open WebUI, or with a plain chat answer.

Every delivered file goes through a deterministic content check (Excel files are recalculated by LibreOffice first)
and, separately, a blind quality review on five criteria. Everything is public: tasks, reference solutions, checks,
run logs and grades.

## Results

Run v0.3: 50 tasks × 3 runs per model on 22 October 2026 through the Vercel AI Gateway, with Office Documents
0.3.1 as the tool, scored with the checks of v0.3.1 and graded in v0.3.2.

| Model | Success | pass^3 | Content ok | Quality (1–5) | Cost of 150 runs |
|---|---:|---:|---:|---:|---:|
| Claude Haiku 5.5 (thinking medium) | 98 % (95–100) | 94 % | 98 % | 4.45 (4.29–4.60) | $0.67 |
| DeepSeek V4 Flash (thinking high) | 95 % (89–99) | 90 % | 95 % | 4.33 (4.21–4.45) | $0.16 |
| Nemotron 3.5 Super VL (thinking on) | 87 % (78–94) | 76 % | 88 % | 4.15 (4.01–4.28) | $0.53 |
| Qwen3.8-27B (thinking medium) | 86 % (78–93) | 70 % | 84 % | 4.03 (3.87–4.19) | $0.28 |
| Qwen3.8-Flash (thinking medium) | 86 % (79–93) | 66 % | 86 % | 4.13 (3.99–4.27) | $0.44 |
| gpt-oss-120b (reasoning medium) | 72 % (61–83) | 58 % | 71 % | 3.67 (3.51–3.85) | $0.42 |
| Gemma 4 31B | 69 % (57–81) | 58 % | 64 % | 3.72 (3.54–3.89) | $0.34 |

- **Success**: the run delivered what the task asks for (the file, every follow-up turn, no hard defect in the
  content check, reply and behavior checks where the task has them).
- **pass^3**: chance that three fresh runs of a task all succeed: how reliable a model is, not just how good.
- **Content ok**: file tasks only (43 of 50): the delivered file has no hard defect.
- **Quality**: blind review of 697 files as delivered (two per model and task) by Claude Opus 5.5 agent sessions,
  mean of language, content, completeness, structure and usefulness.
- **Cost**: as reported by the gateway; prices depend on the provider.
- 95 % intervals from a bootstrap over tasks. Full report with per-task results, defects, tool errors and
  rejections: [results/v0.3/report.md](results/v0.3/report.md); earlier runs and what changed between versions:
  [CHANGELOG.md](CHANGELOG.md).

### What stands out

- **Calling the tool is not the problem.** Every model ends with a file in 95–100 % of the file tasks. The
  failures are in the content: missing values and topics, wrong group sums, dates on the wrong weekday.
- **Haiku and DeepSeek lead**, and their gap is within noise in both success and quality; DeepSeek costs a quarter
  as much. Nemotron and the two Qwen models overlap, gpt-oss-120b and Gemma are clearly behind. Success and
  quality form the same three groups.
- **Content and usefulness get the lowest grades, language the highest** for every model except the two Qwen
  models: their German gets 4.1, below Gemma, for made-up words, Denglisch and, in six Qwen3.8-Flash files,
  Chinese characters.
- **Reliability differs more than success.** The Qwen models succeed as often as Nemotron but less consistently
  (pass^3 66–70 % against 76 %).
- **Habits of single models:** gpt-oss-120b hits the limit of 8 tool rounds in 7 runs; Qwen3.8-Flash builds a new
  file for each small fix in 32 of 150 runs; Haiku twice sent a second, empty "Test" workbook in the same round
  (Office Documents 0.3.2 sends such a workbook back).

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
uv run obench report results/v0.3 runs/my-run
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
- **The tool** is vendored unchanged (`src/officebench/tool/`, Office Documents 0.3.2, plugin commit `9ff6838`;
  the published results ran with older versions, see each `meta.json`), with the function specs frozen as Open
  WebUI 0.11.4 sends them. The model only fills in JSON arguments; fixed code builds the file.
- **The content check** has over 40 checks: required values and topics, formulas and their results after
  recalculation, total rows, weekdays and public holidays, numbers without a source, placeholders, retained
  content in follow-ups and more. A hard defect means the file is not usable as delivered; soft defects are
  reported but do not decide success. Each task's reference solution passes its checks; of 202 mutants the tool
  itself sends back or repairs 8, and the checks catch 178 of the other 194.
- **The quality review** grades blind: neutral ids, neutral file timestamps, one file per request.

## Data

`results/<version>/` holds, per model, `meta.json` (model config, profile, tool and task hashes), `log.jsonl`
(every round: tokens, cost, provider, tool calls and their results; reasoning is not stored) and `results.jsonl`
(the scored runs), plus the report. `results/v0.1/grades.jsonl` and `results/v0.3/grades.jsonl` have the quality
grades with reasons, `results/v0.3/anchor-grades.jsonl` the 30 v0.1 files graded again as anchors. The built files
(the documents plus the raw arguments of every tool call) are release downloads (`v0.3.1-files.zip`,
`v0.2-files.zip`, `v0.1-files.zip`): unzip them into the matching folder to rerun the content check.

## License

MIT, see [LICENSE](LICENSE). The vendored Office Documents tool is MIT as well.
