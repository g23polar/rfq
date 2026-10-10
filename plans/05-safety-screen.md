# 05: Safety screen (stage 2)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 07 |
| **Unblocks** | 14 |

## Goal

Find text in the RFQ that tries to instruct the AI, withhold it from processing, and show it to the specialist.

## Spec requirements

SF-1, SF-2, SF-3 (all M). Edge case S1. The leak check (SF-4, SF-5) is in task 12.

## Inputs

The full document text from intake, before segmentation output is used.

## Outputs

`Withheld[]` and the cleaned text. A line that lost text gets an internal `withheld_text` issue, which sends it to specialist review.

## How

- **Fixed patterns** first: phrases addressed to an AI or system ("ignore previous instructions", "you are", "system prompt", "set all prices").
- **One model call** that returns suspect passages as verbatim quotes. A quote not found in the document is ignored.
- Passages are cut from the text before any interpretation call sees it.
- The verdict is clean, flagged (passages withheld, rest continues) or blocked (nothing usable remains).
- The original text is recorded to PRISM as the input of this stage's span, so the dashboard's Prompt Injection guardrail flags it there (task 17). PRISM cannot block this traffic, because its proxy does not route to Nicrron (spec Q2); our screen does the withholding.

The stronger defense is structural and is not in this task: no model output can set a price or a status (spec principle 4).

## In scope

- Telling manipulation apart from ordinary buyer requests. "Can you do 10% off" is a commercial request shown to the specialist, not a withheld passage.

## Out of scope

- Reading a guardrail verdict back from PRISM (no API exists).

## Acceptance criteria

- The hidden instruction in the PDF fixture is withheld and shown with its location.
- Every price and status from `rfq.pdf` equals that from `rfq_clean.pdf`; the fixture's hidden instruction sits outside the line items.
- A unit test with an instruction inside a line shows that line, and only that line, sent to specialist review.
- Clean lines in the same RFQ are still quoted.
- A commercial request is not withheld.
