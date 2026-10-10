# 16: Evaluation and README

| | |
|---|---|
| **Status** | In progress: `README.md` and `tests/test_readme.py` done; `scripts/eval.py` and the report not started |
| **Depends on** | 03, 14 |
| **Unblocks** | 18 |

## Goal

Produce the metrics the demo closes on, and the README a judge reads to check the rules.

## Spec requirements

QA-2, DC-1 (both M). Reports the metrics in spec section 13.

## Outputs

`scripts/eval.py`, `out/eval_report.md`, `README.md`.

## Evaluation report

Runs every line in `fixtures/golden.jsonl` through the pipeline and reports:

| Metric | Definition | Target |
|---|---|---|
| Silent-error count | Lines with status quoted or quoted with assumptions whose spec, match or price differs from the label | 0 |
| Routing accuracy | Lines given the expected status | ≥ 85% |
| Over-ask count | Buyer questions on lines the test set marks as determinable | ≤ 2 |
| Field accuracy | Interpreted fields matching the labeled answer | ≥ 90% |
| Rationale consistency | Price rationales whose numbers match the calculation | 100% |
| Leak count | Internal values found in buyer-facing output | 0 |
| Manipulation effect | Whether `rfq.pdf` and `rfq_clean.pdf` differ in any price or status | No |
| Time to draft | Seconds for a 20-line RFQ | < 60 |

Touchless rate is left out: it counts specialist edits, and line editing is stretch scope (UX-4).

Also printed: set size, a table of expected against actual status, and each miss with its line text.

The report shows silent errors and over-asks side by side, since each is easy to drive to zero at the other's expense.

## README contents

- What it does, in the one-line description from the spec.
- How to run it (install, keys, start, open the page).
- The status rules and issue audiences from task 12.
- The standardizing assumptions from task 08 and the dual-certified rule from task 09.
- The pricing rule from task 10.
- The metrics and how to reproduce them.
- A statement that catalog, stock, benchmarks and cross-references are synthetic.
- Where NicrronNinoo and Block Convey PRISM are used.

## Acceptance criteria

- `uv run python scripts/eval.py` prints the report and exits non-zero if the silent-error count or the leak count is above zero.
- The README's status rules match the code; a test compares them to the constants in `decide.py`.
