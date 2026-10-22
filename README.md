# office-bench-de

How well do language models write German office documents through a tool call? 50 everyday office tasks in
German (offers, minutes, budgets, rotas, slides from a report, letters, follow-up changes), each answered by the
model with a Word, Excel or PowerPoint file built by the
[Office Documents](https://github.com/tovren/open-webui-plugins) tool for Open WebUI, or with a plain chat answer.

Every delivered file goes through a deterministic content check (Excel files are recalculated by LibreOffice first)
and, separately, a blind quality review on five criteria. Everything is public: tasks, reference solutions, checks,
run logs and grades.

## Results v0.3

50 tasks × 3 runs per model, run on 22 October 2026 through the Vercel AI Gateway, with Office Documents 0.3.1 as
the tool (v0.2: 0.3.0, v0.1: 0.1.0). All three runs are scored with the checks of v0.3.1 (see below).

| Model | Success | pass^3 | Content ok | Cost of 150 runs | v0.2 | v0.1 |
|---|---:|---:|---:|---:|---:|---:|
| Claude Haiku 5.5 (thinking medium) | 98 % (95–100) | 94 % | 98 % | $0.67 | 96 % | 91 % |
| DeepSeek V4 Flash (thinking high) | 95 % (89–99) | 90 % | 95 % | $0.16 | 92 % | 88 % |
| Nemotron 3.5 Super VL (thinking on) | 87 % (78–94) | 76 % | 88 % | $0.53 | 86 % | 86 % |
| Qwen3.8-27B (thinking medium) | 86 % (78–93) | 70 % | 84 % | $0.28 | 79 % | 85 % |
| Qwen3.8-Flash (thinking medium) | 86 % (79–93) | 66 % | 86 % | $0.44 | 89 % | 83 % |
| gpt-oss-120b (reasoning medium) | 72 % (61–83) | 58 % | 71 % | $0.42 | 62 % | 68 % |
| Gemma 4 31B | 69 % (57–81) | 58 % | 64 % | $0.34 | 66 % | 65 % |

- **Success**: the run delivered what the task asks for (the file, every follow-up turn, no hard defect in the
  content check, reply and behavior checks where the task has them). 95 % intervals from a bootstrap over tasks.
- **pass^3**: chance that three fresh runs of a task all succeed: how reliable a model is, not just how good.
- **Content ok**: file tasks only (43 of 50): the delivered file has no hard defect.
- **Cost**: as reported by the gateway, for all 150 runs; prices depend on the provider.
- **v0.2, v0.1**: success with the same tasks and checks and the older tool versions
  ([results/v0.2](results/v0.2/README.md), [results/v0.1](results/v0.1/README.md)); `quartal` there is still
  version 1 (without numbers).
- **v0.3.1** fixed four checks that missed correct answers and gave `quartal` the numbers it talks about; all three
  runs were rescored from their stored files, only `quartal` ran again. Details in
  [results/v0.3/README.md](results/v0.3/README.md).

There is no blind quality review for v0.2 and v0.3. The quality grades of v0.1 (Claude Opus 5.5 agent sessions,
696 files) are in [results/v0.1/README.md](results/v0.1/README.md): Haiku 4.30, DeepSeek 4.27, Nemotron 4.00,
Qwen3.8-Flash 3.92, Qwen3.8-27B 3.91, Gemma 3.63, gpt-oss-120b 3.57 (1–5).

Full report with per-task results, defects, tool errors and rejections:
[results/v0.3/report.md](results/v0.3/report.md).

### What stands out

- **Sum rows work now.** Office Documents 0.3.1 keeps a formula the model writes into a row of a formula column
  (net, VAT and gross below the items); 0.3.0 replaced it with the line item formula, so the totals showed 0. The
  four tasks with such rows (`anfrage`, `preisaenderung`, `bueromaterial`, `angebot`) succeed in 70 of 84 runs
  over all models (v0.2: 48, v0.1: 41); `preisaenderung` alone goes from 8 to 20 of 21.
- **Fewer rounds lost to broken JSON.** 0.3.1 repairs swapped and extra closing brackets and stray quotes.
  Nemotron 3.5 Super had 49 calls with invalid JSON in v0.2 and 3 runs at the round limit; in v0.3 it has 1 and
  none.
- **`quartal` comes with its numbers now.** Version 1 asked for slides „zu den Zahlen von Q3 2026“ without giving
  any: Haiku asked for them and failed, Gemma, gpt-oss and Nemotron invented figures without saying so and passed.
  With the numbers attached (version 2), 17 of 21 runs pass; most failures leave the wrong customer out of the top
  five.
- **The percent trap stays fixed** (since 0.2.0): `anfrage` 13 of 21 runs right (v0.1: 2 of 21).
- **Most changes between runs are noise.** Paired by task against v0.2 (without `quartal`), gpt-oss-120b's +10
  points (+1 to +18) and Qwen3.8-27B's +8 (0 to +16) are at the edge of what chance explains; the others are within
  ±4. Haiku leads, DeepSeek follows at a quarter of the cost, Nemotron, Qwen3.8-27B and Qwen3.8-Flash overlap,
  gpt-oss and Gemma are clearly behind.
- **Calling the tool is not the problem.** Every model ends with a file in 95–100 % of the file tasks. The
  failures are in the content: missing values and topics, wrong group sums, dates on the wrong weekday.
- **gpt-oss-120b** still hits the limit of 8 tool rounds in 7 runs; only 70 of its 120 calls rejected by the
  tool's content validation are followed by a file.
- **Qwen3.8-Flash** builds more files than needed in 32 of 150 runs (a new file for each small fix); **Haiku** twice
  sent a second, empty "Test" workbook in the same round, which then counts as the delivered file.

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
- **The tool** is vendored unchanged (`src/officebench/tool/`, Office Documents 0.3.1, plugin commit `0386886`),
  with the function specs frozen as Open WebUI 0.11.4 sends them. The model only fills in JSON arguments; fixed code builds the file.
- **The content check** has over 40 checks: required values and topics, formulas and their results after
  recalculation, total rows, weekdays and public holidays, numbers without a source, placeholders, retained
  content in follow-ups and more. A hard defect means the file is not usable as delivered; soft defects are
  reported but do not decide success. Each task's reference solution passes its checks; of 202 mutants the tool
  itself sends back or repairs 8, and the checks catch 178 of the other 194.
- **The quality review** grades blind: neutral ids, neutral file timestamps, one file per request.

## Data

`results/v0.3/`, `results/v0.2/` and `results/v0.1/` hold, per model, `meta.json` (model config, profile, tool and task hashes),
`log.jsonl` (every round: tokens, cost, provider, tool calls and their results; reasoning is not stored) and
`results.jsonl` (the scored runs), plus the report; `results/v0.1/grades.jsonl` has all 696 quality grades with
reasons, in German. The built files (the documents plus the raw arguments of every tool call) are release
downloads (`v0.3-files.zip`, `v0.2-files.zip`, `v0.1-files.zip`): unzip them into the matching folder to rerun the content check.

## License

MIT, see [LICENSE](LICENSE). The vendored Office Documents tool is MIT as well.
