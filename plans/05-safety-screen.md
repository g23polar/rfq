# 05: Safety screen (stage 1)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 07 |
| **Unblocks** | 14 |

## Goal

Find text in the RFQ that tries to instruct the AI, remove it from processing, and show it to the specialist as withheld.

## Spec requirements

SF-1, SF-2 (Must), SF-3, SF-4 (Should).

## Inputs

The full document text from intake.

## Outputs

`Withheld[]` and the cleaned text. Lines that lost text get the review flag reason "text withheld".

## How

- **Fixed patterns** first: phrases addressed to an AI or system ("ignore previous instructions", "you are", "system prompt", "set all prices").
- **One model call** that returns suspect passages as verbatim quotes. A quote not found in the document is ignored.
- Passages are cut from the text before any reading call sees it.
- The original text is recorded to PRISM as the input of this stage's span, so the dashboard's Prompt Injection guardrail flags it there (task 17). PRISM cannot block this traffic, because its proxy does not route to Nicrron; our screen does the withholding.

The stronger defense is structural and is not in this task: no model output can set a price or a status.

## In scope

- Distinguishing manipulation from ordinary buyer requests. "Can you do 10% off" is a commercial request shown to the specialist, not a withheld passage.

## Out of scope

- Reading a guardrail verdict back from PRISM (no API exists).

## Acceptance criteria

- The seeded passage in the PDF fixture is withheld and shown with its location.
- Prices and statuses from the injected PDF equal those from the clean copy.
- The discount request in the email fixture is not withheld.
- Clean lines in the same RFQ are still processed.
