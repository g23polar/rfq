# 04: Intake and segmentation (stages 0 and 1)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 07 |
| **Unblocks** | 14 |

## Goal

Read an RFQ and split it into RFQ-wide terms and typed segments, each with the buyer's own line number and a pointer to where it sits in the original. Interpret nothing.

## Spec requirements

M: IN-1 (email, PDF), IN-3, IN-4, IN-5, IN-6. S: IN-1 (spreadsheet), IN-2, IN-7.

## Inputs

File bytes and filename, or pasted text.

## Outputs

`Terms` and `Segment[]` (task 01), plus the cleaned document text used for source checks later.

## How (M)

1. **Extract text**: email as-is; PDF with pypdf, keeping page numbers.
2. **Strip by rule** before any model call: forwarded and quoted history ("From:", "-----Original Message-----", "On ... wrote:", ">" lines), signatures, disclaimers. What was stripped is kept and shown, not thrown away.
3. **Segment** with one model call that returns verbatim quotes: the customer, due date, delivery terms, RFQ-wide requirements, commercial requests, attachment references ("per dwg 4471"), and each line with its buyer line number and kind (`item`, `requirement`, `note`, `service`).
4. **Verify** every quote is found in the cleaned text; its position becomes the location. A quote that isn't found is dropped and logged.
5. A requirement sitting among the item lines ("All material DFARS compliant") becomes an RFQ-wide requirement and a `not_an_item` line.
6. An attachment reference with no attachment adds a buyer-facing `missing_attachment` issue to the lines that cite it.

Where the buyer gave no line numbers, lines are numbered 1, 2, 3 in order.

## Stretch (S)

- **Spreadsheet** (`.xlsx`, `.csv`): no model call. Rows above the table are terms text; each row is a segment; the buyer's line-number column is preserved.
- **Triage** (stage 0, IN-2): classify the message as new RFQ, revision or not an RFQ. A non-RFQ is labeled and not quoted.
- **Wrapped and multi-item lines** (IN-7): join descriptions that wrap; split a line that asks for several items into linked lines.

## Out of scope

- Interpreting any line (task 06). Scanned PDFs. Reading drawings.

## Acceptance criteria

- The email thread fixture yields only the newest request's lines.
- The signature's phone number is not a segment and not a dimension.
- Quote lines carry the buyer's numbering.
- The DFARS note is in `Terms.requirements` and applies to all lines.
- The line citing a missing drawing carries a `missing_attachment` issue.
- Every segment's text is found verbatim at its stated location.
