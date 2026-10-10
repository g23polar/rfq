# 12: Decide and verify (stages 9 and 10)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 07 |
| **Unblocks** | 14 |

## Goal

Give every line exactly one status from its issue list using fixed rules, keep buyer-facing and internal issues apart, draft the buyer questions, and check the draft before a person sees it.

## Spec requirements

DC-1, DC-2, DC-3, DC-4, SF-4, SF-5, VR-1 (all M). Edge cases S2, S3, B1. Implements spec section 9.

## Inputs

A `Line` with its issues and offers. Can be built and tested against `fixtures/sample_run.json` before any other stage exists.

## Outputs

`status`, `question`, `review_note`, `verification` on each line; a leak-check result on the run.

## Issue kinds and audience

| Audience | Kinds |
|---|---|
| Buyer | `missing`, `conflict`, `missing_attachment`, `ambiguous_options`, `tie`, `substitution`, `open_question`, `assumption`, `no_match`, `unmet_requirement` |
| Internal | `below_floor`, `weak_match`, `paths_disagree`, `withheld_text`, `unconfirmed`, `verification_failed`, `model_failed`, `price_out_of_range`, `stale_benchmark` |

## Status rules, first match wins

| Order | Condition | Status |
|---|---|---|
| 1 | Segment kind is not `item` | Not an item |
| 2 | `below_floor`, `weak_match`, `paths_disagree`, `withheld_text`, `unconfirmed`, `verification_failed`, `model_failed` | Needs specialist review |
| 3 | `no_match`, no offer at all, or `unmet_requirement` on every offer | No bid |
| 4 | `missing`, `conflict`, `missing_attachment` | Needs buyer input |
| 5 | `ambiguous_options`, `tie` or `substitution`, with at least one priced offer | Quoted with alternates |
| 6 | `assumption` or `open_question` only | Quoted with assumptions |
| 7 | No issues | Quoted |

`price_out_of_range` and `stale_benchmark` add a review note without changing the status.

## Questions

- One question per open item, built from a fixed template per issue kind, with options where they exist (the alternates, feet or inches, melt or manufacture).
- The model rewords the template into natural language. The reworded text is checked: it may contain no number, date or currency amount that the template did not contain, no commitment words ("we will", "guarantee"), and no internal term. If the check fails, the template text is used (SF-5, S3).
- Questions on lines that block pricing come first in the email; questions on lines that are already priced (alternates, `open_question`) follow (DC-4). Internal issues never produce a question (DC-2).

## Verification checks (no model)

- Every non-blank spec field has a verified source or a named assumption.
- Every number in each price rationale equals a value in `Price.numbers` (VR-1).
- A line with a buyer-visible price has a match and no internal issue.
- **Leak check** (SF-4, S2): the rendered buyer quote and buyer email are searched for every internal value in the run: each cost and margin figure, the floor, supplier names, review notes, withheld text. Any hit fails the run's leak check and blocks approval.

A failed line check adds `verification_failed`, which sends the line to specialist review.

## Out of scope

- Rendering the documents (task 14). Sending anything.

## Acceptance criteria

- Every line in the sample run and the fixtures gets exactly one status.
- Every line with a buyer-facing open item has a question; alternates list their options.
- No internal issue appears in the buyer email.
- A reworded question containing a price is rejected and replaced by the template.
- A test that plants a cost figure in the buyer quote fails the leak check.
- A test that tampers with a rationale number fails verification.
