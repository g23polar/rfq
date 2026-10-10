# 01: Contracts and skeleton

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | none |
| **Unblocks** | every other task |

## Goal

Fix the shared data shapes and the project layout so every other task can be built on its own against them. This is the only task everything waits for.

## Spec requirements

None directly; it carries the shapes that RD-2 (source text on every value), section 7 (statuses) and UX-2 (line detail) need.

## Outputs

1. **Project skeleton**: `pyproject.toml` (uv), `src/rfq/`, `tests/`, `scripts/`, `fixtures/`, `src/rfq/data/`, `src/rfq/static/`. `.env` already exists and is git-ignored.
2. **`src/rfq/models.py`** with the shapes below (pydantic).
3. **`fixtures/sample_run.json`**: one hand-written `Run` with four lines, one per status, plus one withheld passage. Tasks 12, 14 and 15 build against it.
4. **Stage signature**, written in the module docstring: every stage is `stage(line, context) -> line`, where `context` holds the header terms, catalog, benchmarks and reference tables. A stage only adds to the line; it never removes what an earlier stage wrote.

## Data shapes

| Shape | Fields |
|---|---|
| `Sourced` | `value`, `source_text` (exact text from the RFQ), `where` (`"line"` or `"header"`) |
| `RawLine` | `line_no`, `text`, `location` (page or row, plus character range in the original) |
| `Header` | `due_date`, `delivery`, `requirements[]` (each a `Sourced`), `commercial_requests[]` (each a `Sourced`) |
| `Withheld` | `text`, `location`, `reason`, `detector` (`pattern` or `model`) |
| `Reading` | One optional `Sourced` per field: `material`, `grade`, `form`, `thickness`, `width`, `length`, `diameter`, `quantity`, `quantity_unit`, `standard`; `requirements[]`; `discarded[]` (values dropped by source verification) |
| `Issue` | `kind`, `field`, `message`. Kinds: `missing`, `conflict`, `unlisted_inference`, `assumption`, `weak_match`, `tie`, `substitution`, `unconfirmed`, `no_match`, `unmet_requirement` |
| `Spec` | `material`, `grade`, `form`, `thickness_in`, `width_in`, `length_in`, `diameter_in`, `quantity`, `quantity_unit`, `standard`, `fingerprint` |
| `Candidate` | `sku`, `description`, `strength` (0 to 1), `differences[]` |
| `Match` | `best` (optional `Candidate`), `alternatives[]` (at most two) |
| `Price` | `weight_lb`, `price_per_lb`, `unit_price`, `extended`, `benchmark` (`low`, `mid`, `high`, `source`, `as_of`), `position`, `explanation`, and specialist-only `cost_per_lb`, `margin_pct` |
| `RequirementResult` | `requirement`, `scope` (`header` or `line`), `source_text`, `result` (`met`, `not_met`, `unknown`), `evidence` |
| `Line` | `line_no`, `raw` (`RawLine`), `reading`, `spec`, `issues[]`, `match`, `price`, `compliance[]`, `status`, `question` (`text`, `options[]`), `review_flag`, `review_reasons[]`, `duplicate_of[]`, `verification` (`passed`, `failures[]`) |
| `Run` | `rfq_id`, `created`, `source` (`filename`, `kind`), `header`, `withheld[]`, `lines[]`, `counts` (by status), `total`, `email`, `prism_trace_id` |

`status` is one of `quoted`, `quoted_with_assumptions`, `needs_clarification`, `no_bid`.

## In scope

- The shapes, the skeleton, the sample run, a test that the sample run loads into the models.

## Out of scope

- Any stage logic.

## Acceptance criteria

- `uv sync` and `uv run pytest -q` succeed on a clean checkout.
- `fixtures/sample_run.json` validates against `Run` and contains all four statuses.
- A buyer-facing dump of a `Line` (a named helper) omits `cost_per_lb` and `margin_pct`.
