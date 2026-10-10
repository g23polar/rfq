# 12: Decide and verify (stages 9 and 10)

| | |
|---|---|
| **Status** | Done |
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

## As built

- Changed during wiring (tests/test_chain.py): a finish may be sourced from the material wording ("CRS" names both material and finish).

**Entry points**

- `rfq.decide.decide(line, ctx) -> Line`: sets `status`, `question`, `review_note` (recomputed each call). Also `assign_status(line)`, `build_question(line)`, `email_questions(run) -> list[tuple[str, Question]]` (blocking first, then priced lines; run order within each group) and the constant `STATUS_RULES`.
- `rfq.questions.reword(question) -> Question` (fast model, falls back to the template); `check_rewording(template, text) -> list[str]` returns the reasons for rejection.
- `rfq.verify.verify(line, ctx) -> Line`; `rfq.verify.leak_check(run, buyer_texts, ref=None) -> LeakCheck`.

**Status rules as implemented** (`STATUS_RULES`, first match wins)

| Order | Condition | Status |
|---|---|---|
| 1 | Segment kind is not `item` | not_an_item |
| 2 | any of below_floor, weak_match, paths_disagree, withheld_text, unconfirmed, verification_failed, model_failed | needs_specialist_review |
| 3 | `no_match` or `unmet_requirement`; or no offers and nothing that blocks on the buyer | no_bid |
| 4 | `missing`, `conflict`, `missing_attachment`; or `ambiguous_options`, `tie`, `substitution`, `open_question` with no priced offer | needs_buyer_input |
| 5 | `ambiguous_options`, `tie` or `substitution`, with a priced offer | quoted_with_alternates |
| 6 | `assumption` or `open_question` only, with a priced offer | quoted_with_assumptions |
| 7 | no issues other than `price_out_of_range` / `stale_benchmark`, with a priced offer | quoted |
| 8 | fallback: offers exist but none is priced | needs_specialist_review |

Deviations from the plan table: rule 3 does not fire on "no offer at all" alone, because `missing` and `conflict` lines have no offers (matching is skipped); rule 4 absorbs alternate and `open_question` items that cannot be priced; rule 8 is new. `price_out_of_range` and `stale_benchmark` go into `review_note` only. `review_note` joins the messages of all review and note-only internal issues; it is None otherwise.

**Questions.** One per line, only for statuses needs_buyer_input, quoted_with_alternates and quoted_with_assumptions (never for internal issues, assumptions, no bid). Text is `Line N: ` then, for each open item in order conflict, missing, missing_attachment, ambiguous_options, tie, substitution, open_question, the issue message followed by a fixed ask: missing "Please provide the missing detail."; conflict "Please confirm which is correct."; missing_attachment "Please send the attachment."; ambiguous_options/tie "Which would you like?" (plus "Each option is priced in the quote." when already priced); substitution "Is this substitution acceptable?"; open_question "Please confirm.". The options of the first item are appended as "Options: a, b." and set as `Question.options`. `blocking` is False when the line status is priced.

**Rewording check.** Rejected if: empty; a number not in the template (commas and trailing zeros ignored); a currency sign or word not in the template; a month name not in the template ("may" is not checked); we will, we'll, we shall, guarantee, promise, commit, assure; cost, margin, floor, markup, supplier, vendor (singular or plural) or any catalog supplier name. Any model error returns the template.

**Line checks.** (1) Each non-blank `Spec` field has a source in `Line.reading` (material may come from the grade; dimensions from unlabeled dimensions; any field when a cross-referenced part number was used) or a buyer `assumption`/`substitution` issue naming it. (2) Every figure in a rationale matches a value in `Price.numbers` within the rounding of the figure as written; digits of dates, the line's grade names and any word mixing letters and digits (6061-T6, A240, 304L) are ignored. (3) A line that is priced, by stored status or by the rules, has a candidate on every priced offer and no review-kind internal issue (`price_out_of_range` and `stale_benchmark` are allowed). On failure `verification_failed` is added once and `decide` re-runs.

**Leak check.** Searches the documents for: cost, margin and floor figures of every offer plus the catalog cost of each matched item; unit price, extended and components of any line not priced in the buyer view; rationale and SKU of those lines; all supplier names in the catalog; review notes; withheld text; messages of internal issues. Skips: an internal figure equal (2 decimals) to a decimal figure the buyer may see in `buyer_view(run)`; an internal string contained in buyer-visible text; strings under 4 characters. Matching of figures: two or more decimals may be a rounding ("1.72" for 1.7234); one decimal must be exact; whole numbers only with a "$" before or "%" after and only if the internal value is whole. Known gap: an internal figure that equals a visible one is not detected.

**Not done / contract notes.** `leak_check` takes an optional third argument, `ref`. `reword` returns only the question, not the `CallRecord`s that task 13 may want.
