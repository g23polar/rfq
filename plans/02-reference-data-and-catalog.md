# 02: Reference data and catalog

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01 |
| **Unblocks** | 03, 08, 09, 10, 11, 17 |

## Goal

Produce the synthetic data every rule stage reads, and the document that gets uploaded to the PRISM Knowledge Base.

## Spec requirements

Section 10 (demo data), PR-6 (synthetic label), MT-6 (reference tables for the Knowledge Base).

## Outputs

| File | Contents |
|---|---|
| `src/rfq/data/catalog.csv` | About 60 items: `sku`, `description`, `material`, `grade` (dual-certified written `304/304L`), `form`, `thickness_in`, `width_in`, `length_in`, `diameter_in`, `standard`, `cost_per_lb`, `country_of_origin`, `mtr_available` (`yes`, `no`, `unknown`), `dfars_compliant` |
| `src/rfq/data/benchmarks.csv` | One row per grade and form family: `low`, `mid`, `high` in $/lb, `source` (always "synthetic"), `as_of` |
| `src/rfq/data/reference.json` | Gauge-to-thickness by material, densities, abbreviations and alternate names, default standard by grade and form, allowed substitutions |
| `src/rfq/reference.py` | Loaders returning the typed shapes from task 01 |
| `scripts/export_kb.py` → `out/knowledge_base.md` | The reference tables as readable prose and tables, for upload in task 17 |

## In scope

- Stainless (304, 316), carbon steel (A36, A1011, 1018), aluminum (5052, 6061) in sheet, plate, round bar and round tube.
- Items needed by the seeded cases in task 03: the 16 ga 304 sheet 48 x 96; a non-domestic item with no domestic equivalent; an item with `mtr_available` unknown; one stale benchmark; one item whose cost floor lands above the benchmark range.
- A test that every catalog grade and form has a benchmark and a default standard.

## Out of scope

- Real prices or real inventory. Stock quantities are not modeled.

## Acceptance criteria

- Loaders return validated objects; no row fails validation.
- The Knowledge Base export states the 16 ga stainless thickness and the default standard for 304 sheet in plain sentences, so a grounded claim can cite them.
- Every file and the export carry a "synthetic demo data" label.
