# 15: Web UI

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01 (builds against `fixtures/sample_run.json`); live data needs 14 |
| **Unblocks** | 18 |

## Goal

A single page a quoting specialist can use without a walkthrough: upload an RFQ, see every line's status, and click any value back to where it came from.

## Spec requirements

UX-1, UX-2, UX-7 (Must), UX-3, UX-6 (Should). Displays PR-3, PR-6, SF-2.

## Outputs

`src/rfq/static/index.html` (one file, plain JavaScript, no build step).

## What is on the page

| Area | Contents |
|---|---|
| Top | Upload or paste box; a "load sample" button for each fixture |
| Summary | Counts by status, quote total, "synthetic demo data" label, link to the PRISM run |
| Quote table | One row per line: status badge, original text, matched item, quantity, unit and extended price, review flag |
| Line detail (expand a row) | Original text with each field's source highlighted; standardized spec; match with strength and alternatives; price math against the benchmark range, with cost and margin; compliance results with evidence; issues and assumptions; the buyer question with an answer box |
| Withheld | Passages removed by the safety screen, with location and reason |
| Deliverables | Buyer email text with a copy button; link to the buyer quote page |

## Build in two steps

1. Render `fixtures/sample_run.json` as a static page. No backend needed; can start right after task 01.
2. Switch to the live endpoints from task 14: upload, answer a question, reload.

## In scope

- Hovering or clicking a spec field highlights its source text in the original line.
- A visible state while a run is in progress.

## Out of scope

- Login, editing the catalog, mobile layout.

## Acceptance criteria

- All four statuses are distinguishable at a glance in the table.
- Every displayed spec field shows its source text or the named assumption.
- The withheld passage from the PDF fixture is visible.
- Someone who has not seen the page can upload a fixture and find the price reasoning for a line unaided.
