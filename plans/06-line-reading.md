# 06: Interpret (stage 3)

| | |
|---|---|
| **Status** | Done (M scope) |
| **Depends on** | 01, 07 |
| **Unblocks** | 14 |

## Goal

Turn one item segment into specification fields, each tied to the exact text it came from, and throw away anything the model made up.

## Spec requirements

RD-1, RD-2, RD-3, RD-4 (all M). Supports NF-1 (traceability).

## Inputs

One `Segment` of kind `item`, and the `Terms`.

## Outputs

A `Reading` (task 01): each field is a value plus its `source_text`, or blank. Discarded values are listed in `Reading.discarded`.

## Fields

Material, grade, form, thickness, width, length, diameter, quantity, quantity unit, standard, finish, temper, tolerance, customer part number, drawing reference, and line-level requirements (certifications, origin, MTR).

## How

- One model call per line; lines run concurrently.
- The prompt asks for values **as written** (number and unit separately, e.g. `16` and `ga`), with the quoted source for each. No conversion, no defaults, no standard inferred from grade, no grade inferred from material.
- **Source verification** in code: a field is kept only if its `source_text` appears in the line or the RFQ terms (whitespace and case ignored) and the value appears within that source text. Otherwise it is discarded and logged.
- Dimensions are returned in the order written, unlabeled when the RFQ doesn't label them ("48 x .25 x 96"); task 08 decides which is thickness.
- Two stated values for one field (gauge and decimal thickness) are both kept so task 08 can detect a conflict.

## As built

- `src/rfq/interpret.py`: `interpret(line, terms) -> Line` makes one `MODEL_READ` call per item line and returns a copy of the line with a `Reading`. Other segment kinds pass through untouched. `interpret_all(lines, terms)` runs lines on a thread pool and keeps their order.
- The model returns `LineReading` (each field `value`, `unit`, `source_text`). The prompt sends only the line plus the RFQ requirements and attachment references, as context.
- Source verification in code: whitespace and case are ignored. The quote must be in the segment text (`source="rfq_line"`) or in any terms source text (`"rfq_terms"`), and the value must be in the quote. A value of `0.25` is accepted for a written `.25`. Failures go to `Reading.discarded` with a reason and a log warning.
- Values stay as written: `16`/`ga`, `1-1/2`/`"`, `1½`, `1,500`/`lb`, `ACME-PN 88213`. `4x8` gives two unlabeled dimensions, both quoting `4x8`. A tube wall (`.065 wall`) goes in `Reading.wall` (added to `models.py` along with `Spec.wall_in`).
- On `ModelCallError` the line gets an internal `model_failed` issue and no reading. Other lines are unaffected.
- Call records are not returned (the stage signature has no place for them). Task 13 can read them from the cache, or `interpret` can return them later.
- Live check (`uv run python scripts/run_interpret.py`, all 29 golden lines, about 10 s concurrent): grade 26/28 and quantity 28/28 match as written, with nothing discarded. The two grade differences are correct as-written readings that task 08 or 09 resolves: `304 or 304L?` and `Inconel 625`. Golden PDF texts have their leading line number stripped first, to match intake. Before that, the model read `3 1,500 lb` as quantity 3.

## Out of scope

- Unit conversion, shorthand expansion, any assumption (task 08).
- Model self-reported confidence. The spec replaces it with verifiable signals: source found here, rules in task 08, path agreement in task 09.

## Acceptance criteria

- The missing-grade fixture line has `grade` blank.
- A unit test with a fabricated `source_text` shows the field discarded and logged.
- Every kept field's `source_text` is a substring of the line or the terms.
- A line that is only a customer part number yields `customer_part_no` and nothing invented.
- Field accuracy against `golden.jsonl` is reported by task 16.
