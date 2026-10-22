# Report (2026-10-22)

Runs:
- `claude-haiku-5.5-medium` (results/v0.3/claude-haiku-5.5-medium): Claude Haiku 5.5, thinking medium, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 48c4834d4039, harness 0.3.0+v0.2-1-gd9df0fc
- `deepseek-v4-flash-high` (results/v0.3/deepseek-v4-flash-high): DeepSeek V4 Flash 0731, thinking high, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 48c4834d4039, harness 0.3.0+v0.2-1-gd9df0fc
- `gemma-4-31b` (results/v0.3/gemma-4-31b): Gemma 4 31B, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 48c4834d4039, harness 0.3.0+v0.2-1-gd9df0fc
- `gpt-oss-120b-medium` (results/v0.3/gpt-oss-120b-medium): gpt-oss-120b, reasoning medium, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 48c4834d4039, harness 0.3.0+v0.2-1-gd9df0fc
- `nemotron-3.5-super` (results/v0.3/nemotron-3.5-super): Nemotron 3.5 Super VL, thinking on, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 48c4834d4039, harness 0.3.0+v0.2-1-gd9df0fc
- `qwen3.8-27b-medium` (results/v0.3/qwen3.8-27b-medium): Qwen3.8-27B, thinking medium, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 48c4834d4039, harness 0.3.0+v0.2-1-gd9df0fc
- `qwen3.8-flash-medium` (results/v0.3/qwen3.8-flash-medium): Qwen3.8-Flash, thinking medium, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 48c4834d4039, harness 0.3.0+v0.2-1-gd9df0fc

## Rates

| model | scored runs | file at 1st call | file at end | content ok | clean | success | pass^2 (success) | pass^k (success) |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-5.5-medium | 150 (50 tasks) | 90 % (82–96) · 116/129 | 98 % (95–100) · 127/129 | 96 % (91–100) · 124/129 | 60 % (47–73) · 77/129 | 96 % (91–99) · 144/150 | 93 % | k=3: 90 % |
| deepseek-v4-flash-high | 150 (50 tasks) | 95 % (90–99) · 123/129 | 100 % (100–100; Wilson 97–100) · 129/129 | 94 % (87–99) · 121/129 | 57 % (45–71) · 74/129 | 93 % (87–99) · 140/150 | 90 % | k=3: 88 % |
| gemma-4-31b | 150 (50 tasks) | 69 % (57–81) · 89/129 | 100 % (100–100; Wilson 97–100) · 129/129 | 62 % (49–75) · 80/129 | 38 % (26–51) · 49/129 | 65 % (52–77) · 97/150 | 57 % | k=3: 54 % |
| gpt-oss-120b-medium | 150 (50 tasks) | 78 % (67–89) · 101/129 | 94 % (87–99) · 121/129 | 70 % (57–82) · 90/129 | 36 % (22–49) · 46/129 | 69 % (57–80) · 103/150 | 57 % | k=3: 52 % |
| nemotron-3.5-super | 150 (50 tasks) | 93 % (86–98) · 120/129 | 100 % (100–100; Wilson 97–100) · 129/129 | 88 % (79–96) · 114/129 | 46 % (33–60) · 59/129 | 87 % (78–94) · 130/150 | 80 % | k=3: 76 % |
| qwen3.8-27b-medium | 150 (50 tasks) | 81 % (72–90) · 105/129 | 100 % (100–100; Wilson 97–100) · 129/129 | 84 % (75–93) · 109/129 | 48 % (36–60) · 62/129 | 85 % (76–93) · 127/150 | 77 % | k=3: 70 % |
| qwen3.8-flash-medium | 150 (50 tasks) | 81 % (71–90) · 105/129 | 100 % (100–100; Wilson 97–100) · 129/129 | 86 % (78–94) · 111/129 | 48 % (36–60) · 62/129 | 85 % (77–92) · 127/150 | 73 % | k=3: 64 % |

## Operations

| model | median time to file | mean rounds to file | mean tokens in / out | cost total | cost per success | server errors | outages (not scored) | missing (no log line) | no final answer | round limit | claims file without file | links in the reply | more files than needed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5.5-medium | 12 s | 1.09 | 17130 / 5335 | $ 0.657 | $ 0.0046 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| deepseek-v4-flash-high | 16 s | 1.05 | 11724 / 4953 | $ 0.162 | $ 0.0012 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| gemma-4-31b | 22 s | 1.44 | 11135 / 1703 | $ 0.336 | $ 0.0035 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| gpt-oss-120b-medium | 9 s | 1.56 | 12802 / 3260 | $ 0.436 | $ 0.0042 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 |
| nemotron-3.5-super | 6 s | 1.07 | 11291 / 4674 | $ 0.528 | $ 0.0041 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| qwen3.8-27b-medium | 15 s | 1.19 | 12739 / 3768 | $ 0.277 | $ 0.0022 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 |
| qwen3.8-flash-medium | 33 s | 1.21 | 15961 / 4609 | $ 0.444 | $ 0.0035 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 32 |

Time to file: model time (sum of the round durations without retry pauses) up to the first built file. Costs as reported by the API (missing for local servers).

## Tool rejections and recovery

| model | runs with a rejection: file after it | invalid JSON | schema / required field | garbled arguments | tool's content validation | wrong function |
|---|---|---|---|---|---|---|
| claude-haiku-5.5-medium | 12/13 | 3/3 | 0/1 | – | 12/13 | – |
| deepseek-v4-flash-high | 11/11 | – | – | – | 17/17 | – |
| gemma-4-31b | 43/43 | 5/5 | 7/7 | 167/167 | 36/36 | – |
| gpt-oss-120b-medium | 22/30 | 1/8 | – | – | 70/127 | – |
| nemotron-3.5-super | 11/11 | 1/1 | – | – | 10/10 | – |
| qwen3.8-27b-medium | 26/27 | 8/8 | 3/3 | – | 16/16 | 0/1 |
| qwen3.8-flash-medium | 36/36 | 14/14 | 6/6 | – | 22/22 | – |

Cell per category: rejected calls after which a file came in the same turn / all rejected calls.

## Follow-ups, tasks without a file, extra tools

| model | follow-up: all turns fulfilled | no file: unnecessary office call | no file: reply topics there | with file: reply check passed | extra tool called (runs / offered) | reply truncated |
|---|---|---|---|---|---|---|
| claude-haiku-5.5-medium | 18/18 | 0/21 | 21/21 | 2/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| deepseek-v4-flash-high | 18/18 | 2/21 | 21/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| gemma-4-31b | 18/18 | 0/21 | 18/21 | 2/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| gpt-oss-120b-medium | 18/18 | 1/21 | 14/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 1 |
| nemotron-3.5-super | 18/18 | 3/21 | 18/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| qwen3.8-27b-medium | 18/18 | 0/21 | 18/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| qwen3.8-flash-medium | 18/18 | 2/21 | 19/21 | 2/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |

Unnecessary office call: the office tool was called in a turn that expects no file. Whether an extra tool should be called is set per task ([behavior]). Reply check: [reply] topics there and nothing forbidden in the final answer. Reply truncated: the log keeps 4000 characters; counted for tasks with a reply check.

## Most common defects

| model | files checked | hard defects (runs) | soft defects (runs) | numbers without source |
|---|---|---|---|---|
| claude-haiku-5.5-medium | 127 | too few rows (2), no total row (2), no chart (2), no formula (1), missing months (1), too few sheets (1) | placeholder (17), markdown in reply (9), missing topic (8), date on a weekend (8), number without source (7), rather short (6) | 0.8 · 7/57 |
| deepseek-v4-flash-high | 129 | missing topic (5), missing value (1), summary does not match (1), forbidden content (1), very short (1) | number without source (10), missing topic (9), markdown in reply (9), placeholder (8), date on a weekend (8), incomplete sum range (7) | 0.8 · 10/57 |
| gemma-4-31b | 129 | missing topic (18), missing value (15), no total row (9), no chart (8), summary does not match (8), no formula (5) | missing topic (16), placeholder (11), markdown in reply (9), rather short (9), number without source (8), date on a weekend (7) | 0.6 · 8/57 |
| gpt-oss-120b-medium | 121 | missing topic (10), missing value (9), very short (8), missing topic in reply (7), wrong chart values (3), no total row (3) | missing topic (21), date on a weekend (14), number without source (11), markdown in reply (9), date not on a workday (9), placeholder (7) | 0.7 · 11/56 |
| nemotron-3.5-super | 129 | very short (7), missing topic in reply (3), missing value (2), summary does not match (2), wrong weekday (2), missing topic (2) | placeholder (13), date on a weekend (11), missing topic (10), number without source (10), markdown in reply (9), number as text (4) | 0.7 · 10/57 |
| qwen3.8-27b-medium | 129 | wrong weekday (5), missing value (4), missing topic (4), summary does not match (3), missing topic in reply (3), wrong chart values (2) | date on a weekend (16), number without source (13), placeholder (8), markdown in reply (8), missing topic (7), rather short (5) | 1.0 · 13/57 |
| qwen3.8-flash-medium | 129 | foreign script (4), missing value (4), forbidden content (4), missing topic in reply (3), missing prices (2), wrong chart values (2) | number without source (16), date on a weekend (15), incomplete sum range (12), markdown in reply (9), number as text (5), placeholder (5) | 1.5 · 16/57 |

Defects of the content check, the reply and the behavior checks; per label the number of runs. Numbers without source (numbers_sourced): mean per checked file · files with at least one / checked files.

## Per task

| task | claude-haiku-5.5-medium | deepseek-v4-flash-high | gemma-4-31b | gpt-oss-120b-medium | nemotron-3.5-super | qwen3.8-27b-medium | qwen3.8-flash-medium |
|---|---|---|---|---|---|---|---|
| anfrage: Quote for a customer inquiry (attachment) | 1·3·3/3 | 2·3·2/3 | 3·3·0/3 | 1·3·3/3 | 1·3·2/3 | 2·3·2/3 | 2·3·1/3 |
| angebot: Quote calculation | 3·3·3/3 | 3·3·3/3 | 0·3·3/3 | 3·3·3/3 | 3·3·3/3 | 1·3·3/3 | 3·3·3/3 |
| angebotsvergleich: Decision paper from two offers (attachments) | 3·3·3/3 | 3·3·3/3 | 3·3·1/3 | 3·3·2/3 | 3·3·3/3 | 3·3·2/3 | 3·3·3/3 |
| anweisung: Work instruction | 3·3·3/3 | 3·3·3/3 | 1·3·2/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 2·3·2/3 |
| arbeitstage: Question: working days in Excel (no_file) | –·–·3/3 | –·–·1/3 | –·–·3/3 | –·–·3/3 | –·–·0/3 | –·–·3/3 | –·–·2/3 |
| auftragsdaten: Q3 order analysis from an export (attachment) | 2·3·3/3 | 3·3·3/3 | 1·3·0/3 | 0·2·0/3 | 3·3·2/3 | 2·3·3/3 | 3·3·2/3 |
| aushang: Tea kitchen notice (vague) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| bahncard: Question with web search: BahnCard (no_file) | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 |
| befragung: Employee survey (follow-up) (follow_up) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 0·3·3/3 |
| budget: Budget | 3·3·2/3 | 2·3·3/3 | 0·3·0/3 | 0·2·2/3 | 1·3·2/3 | 3·3·3/3 | 2·3·3/3 |
| bueromaterial: Office supplies order list (follow-up) (follow_up) | 2·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·0/3 | 3·3·2/3 | 3·3·3/3 | 2·3·2/3 |
| einladung: Christmas party invitation | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 | 3·3·1/3 | 3·3·2/3 | 3·3·3/3 |
| filialumsatz: Branch revenue from an email (copying data) | 2·3·3/3 | 3·3·3/3 | 0·3·1/3 | 1·3·3/3 | 3·3·3/3 | 2·3·2/3 | 1·3·3/3 |
| handbuch: Onboarding handbook (long) | 3·3·3/3 | 3·3·3/3 | 3·3·0/3 | 3·3·0/3 | 3·3·1/3 | 2·3·3/3 | 3·3·2/3 |
| homeoffice: Circular email from a long works agreement (attachment, no file) (no_file) | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·1/3 | –·–·3/3 | –·–·3/3 | –·–·2/3 |
| inventar: IT inventory list (long) | 2·3·2/3 | 3·3·2/3 | 1·3·0/3 | 2·3·0/3 | 2·3·3/3 | 3·3·2/3 | 1·3·3/3 |
| jahresbericht: Slides from a long annual report with correction (attachment) | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 |
| konzept: Concept paper | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 | 3·3·3/3 | 0·3·3/3 | 1·3·3/3 |
| kostenumlage: Allocate building costs (two keys) | 3·3·3/3 | 2·3·3/3 | 1·3·1/3 | 1·3·3/3 | 3·3·3/3 | 1·3·1/3 | 3·3·2/3 |
| kundenantwort: Reply to a complaint (attachment, no file) (no_file) | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 |
| leasing: Question: lease or buy (no_file) | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·2/3 | –·–·2/3 | –·–·3/3 | –·–·3/3 |
| mahnung: Payment reminder (overdue only) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| planist: Plan vs. actual per cost centre (follow-up, three rounds) (follow_up) | 3·3·3/3 | 3·3·3/3 | 3·3·0/3 | 2·3·3/3 | 2·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| praesentation: Presentation | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 0·1·1/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 |
| preisaenderung: Quote with price list and price change (two attachments) | 2·3·3/3 | 3·3·3/3 | 3·3·2/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| projektplan: Project plan for an office move | 1·3·3/3 | 3·3·3/3 | 3·3·1/3 | 3·3·1/3 | 3·3·3/3 | 1·3·3/3 | 3·3·3/3 |
| projektstatus: ERP project status | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 2·3·2/3 |
| protokoll: Meeting minutes | 3·3·3/3 | 3·3·3/3 | 1·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·0/3 | 2·3·2/3 |
| provision: Sales commission statement with tiers and bonus | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 1·3·3/3 |
| quartal: Quarterly presentation | 1·1·1/3 | 3·3·3/3 | 3·3·2/3 | 2·2·2/3 | 3·3·3/3 | 2·3·3/3 | 2·3·3/3 |
| reisekosten: Travel expenses | 2·3·3/3 | 3·3·3/3 | 1·3·2/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 |
| richtlinie: Remote work policy (two change rounds) (follow_up) | 3·3·3/3 | 3·3·1/3 | 3·3·0/3 | 3·3·1/3 | 3·3·0/3 | 3·3·2/3 | 3·3·3/3 |
| rufbereitschaft: On-call rota November/December (holidays, substitute) | 3·3·3/3 | 2·3·3/3 | 0·3·0/3 | 3·3·1/3 | 3·3·1/3 | 3·3·1/3 | 2·3·1/3 |
| rundschreiben: Staff circular | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 |
| schulung: Phishing training | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 0·0·0/3 | 3·3·3/3 | 3·3·3/3 | 2·3·2/3 |
| servicebericht: Slides from a report (attachment) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·1/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| sparquote: Budget with savings rate (follow-up) (follow_up) | 2·3·3/3 | 2·3·3/3 | 1·3·0/3 | 0·3·3/3 | 2·3·3/3 | 2·3·2/3 | 3·3·3/3 |
| stellenanzeige: Job ad for a service technician (AGG-compliant) | 3·3·3/3 | 3·3·3/3 | 2·3·1/3 | 3·3·2/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| teamnotizen: Minutes from notes (attachment) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 |
| termin: Calendar entry and an invitation to send yourself (no_file) | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·0/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 |
| transkript: Decision minutes from a transcript (attachment) | 3·3·3/3 | 3·3·3/3 | 1·3·1/3 | 3·3·1/3 | 3·3·3/3 | 2·3·2/3 | 3·3·1/3 |
| urlaubsplanung: Vacation planning (vague) | 3·3·3/3 | 3·3·3/3 | 1·3·3/3 | 2·3·2/3 | 3·3·3/3 | 1·3·3/3 | 2·3·2/3 |
| vergleich: Laptop comparison | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 0·3·3/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 |
| versammlung: Staff meeting (follow-up) (follow_up) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| vertrieb: Revenue by region (year-on-year) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 | 3·3·3/3 | 3·3·2/3 | 3·3·3/3 |
| wartungsmail: Server maintenance email (no_file) | –·–·3/3 | –·–·3/3 | –·–·0/3 | –·–·1/3 | –·–·2/3 | –·–·0/3 | –·–·1/3 |
| wartungsvertrag: Overview of a long maintenance contract (attachment) | 3·3·2/3 | 3·3·2/3 | 0·3·0/3 | 3·3·1/3 | 2·3·3/3 | 3·3·3/3 | 2·3·3/3 |
| workshop: Workshop agenda with times | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 | 3·3·3/3 |
| zeiterfassung: Time sheet with macro request | 3·3·2/3 | 2·3·3/3 | 3·3·1/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 3·3·2/3 |
| zeugnis: Employment reference (grade good) | 3·3·3/3 | 3·3·0/3 | 2·3·1/3 | 3·3·0/3 | 3·3·1/3 | 3·3·0/3 | 3·3·1/3 |

Cell: file at 1st call · file at end · success / scored runs (? = success not determinable, e.g. the file of the last call is missing).

---

Rates: estimate = mean over tasks of the per-task rate, 95 % interval from a cluster bootstrap over tasks (runs of one task are not independent), then the raw count. When the interval has zero width (all values equal), the Wilson interval is added (it treats runs as independent). File columns only count tasks that ask for a file; success counts all. Success = file at end, every turn fulfilled and content ok (no hard defect), plus the reply check and the behavior check where the task has them; without a file: no office call, a final answer with every required topic and nothing forbidden. Not scored: runs that a provider or network failure ended before the outcome was settled, and task runs without a log line. Server errors of the model's own server count as failures. pass^k: chance that k fresh runs of a task all succeed (mean over tasks). Details: docs/scoring.md.
