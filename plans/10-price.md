# 10: Price (stage 7)

| | |
|---|---|
| **Status** | Done |
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

## As built

Entry points in `src/rfq/price.py`:
- `price(line, ctx) -> Line`: for each offer with a candidate, a quantity and a quantity unit in `offer.spec`, sets `offer.price`. Returns the line untouched if there are no offers; offers missing a candidate or quantity are skipped silently.
- `piece_weight_lb(spec, item, ctx) -> float`: weight of one piece. Each dimension comes from `spec`, else from the catalog item; density is `tables.density_lb_per_in3[item.material]`. Raises `ValueError` if a needed dimension is missing from both (the stage turns that into an `unconfirmed` issue).

Formulas (volume in in3 x density):
- sheet, plate, flat_bar: t x w x l. round_bar: pi/4 d^2 l. round_tube, pipe: pi/4 (d^2 - (d - 2 wall)^2) l. square_tube: (w^2 - (w - 2 wall)^2) l, with the outside size in `width_in` (falls back to `diameter_in`).
- Benchmark is looked up for the catalog item's grade and form (not the spec's). `per_lb = round(mid x target_multiplier, 4)`.
- `ea`: unit = round(per_lb x piece, 2); weight = qty x piece. `lb`: unit = per_lb (4 decimals); weight = qty. `cwt`: unit = round(per_lb x 100, 2); weight = qty x 100. `ft`: unit = round(per_lb x lb per ft, 2) where lb per ft = piece weight / (length_in / 12), length from spec else item; weight = qty x lb per ft.
- `extended = round(unit_price x qty, 2)` in every unit, so it reproduces from the displayed unit price. `weight_lb` is rounded to 2 decimals.
- `margin = (per_lb - cost) / per_lb x 100`; `margin_pct` stored to 1 decimal, the floor test uses the unrounded value.
- `position`: below_mid if per_lb < mid; within_range if mid <= per_lb <= high; else above_range. With the 0.97 rule it is always below_mid.
- `valid_until = today + validity_days` (ISO).

Rationale template (no model call), `{...}` from `Price.numbers`:
`Priced at ${price_per_lb:.4f}/lb, {pct_below_mid:.1f}% below the ${benchmark_mid:.2f}/lb midpoint of the benchmark range ${benchmark_low:.2f}-${benchmark_high:.2f}/lb ({source} data, as of {as_of}).`
Within range: `{pct_above_mid:.1f}% above the ${benchmark_mid:.2f}/lb midpoint of the`. Above range: `above the ${benchmark_high:.2f}/lb top of the`. Only the keys the sentence uses are in `numbers`.

Issues: `below_floor` (internal, field `price`, states margin, floor, price and cost) and `unconfirmed` (internal, field `price`; no benchmark, item not in catalog, or a dimension missing). When a line has more than one offer the message is prefixed with the offer label, and one issue is raised per offending offer.

Deviations and decisions:
- The sample rationale names the grade and form ("304 sheet"); this one omits them, because digits such as "304" would look like uncited numbers to the verifier. The item is already named on the offer.
- The benchmark date is in the text and in `Price.benchmark.as_of`, not in `numbers` (which holds floats only). A verifier should skip ISO dates.
- Stretch items (surcharge, processing and minimum charges, quantity breaks, price_out_of_range and stale_benchmark flags) are not built.
- Tests: `tests/test_price.py`, 13 tests.
