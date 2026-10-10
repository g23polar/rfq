# RFQ-to-Quote Agent: master plan

Product spec: [`../spec.md`](../spec.md) (v2). Submission target: 4:15 PM EDT, Oct 10, 2026.
This file is the index and status tracker. Each task has its own file with goal, contract and acceptance criteria.

## Approach in brief

- **Stack**: Python, one FastAPI process serving a JSON API and a single static HTML page. No frontend build step.
- **Model use**: three places only, all through the Nicrron gateway: splitting free text into lines, reading a line into fields, screening for manipulation. Everything with a right answer is plain code.
- **Shape**: ten stages (spec section 6). Each stage is a function that takes a line and adds to it; issues accumulate on the line and the status is decided from them (spec 7.2).
- **PRISM**: our code records every stage of every run over PRISM's HTTP API. The guardrail, Knowledge Base and evaluator are dashboard-only, so a person configures them (task 17).
- **Data**: synthetic catalog, benchmarks and sample RFQs, labeled as synthetic everywhere.

## Decisions already made

| Decision | Choice |
|---|---|
| Language | Python (`uv`, `pytest`) |
| Interface | Web UI plus JSON API; the UI is required by the spec |
| Models | `anthropic/claude-sonnet-5` for intake and reading, `anthropic/claude-haiku-4-5` for the safety screen, `temperature: 0` |
| PRISM recording | Direct HTTP (`/api/spans/ingest`, `/api/traces`), not the SDK |
| Safety | Our own screen does the withholding; PRISM's guardrail flags the same text on the recorded run |
| Pricing rule | Target = benchmark midpoint x 0.97; floor = cost x 1.12; price = the higher. Proposed values, change in [task 10](10-price.md) |
| Matching | Exact stock sizes only; no cut-to-size |
| Dashboard setup | Done by the user while the code is built |

## Status tracker

Statuses: Not started, In progress, Blocked, Done. Update this table when a task changes state.

| # | Task | Owner | Status | Depends on | Spec requirements |
|---|---|---|---|---|---|
| 01 | [Contracts and skeleton](01-contracts-and-skeleton.md) | Unassigned | Not started | none | all (shared shapes) |
| 02 | [Reference data and catalog](02-reference-data-and-catalog.md) | Unassigned | Not started | 01 | PR-6, MT-6, section 10 |
| 03 | [Fixtures and golden set](03-fixtures-and-golden-set.md) | Unassigned | Not started | 01, 02 | QA-1, section 10 |
| 04 | [Intake](04-intake.md) | Unassigned | Not started | 01, 07 | IN-1 to IN-5 |
| 05 | [Safety screen](05-safety-screen.md) | Unassigned | Not started | 01, 07 | SF-1 to SF-4 |
| 06 | [Line reading](06-line-reading.md) | Unassigned | Not started | 01, 07 | RD-1 to RD-4 |
| 07 | [Model client](07-model-client.md) | Unassigned | Not started | 01 | EV-2 |
| 08 | [Standardize](08-standardize.md) | Unassigned | Not started | 01, 02 | RD-5 to RD-9 |
| 09 | [Match](09-match.md) | Unassigned | Not started | 01, 02 | MT-1 to MT-5 |
| 10 | [Price](10-price.md) | Unassigned | Not started | 01, 02 | PR-1 to PR-7 |
| 11 | [Compliance](11-compliance.md) | Unassigned | Not started | 01, 02 | CP-1 to CP-5 |
| 12 | [Decide and verify](12-decide-and-verify.md) | Unassigned | Not started | 01 | DC-1 to DC-3, VR-1 |
| 13 | [PRISM recording](13-prism-recording.md) | Unassigned | Not started | 01 | VR-4, EV-3, UX-6 |
| 14 | [Pipeline and API](14-pipeline-and-api.md) | Unassigned | Not started | 04 to 13 | DC-4, UX-4, UX-5 |
| 15 | [Web UI](15-web-ui.md) | Unassigned | Not started | 01 | UX-1 to UX-3, UX-6, UX-7 |
| 16 | [Evaluation and README](16-evaluation-and-readme.md) | Unassigned | Not started | 03, 14 | QA-2, QA-3, DC-1 |
| 17 | [PRISM dashboard setup](17-prism-dashboard-setup.md) | User | Not started | 02, 13 | SF-1, MT-6, VR-2, VR-3 |
| 18 | [Submission](18-submission.md) | User | Not started | all | EV-9 |

## Order of work

Tasks in the same wave do not depend on each other and can be worked on at the same time.

| Wave | Tasks | Gate to start |
|---|---|---|
| 0 | 01 | Plan approved |
| 1 | 02, 07, 12, 13, 15 | 01 done: shared shapes and the sample run JSON exist |
| 2 | 03, 04, 05, 06, 08, 09, 10, 11, 17 | 02 and 07 done |
| 3 | 14 | Stages 04 to 13 done |
| 4 | 16, 18 | 14 done |

The critical path is 01 → 07 → 06 → 14 → 16. Task 15 (UI) is the largest single task and can start right after 01 against the sample run JSON, without waiting for any stage.

## Cut order

If scope has to shrink, first to cut is first in the list (from spec R1):

1. Printable export polish (task 14: the print stylesheet)
2. Duplicate linking (task 08)
3. Review queue (task 17)
4. Model-worded questions; templates stay (task 12)
5. Substitution proposals (task 09)
6. Re-quote after an answer (task 14)
7. Spreadsheet intake (task 04)

Never cut: source tracing (06), fixed pricing rule (10), the four statuses (12), PRISM recording, guardrail, evaluator and Knowledge Base claim (13, 17).

## Open items that can change a task

| Item | Affects | Who resolves |
|---|---|---|
| Does the Knowledge Base show a grounded claim, or is it upload-only? (spec Q1) | 17 | Ask the PRISM team |
| Are evaluators available on our workspace plan? | 17 | Check the dashboard |
| Does Nicrron accept `temperature` and JSON output for the chosen models? | 07 | Smoke test in task 07 |
| Does an evaluator on an AI-written output satisfy the event rule? (spec Q6) | 17 | Ask the PRISM team |
| Keys in `.env` (`NICRRON_API_KEY`, `PRISMTRACE_API_KEY`, `PRISMTRACE_PROJECT_ID`) | 07, 13 | User, before wave 1 |
