# 10: Price (stage 5)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 02 |
| **Unblocks** | 14 |

## Goal

Calculate a price from one documented rule and explain it in plain language using only the calculated numbers.

## Spec requirements

PR-1, PR-2, PR-3, PR-4, PR-6, PR-7 (Must), PR-5 (Should).

## Inputs

A `Spec`, the matched catalog item, the benchmarks.

## Outputs

A `Price` (task 01) and, where needed, review flag reasons.

## The pricing rule (proposed values; confirm before build)

| Step | Rule |
|---|---|
| Weight | Geometry x density for the material, x quantity (or the stated pounds) |
| Target | Benchmark midpoint x 0.97 |
| Floor | Cost x 1.12 |
| Price per lb | The higher of target and floor |
| Position | Below midpoint, within range, or above range |
| Review flag | Price above the benchmark range, or benchmark older than 90 days |
| No benchmark | Not priced; `unconfirmed` issue |

## Explanation

A fixed sentence template filled from the calculated numbers: the benchmark range with its source and date, where our price sits, and, when the floor decided the price, that the minimum margin holds it there. No model call. The numbers used are also stored separately so task 12 can re-check them.

Cost and margin are stored on the `Price` for the specialist view and are excluded from the buyer document.

## Out of scope

- Volume breaks, cut charges, freight, lead time.

## Acceptance criteria

- Unit and extended price reproduce by hand from the rule.
- A below-cost scenario is impossible: a test with a benchmark far under cost prices at the floor and raises the review flag.
- The stale-benchmark item raises the review flag.
- Every explanation states "synthetic" for the benchmark source.
