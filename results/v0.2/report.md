# Report (2026-10-22)

Runs:
- `claude-haiku-5.5-medium` (results/v0.2/claude-haiku-5.5-medium): Claude Haiku 5.5, thinking medium, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 5358e74f55a9, harness 0.2.0+v0.1.1-2-gbb4bfe8
- `deepseek-v4-flash-high` (results/v0.2/deepseek-v4-flash-high): DeepSeek V4 Flash 0731, thinking high, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 5358e74f55a9, harness 0.2.0+v0.1.1-2-gbb4bfe8
- `gemma-4-31b` (results/v0.2/gemma-4-31b): Gemma 4 31B, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 5358e74f55a9, harness 0.2.0+v0.1.1-2-gbb4bfe8
- `gpt-oss-120b-medium` (results/v0.2/gpt-oss-120b-medium): gpt-oss-120b, reasoning medium, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 5358e74f55a9, harness 0.2.0+v0.1.1-2-gbb4bfe8
- `nemotron-3.5-super` (results/v0.2/nemotron-3.5-super): Nemotron 3.5 Super VL, thinking on, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 5358e74f55a9, harness 0.2.0+v0.1.1-2-gbb4bfe8
- `qwen3.8-27b-medium` (results/v0.2/qwen3.8-27b-medium): Qwen3.8-27B, thinking medium, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 5358e74f55a9, harness 0.2.0+v0.1.1-2-gbb4bfe8
- `qwen3.8-flash-medium` (results/v0.2/qwen3.8-flash-medium): Qwen3.8-Flash, thinking medium, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 5358e74f55a9, harness 0.2.0+v0.1.1-2-gbb4bfe8

## Rates

| model | scored runs | file at 1st call | file at end | content ok | clean | success | pass^2 (success) | pass^k (success) |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-5.5-medium | 150 (50 tasks) | 89 % (81–96) · 115/129 | 99 % (97–100) · 128/129 | 96 % (91–100) · 124/129 | 57 % (44–71) · 74/129 | 96 % (91–99) · 144/150 | 93 % | k=3: 90 % |
| deepseek-v4-flash-high | 150 (50 tasks) | 91 % (83–97) · 117/129 | 100 % (100–100; Wilson 97–100) · 129/129 | 92 % (84–98) · 119/129 | 61 % (48–74) · 79/129 | 91 % (84–97) · 137/150 | 86 % | k=3: 82 % |
| gemma-4-31b | 150 (50 tasks) | 71 % (59–84) · 92/129 | 98 % (95–100) · 127/129 | 58 % (44–71) · 75/129 | 32 % (19–45) · 41/129 | 62 % (49–74) · 93/150 | 56 % | k=3: 54 % |
| gpt-oss-120b-medium | 150 (50 tasks) | 78 % (65–89) · 100/129 | 93 % (86–98) · 120/129 | 60 % (48–73) · 78/129 | 32 % (20–44) · 41/129 | 60 % (49–71) · 90/150 | 45 % | k=3: 36 % |
| nemotron-3.5-super | 150 (50 tasks) | 91 % (82–98) · 117/129 | 98 % (93–100) · 126/129 | 85 % (76–94) · 110/129 | 50 % (36–64) · 64/129 | 86 % (77–93) · 129/150 | 79 % | k=3: 74 % |
| qwen3.8-27b-medium | 150 (50 tasks) | 82 % (72–91) · 106/129 | 100 % (100–100; Wilson 97–100) · 129/129 | 79 % (68–89) · 102/129 | 47 % (35–60) · 61/129 | 79 % (69–87) · 118/150 | 65 % | k=3: 56 % |
| qwen3.8-flash-medium | 150 (50 tasks) | 78 % (67–88) · 100/129 | 100 % (100–100; Wilson 97–100) · 129/129 | 88 % (78–95) · 113/129 | 57 % (45–71) · 74/129 | 88 % (80–95) · 132/150 | 80 % | k=3: 74 % |

## Operations

| model | median time to file | mean rounds to file | mean tokens in / out | cost total | cost per success | server errors | outages (not scored) | missing (no log line) | no final answer | round limit | claims file without file | links in the reply | more files than needed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5.5-medium | 12 s | 1.11 | 16928 / 5331 | $ 0.654 | $ 0.0045 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |
| deepseek-v4-flash-high | 10 s | 1.11 | 11905 / 4916 | $ 0.158 | $ 0.0012 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| gemma-4-31b | 33 s | 1.46 | 11352 / 1552 | $ 0.332 | $ 0.0036 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 1 |
| gpt-oss-120b-medium | 8 s | 1.59 | 13172 / 3316 | $ 0.446 | $ 0.0050 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 |
| nemotron-3.5-super | 6 s | 1.20 | 15545 / 5380 | $ 0.593 | $ 0.0046 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 |
| qwen3.8-27b-medium | 19 s | 1.22 | 13666 / 4006 | $ 0.299 | $ 0.0025 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12 |
| qwen3.8-flash-medium | 38 s | 1.33 | 16433 / 4951 | $ 0.471 | $ 0.0036 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 36 |

Time to file: model time (sum of the round durations without retry pauses) up to the first built file. Costs as reported by the API (missing for local servers).

## Tool rejections and recovery

| model | runs with a rejection: file after it | invalid JSON | schema / required field | garbled arguments | tool's content validation |
|---|---|---|---|---|---|
| claude-haiku-5.5-medium | 14/15 | 11/11 | 1/1 | – | 5/6 |
| deepseek-v4-flash-high | 16/16 | 2/2 | – | – | 19/19 |
| gemma-4-31b | 36/38 | 5/5 | 8/8 | 20/36 | 33/33 |
| gpt-oss-120b-medium | 22/31 | 0/3 | – | – | 73/149 |
| nemotron-3.5-super | 14/17 | 25/49 | – | – | 6/6 |
| qwen3.8-27b-medium | 26/26 | 17/17 | 3/3 | – | 16/16 |
| qwen3.8-flash-medium | 35/35 | 22/22 | 3/3 | – | 23/23 |

Cell per category: rejected calls after which a file came in the same turn / all rejected calls.

## Follow-ups, tasks without a file, extra tools

| model | follow-up: all turns fulfilled | no file: unnecessary office call | no file: reply topics there | with file: reply check passed | extra tool called (runs / offered) | reply truncated |
|---|---|---|---|---|---|---|
| claude-haiku-5.5-medium | 18/18 | 0/21 | 21/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| deepseek-v4-flash-high | 18/18 | 2/21 | 20/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| gemma-4-31b | 18/18 | 0/21 | 18/21 | 1/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| gpt-oss-120b-medium | 17/18 | 3/21 | 15/21 | 2/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 1 |
| nemotron-3.5-super | 18/18 | 2/21 | 21/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| qwen3.8-27b-medium | 18/18 | 1/21 | 18/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| qwen3.8-flash-medium | 18/18 | 0/21 | 19/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |

Unnecessary office call: the office tool was called in a turn that expects no file. Whether an extra tool should be called is set per task ([behavior]). Reply check: [reply] topics there and nothing forbidden in the final answer. Reply truncated: the log keeps 4000 characters; counted for tasks with a reply check.

## Most common defects

| model | files checked | hard defects (runs) | soft defects (runs) | numbers without source |
|---|---|---|---|---|
| claude-haiku-5.5-medium | 128 | missing value (3), forbidden content in reply (1), missing topic (1) | placeholder (20), number without source (9), markdown in reply (9), date on a weekend (9), missing topic (8), rather short (5) | 1.0 · 9/57 |
| deepseek-v4-flash-high | 129 | very short (3), missing topic (3), missing value (2), forbidden content (2), no total row (1), sections not numbered (1) | missing topic (11), number without source (10), markdown in reply (9), placeholder (8), date on a weekend (6), incomplete sum range (5) | 0.8 · 10/57 |
| gemma-4-31b | 127 | missing value (21), missing topic (19), no formula (10), no chart (8), summary does not match (7), no total row (7) | missing topic (16), placeholder (14), rather short (10), markdown in reply (9), date not on a workday (8), date on a weekend (8) | 0.7 · 7/57 |
| gpt-oss-120b-medium | 120 | missing value (17), missing topic (12), very short (10), missing topic in reply (7), no total row (4), no chart (3) | missing topic (19), placeholder (14), date on a weekend (13), markdown in reply (9), date not on a workday (8), number without source (6) | 0.3 · 6/55 |
| nemotron-3.5-super | 126 | very short (7), summary does not match (4), missing topic (2), wrong chart values (1), missing value (1), no total row (1) | placeholder (11), number without source (10), date on a weekend (10), missing topic (9), markdown in reply (9), number as text (4) | 0.9 · 10/55 |
| qwen3.8-27b-medium | 129 | missing value (8), missing topic (6), wrong weekday (5), no total row (3), missing topic in reply (3), forbidden content (3) | number without source (14), date on a weekend (12), placeholder (10), markdown in reply (9), missing topic (8), incomplete sum range (4) | 0.9 · 14/57 |
| qwen3.8-flash-medium | 129 | forbidden content (5), missing topic (4), missing prices (2), missing topic in reply (2), missing value (2), wrong weekday (2) | number without source (16), date on a weekend (13), markdown in reply (9), incomplete sum range (8), placeholder (6), slides added (3) | 1.5 · 16/57 |

Defects of the content check, the reply and the behavior checks; per label the number of runs. Numbers without source (numbers_sourced): mean per checked file · files with at least one / checked files.

## Per task

| task | claude-haiku-5.5-medium | deepseek-v4-flash-high | gemma-4-31b | gpt-oss-120b-medium | nemotron-3.5-super | qwen3.8-27b-medium | qwen3.8-flash-medium |
|---|---|---|---|---|---|---|---|
| anfrage: Quote for a customer inquiry (attachment) | 3·3·2/3 | 0·3·2/3 | 3·3·0/3 | 1·3·0/3 | 2·3·3/3 | 2·3·2/3 | 1·3·1/3 |
| angebot: Quote calculation | 2·3·3/3 | 3·3·2/3 | 0·3·3/3 | 3·3·3/3 | 0·2·2/3 | 3·3·2/3 | 3·3·3/3 |
| angebotsvergleich: Decision paper from two offers (attachments) | 3·3·3/3 | 3·3·3/3 | 3·3·1/3 | 3·3·1/3 | 3·3·3/3 | 2·3·2/3 | 3·3·3/3 |
| anweisung: Work instruction | 3·3·3/3 | 3·3·3/3 | 1·3·3/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 1·3·3/3 |
| arbeitstage: Question: working days in Excel (no_file) | –·–·3/3 | –·–·2/3 | –·–·3/3 | –·–·2/3 | –·–·1/3 | –·–·2/3 | –·–·3/3 |
| auftragsdaten: Q3 order analysis from an export (attachment) | 2·3·3/3 | 3·3·3/3 | 0·3·0/3 | 1·3·0/3 | 2·3·2/3 | 3·3·3/3 | 2·3·3/3 |
| aushang: Tea kitchen notice (vague) | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| bahncard: Question with web search: BahnCard (no_file) | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 |
| befragung: Employee survey (follow-up) (follow_up) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| budget: Budget | 3·3·3/3 | 3·3·3/3 | 1·3·0/3 | 0·3·3/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 |
| bueromaterial: Office supplies order list (follow-up) (follow_up) | 2·3·3/3 | 3·3·3/3 | 3·3·0/3 | 3·3·0/3 | 3·3·2/3 | 3·3·1/3 | 2·3·3/3 |
| einladung: Christmas party invitation | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 | 3·3·3/3 | 1·3·1/3 | 3·3·3/3 |
| filialumsatz: Branch revenue from an email (copying data) | 1·3·3/3 | 3·3·3/3 | 2·3·2/3 | 0·1·1/3 | 2·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| handbuch: Onboarding handbook (long) | 3·3·3/3 | 2·3·3/3 | 2·3·0/3 | 3·3·0/3 | 3·3·1/3 | 1·3·2/3 | 2·3·3/3 |
| homeoffice: Circular email from a long works agreement (attachment, no file) (no_file) | –·–·2/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·2/3 | –·–·2/3 |
| inventar: IT inventory list (long) | 2·3·3/3 | 3·3·3/3 | 2·3·0/3 | 0·2·1/3 | 3·3·2/3 | 2·3·3/3 | 2·3·2/3 |
| jahresbericht: Slides from a long annual report with correction (attachment) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| konzept: Concept paper | 3·3·3/3 | 2·3·3/3 | 2·3·3/3 | 3·3·3/3 | 2·3·3/3 | 2·3·3/3 | 1·3·3/3 |
| kostenumlage: Allocate building costs (two keys) | 3·3·3/3 | 3·3·3/3 | 2·3·0/3 | 0·3·3/3 | 3·3·3/3 | 0·3·2/3 | 2·3·2/3 |
| kundenantwort: Reply to a complaint (attachment, no file) (no_file) | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·2/3 | –·–·3/3 | –·–·2/3 | –·–·3/3 |
| leasing: Question: lease or buy (no_file) | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·1/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 |
| mahnung: Payment reminder (overdue only) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 |
| planist: Plan vs. actual per cost centre (follow-up, three rounds) (follow_up) | 3·3·3/3 | 2·3·3/3 | 3·3·2/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 | 3·3·2/3 |
| praesentation: Presentation | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 0·1·1/3 | 3·3·3/3 | 3·3·2/3 | 1·3·3/3 |
| preisaenderung: Quote with price list and price change (two attachments) | 3·3·1/3 | 2·3·2/3 | 3·3·0/3 | 3·3·0/3 | 3·3·2/3 | 3·3·0/3 | 3·3·3/3 |
| projektplan: Project plan for an office move | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·0/3 | 3·3·2/3 | 3·3·3/3 | 3·3·3/3 |
| projektstatus: ERP project status | 3·3·3/3 | 3·3·3/3 | 1·3·3/3 | 3·3·3/3 | 3·3·3/3 | 1·3·3/3 | 1·3·3/3 |
| protokoll: Meeting minutes | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·1/3 | 3·3·2/3 |
| provision: Sales commission statement with tiers and bonus | 2·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 | 3·3·3/3 |
| quartal: Quarterly presentation | 2·2·2/3 | 3·3·3/3 | 3·3·3/3 | 2·2·2/3 | 2·3·3/3 | 3·3·3/3 | 2·3·3/3 |
| reisekosten: Travel expenses | 2·3·3/3 | 2·3·3/3 | 3·3·1/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| richtlinie: Remote work policy (two change rounds) (follow_up) | 3·3·3/3 | 3·3·1/3 | 3·3·0/3 | 3·3·0/3 | 3·3·0/3 | 1·3·3/3 | 3·3·3/3 |
| rufbereitschaft: On-call rota November/December (holidays, substitute) | 3·3·3/3 | 3·3·3/3 | 0·3·0/3 | 3·3·1/3 | 3·3·1/3 | 3·3·1/3 | 3·3·1/3 |
| rundschreiben: Staff circular | 3·3·3/3 | 3·3·3/3 | 1·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| schulung: Phishing training | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 0·1·1/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 |
| servicebericht: Slides from a report (attachment) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 2·3·2/3 | 1·3·3/3 |
| sparquote: Budget with savings rate (follow-up) (follow_up) | 1·3·3/3 | 2·3·3/3 | 0·3·0/3 | 0·2·2/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| stellenanzeige: Job ad for a service technician (AGG-compliant) | 3·3·3/3 | 3·3·3/3 | 3·3·1/3 | 3·3·2/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| teamnotizen: Minutes from notes (attachment) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| termin: Calendar entry and an invitation to send yourself (no_file) | –·–·3/3 | –·–·2/3 | –·–·3/3 | –·–·1/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 |
| transkript: Decision minutes from a transcript (attachment) | 3·3·3/3 | 3·3·3/3 | 1·3·1/3 | 3·3·0/3 | 3·3·3/3 | 2·3·2/3 | 1·3·1/3 |
| urlaubsplanung: Vacation planning (vague) | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 | 1·3·2/3 | 2·3·2/3 | 1·3·3/3 | 0·3·3/3 |
| vergleich: Laptop comparison | 2·3·3/3 | 3·3·3/3 | 0·3·2/3 | 2·3·2/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| versammlung: Staff meeting (follow-up) (follow_up) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 | 3·3·3/3 | 3·3·1/3 | 3·3·3/3 |
| vertrieb: Revenue by region (year-on-year) | 3·3·3/3 | 3·3·3/3 | 3·3·0/3 | 3·3·2/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 |
| wartungsmail: Server maintenance email (no_file) | –·–·3/3 | –·–·2/3 | –·–·0/3 | –·–·1/3 | –·–·3/3 | –·–·1/3 | –·–·2/3 |
| wartungsvertrag: Overview of a long maintenance contract (attachment) | 3·3·3/3 | 3·3·1/3 | 0·3·1/3 | 3·3·1/3 | 0·1·1/3 | 1·3·2/3 | 1·3·2/3 |
| workshop: Workshop agenda with times | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 2·3·3/3 |
| zeiterfassung: Time sheet with macro request | 1·3·3/3 | 2·3·3/3 | 0·1·1/3 | 3·3·2/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 |
| zeugnis: Employment reference (grade good) | 3·3·2/3 | 3·3·0/3 | 2·3·0/3 | 3·3·0/3 | 3·3·0/3 | 3·3·0/3 | 3·3·0/3 |

Cell: file at 1st call · file at end · success / scored runs (? = success not determinable, e.g. the file of the last call is missing).

---

Rates: estimate = mean over tasks of the per-task rate, 95 % interval from a cluster bootstrap over tasks (runs of one task are not independent), then the raw count. When the interval has zero width (all values equal), the Wilson interval is added (it treats runs as independent). File columns only count tasks that ask for a file; success counts all. Success = file at end, every turn fulfilled and content ok (no hard defect), plus the reply check and the behavior check where the task has them; without a file: no office call, a final answer with every required topic and nothing forbidden. Not scored: runs that a provider or network failure ended before the outcome was settled, and task runs without a log line. Server errors of the model's own server count as failures. pass^k: chance that k fresh runs of a task all succeed (mean over tasks). Details: docs/scoring.md.
