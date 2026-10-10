# 15: Review screen

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01 (builds against `fixtures/sample_run.json`); live data needs 14 |
| **Unblocks** | 18 |

## Goal

One screen a quoting specialist can use without instructions: drop in an RFQ, see which lines need their judgment, check any value against its source, and approve the quote.

## Spec requirements

M: UX-1, UX-2, UX-3, NF-8. S: UX-4, UX-8. Displays PR-3, AV-1, SF-2.

## Outputs

`src/rfq/static/index.html` (one file, plain JavaScript, no build step).

## What is on the screen (M)

| Area | Contents |
|---|---|
| Top | Upload or paste box; a "load sample" button for each fixture |
| Summary | Counts by status, quote total, quote status (draft / in review / approved), "synthetic demo data" label |
| Line table | One row per line with the buyer's line number: status badge, original text, matched item, availability, quantity and unit, unit and extended price. Lines needing the specialist are grouped first |
| Line detail (expand a row) | Source text with each field's evidence highlighted; interpreted spec; assumptions; matched item, strength and how it was found; alternates side by side with their prices; availability; price breakdown and benchmark position, with cost and margin; compliance results with evidence; issues split into buyer-facing and internal |
| Withheld | Passages removed by the safety screen, with location and reason |
| Deliverables | Buyer email text with a copy button; link to the buyer-facing quote |
| Approve | One button; offers "approve as partial" when lines await buyer input; disabled with the reason when the leak check failed |

Internal-only values (cost, margin, review notes) are visually marked so it is obvious they do not go to the buyer.

## Build in two steps

1. Render `fixtures/sample_run.json` as a static page. No backend needed; can start right after task 01.
2. Switch to the live endpoints from task 14: upload, approve, reload.

## Stretch (S)

- Edit a line's price, match or status with a required reason (UX-4).
- Link to the PRISM run (UX-8).

## Out of scope

- Login, editing the catalog, mobile layout.

## Acceptance criteria

- All seven statuses are distinguishable at a glance.
- Every displayed spec field shows its source text or the named assumption.
- A line with alternates shows each option's price and the one question.
- Approving changes the quote status and removes the "DRAFT" mark from the buyer quote.
- Someone who has not seen the screen can load a fixture, find the lines needing review, and approve, unaided.
