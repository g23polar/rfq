# 12: Decide and verify (stages 7 and 8)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01 |
| **Unblocks** | 14 |

## Goal

Give every line exactly one status from its issue list using fixed rules, draft the buyer question where one is needed, and run fixed checks before anything is shown as quoted.

## Spec requirements

DC-1, DC-2, DC-3, VR-1 (Must). Implements spec 7.2 and 7.3.

## Inputs

A `Line` with its issues, match, price and compliance results. Can be built and tested against `fixtures/sample_run.json` before any other stage exists.

## Outputs

`status`, `question` (text and options), `review_flag` with reasons, `verification`.

## Status rules, first match wins

| Order | Issue kinds present | Status |
|---|---|---|
| 1 | `missing`, `conflict`, `unlisted_inference`, `weak_match`, `tie`, `substitution`, `unconfirmed` | Needs clarification |
| 2 | `no_match`, `unmet_requirement` | No bid |
| 3 | `assumption` only | Quoted with assumptions |
| 4 | none | Quoted |

## Questions

One template per issue kind, filled from the issue, with options where they exist (tied items, the proposed substitute, feet or inches). The model does not word questions in the first build; that is a later add-on and first in the cut order after export polish.

## Verification checks (no model)

- Every non-blank spec field has a verified source or a named assumption issue.
- Every number in the price explanation equals the stored calculated number.
- Price per lb is at or above the floor.
- A quoted line has a match, a price and no blocking issue.

A failure removes the price from the buyer view and sets the review flag.

## Out of scope

- Sending anything. Combining questions into the email is task 14.

## Acceptance criteria

- Every line in the sample run and the fixtures gets exactly one status.
- Every Needs clarification line has a question; tied matches list the options.
- A test that tampers with an explanation number fails verification.
- The rules table above is reproduced in the README by task 16.
