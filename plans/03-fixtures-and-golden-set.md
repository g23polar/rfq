# 03: Fixtures and golden set

| | |
|---|---|
| **Status** | Done |
| **Depends on** | 01, 02 |
| **Unblocks** | 16, and gives 04 to 12 realistic inputs |

## Goal

Create the sample RFQs and the labeled test set that the demo and the metrics rest on.

## Spec requirements

QA-1, section 16, and the M cases of the edge-case catalogue (section 12).

## Outputs

| File | Contents | Tier |
|---|---|---|
| `scripts/make_fixtures.py` | Generates the files below so they can be rebuilt | M |
| `fixtures/rfq_email.txt` | An email thread: the newest request on top, forwarded history with an old quote below, a signature with a phone number | M |
| `fixtures/rfq.pdf` | A text PDF with a line table, footnotes and the hidden instruction | M |
| `fixtures/rfq_clean.pdf` | The same PDF without the hidden instruction, for the "no effect" comparison | M |
| `fixtures/rfq.xlsx` | A spreadsheet with a header block and buyer line numbers | S |
| `fixtures/golden.jsonl` | About 25 lines: raw text, expected spec fields, expected status, expected SKU where quoted, and whether the answer was determinable (for the over-ask count) | M |

## Seeded cases

| Fixture | Case (catalogue id) | Expected result |
|---|---|---|
| Email | Forwarded history and signature (D1, D2) | Only the newest request's lines; phone number not read as an item |
| Email | "304 SS sheet 16ga 4x8" and "Stainless 304, 0.060 in, 48 x 96" (L1, U2) | Same fingerprint; quoted with assumptions |
| Email | Grade missing (M1) | Quoted with alternates, one question |
| Email | Customer part number only (L5) | Resolved by cross-reference |
| Email | "All material DFARS compliant" between lines (D7, P2) | RFQ-wide requirement, not an item |
| Email | A below-floor item (PR-2) | Needs specialist review |
| PDF | Gauge disagrees with thickness (U7) | Needs buyer input |
| PDF | Wording unclear between 304 and 304L (M2) | Quoted with alternates |
| PDF | Quantity in pounds (Q2) | Priced per lb |
| PDF | Quantity above stock (Q4) | Quoted, partial availability |
| PDF | "Per dwg 4471 rev B" (D5) | Needs buyer input: asks for the drawing |
| PDF | Not in catalog (X4) | No bid |
| PDF | Hidden instruction (S1), placed outside the line items | Withheld; every price and status identical to the clean copy |
| Spreadsheet (S) | Buyer line numbers 10, 20, 30 (D10); missing quantity (Q1); quantity breaks (L8) | Numbering preserved; needs buyer input; tiers priced |

The track's two example strings carry no quantity, so the fixture adds one to each ("10 ea"); without it they would stop at "needs buyer input".

The golden set also needs lines for U1 (fraction forms), U4 (gauge by material), U6 (dimension order), M5 (default standard), P1 (MTR), P3 (line overrides header), P5 (unverifiable requirement), X1 (exact match) and X3 (tie).

## As built

- `uv run python scripts/make_fixtures.py` rebuilds everything; output is byte-stable. Edit the script, not the files. `tests/test_fixtures.py` fails if they drift apart.
- Dependencies added: `pypdf` (runtime; task 04 reads PDFs with it), `fpdf2` and `openpyxl` (dev). Task 04's spreadsheet intake will need `openpyxl` moved to runtime.
- Customers: the email is from Acme Fabrication (DFARS note); the PDF from Brightline Manufacturing (MTRs required for all items, in the notes below the table). The hidden instruction is white 4 pt text in the PDF footer.
- The PDF text layer extracts one row per line as `<line> <qty> <uom> <description>`; golden `text` for PDF lines uses that form.
- `golden.jsonl` has 29 records: 7 from the email (including the DFARS line), 8 from the PDF, 14 standalone. Each record: `id`, `fixture`, `buyer_line_no`, `case_ids`, `text`, `kind`, `customer`, `rfq_requirements`, `expected` (`status`, `skus`, `spec`, `issue_kinds`), `determinable`, `note`.
  - `expected.spec` lists only the fields to check; field accuracy compares those.
  - `expected.skus` is every acceptable item: one per alternate, empty when nothing is priced to the buyer.
  - `determinable: false` marks lines that warrant a buyer question; a question on any other line is an over-ask.
- Whole-fixture cases (D1, D2, D10, S1, B1, ...) are in `FIXTURE_CASES` in the script. S2 and S3 are behaviors, tested in task 12, not fixtures.
- **Open point for task 09:** `pdf-2` ("304 or 304L?") is labeled `quoted_with_alternates` per spec M2, but both options resolve to the same dual-certified item. If task 09 treats dual-certified stock as satisfying both readings, relabel it `quoted_with_assumptions`.

## Out of scope

- Scanned or image-only PDFs.

## Acceptance criteria

- Every M case in the catalogue appears in a fixture or the golden set, with its catalogue id recorded.
- The golden set has at least one line for each of the seven statuses.
- The PDF's text layer extracts with the line items intact.
