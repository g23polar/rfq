# 04: Intake (stage 0)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 07 |
| **Unblocks** | 14 |

## Goal

Read an RFQ in any of three formats and split it into header terms and raw line items, each with a pointer to where it sits in the original.

## Spec requirements

IN-1 (email text, Must), IN-2 (PDF, Must), IN-3 (spreadsheet, Should), IN-4 (header terms), IN-5 (line location).

## Inputs

File bytes and filename, or pasted text.

## Outputs

`Header` and `RawLine[]` (task 01), plus the full document text used for source checks later.

## How

- **Spreadsheet** (`.xlsx`, `.csv`): no model call. Rows above the first table row are header text; each table row becomes a line whose text is the cells joined with their column names. Location is the sheet row.
- **Email and PDF**: extract text (pypdf for PDF, with page numbers), then one model call returns the header terms and the line items as verbatim quotes. Each quote must be found in the document; its position becomes the location. A quote that isn't found is dropped and logged.
- Header terms are sorted into requirements (certification, origin, MTR) and commercial requests (discounts, "best price").

## In scope

- Text PDFs only.
- Pasted text treated as email.

## Out of scope

- Interpreting any line (task 06). Scanned PDFs. Attachments inside emails.

## Acceptance criteria

- Each fixture from task 03 produces its expected line count.
- Every `RawLine.text` is found verbatim at its stated location.
- The "domestic material only" header term appears in `Header.requirements`; the discount request appears in `Header.commercial_requests`.
- The spreadsheet path makes no model call.
