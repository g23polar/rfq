# 04: Intake and segmentation (stages 0 and 1)

| | |
|---|---|
| **Status** | Done (M scope) |
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

## As built

- `src/rfq/intake.py` has two steps so the safety screen (task 05) can sit between them:
  - `read_document(data, filename) -> Document`: no model. Extracts text (PDF via pypdf, with page ranges) and, for emails, strips history, quoted lines, disclaimers and signature contact lines. Each stripped piece is kept in `Document.stripped` with its range in the original.
  - `segment(doc, withheld=[...], attachments=None) -> IntakeResult` makes one model call and returns `terms`, `lines` (each a `Line` holding its `Segment` and any `missing_attachment` issue), `dropped` (model quotes not found in the text) and `calls` (for task 13).
- Withheld passages are blanked with spaces (`mask`), so the model never sees them and every location still points into `doc.cleaned`.
- The top header block and the sign-off name stay in the cleaned text, because they carry the customer and the date. Only contact lines after the sign-off are cut.
- Segment text leaves out the buyer's line number. A PDF table row reads `<qty> <uom> <description>`.
- Buyer numbers are kept as written. Requirement and note lines get `-`. If no item has a number, items are numbered 1, 2, 3.
- `llm.call_json` gained `max_tokens`. Segmentation uses 8000, because the 2000 default truncated the 8-line PDF. Non-default limits are part of the cache key.
- Live check (`uv run python scripts/run_intake.py`): email 8 s, PDF 19 s, one call each, nothing dropped. The PDF's hidden instruction did not appear in any segment.
- **Spreadsheet intake (added later):** `read_document` accepts `.xlsx`, `.xlsm` and `.csv`. `read_spreadsheet` writes the sheet as text, one line per row: rows above the table as they are, and each table row with its own column names (`Line 10 | Description: ... | Qty: 25 | UoM: ea`). It then goes through the same screen, segmentation and interpretation as an email, so there is one code path. This differs from the plan, which had rows becoming segments with no model call; reusing the path was far less code and keeps source checking identical.
  - The line-number column is recognized by its heading (Line, Pos, #, No.) and becomes the buyer's line number.
  - An empty quantity cell is written `(blank)`. Without that, the model could take the line number for the quantity.
  - `Document.rows` maps each text line to its sheet row; segments carry it in `Location.row`.
  - Sample: `fixtures/rfq.xlsx`, also at `POST /api/samples/sheet` and as a button on the review screen.
- Not built: triage and wrapped or multi-item lines (stretch).

## Out of scope

- Interpreting any line (task 06). Scanned PDFs. Reading drawings.

## Acceptance criteria

- The email thread fixture yields only the newest request's lines.
- The signature's phone number is not a segment and not a dimension.
- Quote lines carry the buyer's numbering.
- The DFARS note is in `Terms.requirements` and applies to all lines.
- The line citing a missing drawing carries a `missing_attachment` issue.
- Every segment's text is found verbatim at its stated location.
