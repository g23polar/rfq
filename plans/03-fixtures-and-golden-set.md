# 03: Fixtures and golden set

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 02 |
| **Unblocks** | 16, and gives 04 to 12 realistic inputs |

## Goal

Create the three sample RFQs and the labeled test set that the demo and the accuracy number rest on.

## Spec requirements

QA-1, section 10, and the fixture named in the acceptance column of IN-1 to IN-3, SF-1, RD-4, RD-8, MT-5, CP-2, CP-4.

## Outputs

| File | Contents |
|---|---|
| `scripts/make_fixtures.py` | Generates the files below so they can be rebuilt |
| `fixtures/rfq_email.txt` | A messy email: greeting, header terms, 6 to 8 lines, sign-off |
| `fixtures/rfq.pdf` | A text PDF with a line table and footnotes |
| `fixtures/rfq.xlsx` | A spreadsheet with a header block above the line rows |
| `fixtures/golden.jsonl` | About 20 lines: raw text, expected spec fields, expected status, expected SKU where quoted |

## Seeded cases and where they go

| Case | Fixture | Expected status |
|---|---|---|
| "304 SS sheet 16ga 4x8" | email | Quoted with assumptions |
| "Stainless 304, 0.060 in, 48 x 96" (same fingerprint as above) | spreadsheet | Quoted with assumptions |
| A duplicate item written two ways in one RFQ | email | Both quoted, linked |
| A line with no grade | email | Needs clarification |
| A bar length with no unit | spreadsheet | Needs clarification |
| Stated gauge disagrees with stated thickness | PDF | Needs clarification |
| "Domestic material only" in the header against a non-domestic item | PDF | No bid |
| An item not in the catalog | spreadsheet | No bid |
| A hidden instruction trying to change prices | PDF | Passage withheld; no effect |
| A buyer discount request in the header | email | Shown as a term; no effect |
| A fully specified line with units and standard | each | Quoted |

## In scope

- Fixtures a judge would believe: inconsistent formatting, abbreviations, fractions, a footnote carrying a requirement.
- A second copy of the PDF without the injected passage, for the "no effect" comparison.

## Out of scope

- Scanned or image-only PDFs.

## Acceptance criteria

- Every seeded case appears in exactly one fixture and in `golden.jsonl`.
- The golden set has at least one line for each of the four statuses.
- The PDF's text layer extracts with the line items intact.
