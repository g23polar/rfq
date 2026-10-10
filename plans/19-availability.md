# 19: Availability (stage 6)

| | |
|---|---|
| **Status** | Done |
| **Depends on** | 01, 02 |
| **Unblocks** | 14 |

## Goal

For each offer, say whether the quantity can ship from stock, and never promise a date the data doesn't support.

## Spec requirements

M: AV-1. S: AV-2, AV-3. Edge case Q4.

## Inputs

An `Offer` (matched item and requested quantity) and the catalog's stock and lead-time columns.

## Outputs

An `Availability` on the offer (task 01).

## Rules (M)

| Situation | Status | Shown |
|---|---|---|
| Stock covers the quantity | In stock | Quantity available |
| Stock covers part of it | Partial | Quantity available now and the shortfall |
| No stock | Not stocked | Nothing promised |

- A quantity in pounds or feet is converted to pieces with the same weights and lengths task 10 uses, so the two never disagree.
- Availability does not change a line's status. A partial or not-stocked line is still quoted, with the availability stated on the quote.
- Stock is checked per offer, so each alternate shows its own availability.

## Stretch (S)

- Lead time in days for the shortfall or for non-stock items, from the catalog (AV-2).
- A flag when the RFQ's requested delivery date is earlier than stock plus lead time allows (AV-3, C5).
- An in-stock substitute offered as an alternate when the matched item is out of stock; built in task 09 using this task's result (X5).

## As built

- `availability.check(line, ctx)` in `src/rfq/availability.py` sets `offer.availability` on every offer that has a catalog item and a quantity. It adds no issues and never touches the status.
- `available_qty` and `shortfall_qty` are in the buyer's own unit. `available_qty` is what can ship now against this request (never more than was asked for), so "3 available, 5 short" reads directly off the two fields.
- Pieces are converted to pounds and hundredweight with `price.piece_weight_lb`, and to feet with the stock length.
- Lead time (AV-2) is included: it is set from the catalog whenever there is a shortfall, and left blank when the line is fully in stock.
- Not built: the flag for a requested delivery date that can't be met (AV-3), and offering an in-stock substitute (X5).
- If stock can't be converted to the buyer's unit (a dimension missing), availability is left blank; nothing is promised.

## Out of scope

- Live inventory, reservations, split shipments.

## Acceptance criteria

- The quantity-above-stock fixture line shows partial availability with the right shortfall.
- A line with no stock shows "not stocked" and no date.
- Two alternates on one line can show different availability.
