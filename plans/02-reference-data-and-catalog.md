# 02: Reference data and catalog

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01 |
| **Unblocks** | 03, 08, 09, 10, 11, 19, 17 |

## Goal

Produce the synthetic data every rule stage reads, and the document that gets uploaded to the PRISM Knowledge Base.

## Spec requirements

Section 16 (demo data), MT-3 (cross-reference table), MT-6 (reference data for the Knowledge Base), principle 9 (synthetic label).

## Outputs (M)

| File | Contents |
|---|---|
| `src/rfq/data/catalog.csv` | About 60 items: `sku`, `description`, `material`, `grade` (dual-certified written `304/304L`), `form`, dimensions, `standard`, `certifications`, `finish`, `cost_per_lb`, `stock_qty`, `lead_time_days`, `country_of_melt`, `mtr_available` (`yes`, `no`, `unknown`), `supplier` (internal) |
| `src/rfq/data/cross_reference.csv` | `customer`, `customer_part_no`, `sku`. A few rows for the demo customer and one for a different customer |
| `src/rfq/data/benchmarks.csv` | One row per grade and form family: `low`, `mid`, `high` in $/lb, `source` ("synthetic"), `as_of` |
| `src/rfq/data/reference.json` | Gauge-to-thickness by material, densities, abbreviations and shorthand (SS, CRS, HRP&O, AL, ga, dia, sch), default standard by grade and form, common grades by material and form (for missing-grade alternates), substitution rules, standard sheet sizes |
| `src/rfq/data/rules.json` | Pricing rules: target position, margin floor, validity days; DFARS qualifying countries |
| `src/rfq/reference.py` | Row shapes for the catalog, cross-references and rules (this task owns them), and their loaders. Benchmarks load into the `Benchmark` shape from task 01 |
| `scripts/export_kb.py` → `out/knowledge_base.md` | The reference tables as readable prose and tables, for upload in task 17 |

Benchmarks are keyed by grade and form, not material and form: 304 and 316 cannot share one range.

## Items the seeded cases need

- 16 ga 304/304L sheet 48 x 96, and the 316/316L equivalent (missing-grade alternates).
- Two items that tie for one request (X3).
- An item melted outside the DFARS qualifying countries with no compliant equivalent (P2).
- An item with `mtr_available` unknown (P5).
- An item with stock below a fixture quantity (Q4).
- An item whose cost puts the target price under the margin floor (PR-2).
- A cross-referenced customer part number (L5).

## Stretch (S)

- `surcharges.csv`: monthly stainless alloy surcharge by grade (PR-5).
- Minimum order charge, cutting charge and quantity-break tiers in `rules.json` (PR-6, PR-7).
- Pipe items with nominal size and schedule (U5).

## Out of scope

- Real prices, real inventory, learning new cross-references (L).

## Acceptance criteria

- Loaders return validated objects; no row fails validation.
- Every catalog grade and form has a benchmark and a default standard.
- Cross-reference lookups are scoped by customer: another customer's part number does not resolve (NF-5).
- The Knowledge Base export states the 16 ga stainless thickness and the default standard for 304 sheet in plain sentences, so a grounded claim can cite them.
- Every file and the export carry a "synthetic demo data" label.
