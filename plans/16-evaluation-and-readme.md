# 16: Evaluation and README

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 03, 14 |
| **Unblocks** | 18 |

## Goal

Produce the accuracy numbers the demo closes on, and the README a judge reads to check the rules.

## Spec requirements

QA-2, DC-1, PR-7 (Must), QA-3 (Should). Feeds spec section 11.

## Outputs

`scripts/eval.py`, `out/eval_report.md`, `README.md`.

## Evaluation report

Runs every line in `fixtures/golden.jsonl` through the pipeline and reports:

| Measure | Definition |
|---|---|
| Set size | Number of labeled lines |
| Status table | Expected status against actual status, as counts |
| Wrongly quoted | Lines quoted that should have been asked or declined. Target: 0 |
| Wrongly asked | Lines sent to clarification or declined that should have been quoted |
| Quoted without a question | Share of lines that reached a quoted status |
| Field accuracy | Share of expected spec fields read correctly |
| Match accuracy | Share of quoted lines matched to the expected SKU |
| Time | Seconds per sample RFQ |

Each miss is listed with its line text, expected and actual result.

## README contents

- What it does, in the one-line description from the spec.
- How to run it (install, keys, start, open the page).
- The status rules table and the allowed assumptions, copied from spec 7.1 and 7.2.
- The pricing rule from task 10.
- The evaluation results and how to reproduce them.
- A statement that catalog and benchmarks are synthetic.
- Where NicrronNinoo and Block Convey PRISM are used.

## Judge-typed line (QA-3)

Covered by the paste box in task 15; this task confirms a single typed line runs end to end and adds one sentence to the README.

## Acceptance criteria

- `uv run python scripts/eval.py` prints the report and exits non-zero if any line is wrongly quoted.
- The README's rules match the code; a test compares the status rules table to the constants in `decide.py`.
