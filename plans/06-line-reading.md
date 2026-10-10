# 06: Interpret (stage 3)

| | |
|---|---|
| **Status** | Not started |
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

## Out of scope

- Unit conversion, shorthand expansion, any assumption (task 08).
- Model self-reported confidence. The spec replaces it with verifiable signals: source found here, rules in task 08, path agreement in task 09.

## Acceptance criteria

- The missing-grade fixture line has `grade` blank.
- A unit test with a fabricated `source_text` shows the field discarded and logged.
- Every kept field's `source_text` is a substring of the line or the terms.
- A line that is only a customer part number yields `customer_part_no` and nothing invented.
- Field accuracy against `golden.jsonl` is reported by task 16.
