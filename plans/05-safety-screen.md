# 05: Safety screen (stage 2)

| | |
|---|---|
| **Status** | Done (M scope) |
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

## As built

- `src/rfq/safety.py` runs between intake's two steps:
  - `screen_document(doc) -> ScreenResult` with `withheld` (each with `start`/`end` in `doc.cleaned`, page, reason, detector), `verdict`, `masked` (withheld text blanked, offsets unchanged), `passages` (to pass to `segment(doc, withheld=...)`), `calls` (for task 13), `dropped` (model quotes not in the text) and `model_error`.
  - `flag_lines(lines, withheld, doc.cleaned)` adds an internal `withheld_text` issue to each line whose text line overlaps a withheld passage.
- Fixed patterns are narrow: ignore/disregard previous instructions, "you are an AI", system prompt, set all prices or statuses, mark all items in stock, and text addressed to an AI ("AI assistant:", "SYSTEM:", "note to the AI"). A pattern hit runs from the instruction (and its addressee) to the end of its text line, so an instruction inside an item line removes only the instruction and the item is still segmented and flagged.
- One `MODEL_FAST` call returns verbatim quotes. Quotes not in the text are dropped. Overlapping hits merge into one passage; a pattern hit names the detector.
- If the model call fails, the screen keeps the pattern hits and sets `model_error`.
- Blocked means fewer than 3 words remain after withholding.
- Live check (`uv run python scripts/run_safety.py`): `rfq.pdf` flagged, the footer instruction withheld (pattern and model agree), 1.1 s; `rfq_email.txt` and `rfq_clean.pdf` clean, about 0.6 s each.

- Patterns are narrowed to avoid flagging buyer text: "ignore the previous instructions about ...", "set all prices in USD" and a bare "System:" line are not flagged (regression tests in `tests/test_safety.py`).

## Out of scope

- Reading a guardrail verdict back from PRISM (no API exists).

## Acceptance criteria

- The hidden instruction in the PDF fixture is withheld and shown with its location.
- Every price and status from `rfq.pdf` equals that from `rfq_clean.pdf`; the fixture's hidden instruction sits outside the line items.
- A unit test with an instruction inside a line shows that line, and only that line, sent to specialist review.
- Clean lines in the same RFQ are still quoted.
- A commercial request is not withheld.
