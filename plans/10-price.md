# 10: Price (stage 7)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 02 |
| **Unblocks** | 14 |

## Goal

Calculate a price for each offer from documented rules, in the buyer's unit of measure, and explain it in plain language using only the calculated numbers.

## Spec requirements

M: PR-1, PR-2, PR-3, PR-4, PR-8. S: PR-5, PR-6, PR-7, PR-10. Edge case Q2.

## Inputs

An `Offer` (spec and matched item), the benchmarks, the pricing rules.

## Outputs

A `Price` on the offer (task 01) and `Issue`s.

## The pricing rule (M; values are proposals in `rules.json`)

| Step | Rule |
|---|---|
| Weight | Geometry x density, x quantity; or the stated pounds |
| Price per lb | Benchmark midpoint x 0.97 |
| Margin | (price - cost) / price |
| Margin floor | 12%. A price under the floor is **not raised**: the line gets an internal `below_floor` issue and goes to specialist review |
| Buyer's unit | The price is shown in the unit the buyer used: each, per lb, per cwt, or per foot, plus the extended total |
| Position | Below midpoint, within range, or above range, with the benchmark's source and date |
| Validity | Quote date plus 7 days |
| No benchmark | Not priced; internal `unconfirmed` issue |

`components[]` always has a base line, so stretch components add to it without changing the shape.

## Rationale

A fixed sentence template filled from the calculated numbers: the benchmark range with its source and date, and where our price sits. No model call. The figures used are stored in `Price.numbers` so task 12 can re-check them. The rationale shown to the buyer never mentions cost or margin; the specialist view adds them.

## Stretch (S)

- **Alloy surcharge** on stainless as a separate, month-dated component from the surcharge table (PR-5).
- **Processing and minimum charges**: a cutting charge for cut-to-size offers; a minimum order charge on very small lines, shown separately (PR-6, Q5).
- **Quantity breaks**: each requested tier priced (PR-7, L8).
- **Flags**: internal issue when the price is above the benchmark range or the benchmark is older than 90 days (PR-10).

## Out of scope

- Freight, customer price history (L), live market data.

## Acceptance criteria

- Unit and extended price reproduce by hand from the rule.
- A quantity in pounds is priced per lb; a piece quantity per each.
- The below-floor fixture line goes to specialist review and its price never appears in buyer output.
- Every price carries a validity date.
- Every rationale states "synthetic" for the benchmark source, and every number in it equals a value in `Price.numbers`.
