# RFQ-to-Quote Agent: master plan

Product spec: [`../spec.md`](../spec.md) (version 2.0). Submission target: 4:15 PM EDT, Oct 10, 2026.
This file is the index and status tracker. Each task has its own file with goal, contract and acceptance criteria.

Priority follows the spec's key: **M** = must ship today, **S** = stretch today, **L** = later (pitch only, not planned here). Every task file separates its M scope from its S scope.

## Approach in brief

- **Output is a draft.** The agent produces a reviewable draft quote; a specialist approves it before anything is "ready to send".
- **Answer every line.** Ambiguous lines get priced, labeled alternates plus one question. A line is held only when no reasonable option exists.
- **Two audiences.** Every issue is tagged buyer-facing or internal. Internal problems hold a line for the specialist and never reach the buyer.
- **Stack**: Python, one FastAPI process serving a JSON API and a single static HTML page. No frontend build step.
- **Model use**, all through the Nicrron gateway: segmenting the RFQ, interpreting a line, screening for manipulation, wording buyer questions, and (stretch) choosing among shortlisted catalog items. Everything with a right answer is plain code.
- **PRISM**: our code records every stage of every run over PRISM's HTTP API. The guardrail, Knowledge Base and evaluator are dashboard-only, so a person configures them (task 17).
- **Data**: synthetic catalog, stock, cross-references, benchmarks and sample RFQs, labeled as synthetic everywhere.

## Spec stages and the task that builds each

| Spec stage (section 8) | Task | Tier |
|---|---|---|
| 0 Triage | 04 | S |
| 1 Intake and segmentation | 04 | M |
| 2 Safety screen | 05 | M |
| 3 Interpret | 06 | M |
| 4 Standardize and validate | 08 | M |
| 5 Resolve to catalog | 09 | M (second matching path is S) |
| 6 Availability | 19 | M (lead time is S) |
| 7 Price | 10 | M (surcharge, processing, quantity breaks are S) |
| 8 Compliance | 11 | M |
| 9 Decide | 12 | M |
| 10 Verify | 12 | M |
| 11 Specialist review | 14, 15 | M (approve), S (edit) |
| 12 Assemble | 14 | M |
| 13 Buyer reply loop | 14 | S |
| 14 Learn | not planned | L |

## Decisions already made

| Decision | Choice |
|---|---|
| Language | Python (`uv`, `pytest`) |
| Interface | Web review screen plus JSON API |
| Models | `anthropic/claude-sonnet-5` for segmentation and interpretation, `anthropic/claude-haiku-4-5` for the safety screen and question wording. sonnet-5 rejects `temperature`, so repeatability comes from a local response cache ([07](07-model-client.md)) |
| PRISM recording | Direct HTTP (`/api/spans/ingest`, `/api/traces`), not the SDK |
| Safety | Our own screen does the withholding; PRISM's guardrail flags the same text on the recorded run |
| Dashboard setup | Done by the user while the code is built |
| 304 from dual-certified stock | Stated assumption, no question; alternates only for unclear wording, 304H or "straight 304 only" (spec M2, MT-4 updated) |
| Status precedence ([12](12-decide-and-verify.md)) | Not an item → specialist review → no bid → needs buyer input → alternates → assumptions → quoted. Internal concerns win |
| Pricing values ([10](10-price.md)) | Target = benchmark midpoint x 0.97; margin floor 12%; validity 7 days. A price under the floor is not raised; the line goes to specialist review |
| Benchmarks ([02](02-reference-data-and-catalog.md)) | Keyed by grade and form (spec section 16 updated) |
| Unqualified "domestic" ([11](11-compliance.md)) | The line is priced, the requirement is shown as unknown, and one question asks which rule applies |
| Alternates ([09](09-match.md)) | No limit: every plausible option is priced |
| Buyer questions ([12](12-decide-and-verify.md)) | Worded by the model from a fixed template, checked, with the template as fallback |
| Touchless rate ([16](16-evaluation-and-readme.md)) | Left out of the report until line editing exists |

## Status tracker

Statuses: Not started, In progress, Blocked, Done. Update this table when a task changes state.

As of 13:35 EDT, Oct 10: 12 of 19 done (01 to 12); 04 to 06 and 08 to 12 are must-ship scope only. "Not started" means ready to start: its dependencies are done. "Blocked" means it is waiting on tasks that are not done.

| # | Task | Owner | Status | Depends on | Spec requirements (M) | Stretch in this task (S) |
|---|---|---|---|---|---|---|
| 01 | [Contracts and skeleton](01-contracts-and-skeleton.md) | Claude | Done | none | all (shared shapes) | none |
| 02 | [Reference data and catalog](02-reference-data-and-catalog.md) | Mihir | Done | 01 | Section 16, MT-3, MT-6 | Surcharge table, pipe sizes |
| 03 | [Fixtures and golden set](03-fixtures-and-golden-set.md) | Mihir | Done | 01, 02 | QA-1, section 16 | Spreadsheet fixture |
| 04 | [Intake and segmentation](04-intake.md) | Mihir | Done (M) | 01, 07 | IN-1, IN-3 to IN-6 | IN-1 spreadsheet, IN-2, IN-7 |
| 05 | [Safety screen](05-safety-screen.md) | Mihir | Done (M) | 01, 07 | SF-1 to SF-3 | none |
| 06 | [Interpret](06-line-reading.md) | Mihir | Done (M) | 01, 07 | RD-1 to RD-4 | none |
| 07 | [Model client](07-model-client.md) | Claude | Done | 01 | EV-2, NF-2 | NF-6 |
| 08 | [Standardize and validate](08-standardize.md) | Claude (subagent) | Done (M) | 01, 02 | RD-5 to RD-7 | RD-8, RD-9 |
| 09 | [Resolve to catalog](09-match.md) | Claude (subagent) | Done (M) | 01, 02 | MT-1, MT-3 to MT-5, DC-3 | MT-2 (second path) |
| 10 | [Price](10-price.md) | Claude (subagent) | Done (M) | 01, 02 | PR-1 to PR-4, PR-8 | PR-5 to PR-7, PR-10 |
| 11 | [Compliance](11-compliance.md) | Claude (subagent) | Done (M) | 01, 02 | CP-1 to CP-3, CP-5, CP-6 | CP-4 |
| 12 | [Decide and verify](12-decide-and-verify.md) | Claude (subagent) | Done (M) | 01, 07 | DC-1 to DC-4, SF-4, SF-5, VR-1 | none |
| 13 | [PRISM recording](13-prism-recording.md) | Mihir | Done (M) | 01 | VR-4, EV-3 | UX-8 |
| 14 | [Pipeline, review and API](14-pipeline-and-api.md) | Claude | Done (M) | 04 to 13, 19 | UX-3, UX-5, UX-6 | UX-4, UX-7, DC-5, NF-4 |
| 15 | [Review screen](15-web-ui.md) | Claude | Done (M) | 01 | UX-1 to UX-3, NF-8 | UX-4, UX-8 |
| 16 | [Evaluation and README](16-evaluation-and-readme.md) | Claude | In progress | 03, 14 | QA-2, DC-1 | none |
| 17 | [PRISM dashboard setup](17-prism-dashboard-setup.md) | User | In progress | 02, 13 | SF-1, MT-6, VR-2 | VR-3 |
| 18 | [Submission](18-submission.md) | User | Blocked | all | EV-9 | none |
| 19 | [Availability](19-availability.md) | Claude | Done | 01, 02 | AV-1 | AV-2, AV-3 |

## Order of work

Tasks in the same wave do not depend on each other and can be worked on at the same time. Build the M scope of every task before any S scope.

| Wave | Tasks | Gate to start |
|---|---|---|
| 0 | 01 | Plan approved |
| 1 | 02, 07, 13, 15 | 01 done: shared shapes and the sample run JSON exist |
| 2 | 03, 04, 05, 06, 08, 09, 10, 11, 12, 19, 17 | 02 and 07 done |
| 3 | 14 | Stage tasks done |
| 4 | 16, 18 | 14 done |

The critical path is 01 → 07 → 06 → 14 → 16. Task 15 (review screen) can start right after 01 against the sample run JSON, without waiting for any stage.

## Stretch items and cut order

From spec section 14. If scope has to shrink, cut in this order; first to cut is first in the list:

1. Spreadsheet intake (task 04)
2. Export (task 14)
3. Quantity breaks (task 10)
4. Surcharge and processing charges (task 10)
5. Second matching path; keep the single path plus thresholds (task 09)

Never cut: source evidence (06), rules-based pricing (10), the line statuses including alternates (09, 12), buyer and internal separation (12), the leak check (12), PRISM recording, guardrail, evaluator and Knowledge Base claim (13, 17), the test-set metrics (16).

## Open items that can change a task

| Item | Affects | Who resolves |
|---|---|---|
| Does the Knowledge Base show a grounded claim, or is it upload-only? (spec Q1) | 17 | Ask the PRISM team |
| Can PRISM screen traffic that goes through Nicrron? (spec Q2) | 05, 17 | Ask the PRISM team |
| Are evaluators available on our workspace plan? (spec Q3) | 17 | Check the dashboard |
| How does RudCo price, do they send partial quotes, do buyers accept alternates, typical validity? (spec Q4) | 10, 14 | Ask RudCo |
| Does RudCo supply dual-certified stock against plain 304 without asking? | 09 | Ask RudCo with Q4 |
