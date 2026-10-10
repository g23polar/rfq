# 06: Line reading (stage 2)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 07 |
| **Unblocks** | 14 |

## Goal

Turn one raw line into specification fields, each tied to the exact text it came from, and throw away anything the model made up.

## Spec requirements

RD-1, RD-2, RD-3, RD-4 (all Must).

## Inputs

One `RawLine` and the `Header`.

## Outputs

A `Reading` (task 01): each field is a value plus its `source_text`, or blank. Discarded values are listed in `Reading.discarded`.

## How

- One model call per line; lines run concurrently.
- The prompt asks for values **as written** (number and unit separately, e.g. `16` and `ga`), with the quoted source for each. No conversion, no defaults, no standard inferred from grade.
- **Source verification** in code: a field is kept only if its `source_text` appears in the line or the header (whitespace and case ignored) and the value appears within that source text. Otherwise it is discarded and logged.
- Line-level requirements ("MTRs required", "DFARS") are read here as `requirements[]`.

## In scope

- Fractions and mixed numbers read as written ("1/2", "1-1/4"); conversion happens in task 08.
- Two stated values for one field (gauge and decimal thickness) are both kept so task 08 can detect a conflict.

## Out of scope

- Unit conversion, abbreviation expansion, any assumption (task 08).
- Model self-reported confidence. Not used.

## Acceptance criteria

- The missing-grade fixture line has `grade` blank.
- A unit test with a fabricated `source_text` shows the field discarded and logged.
- Every kept field's `source_text` is a substring of the line or header.
- Field accuracy against `golden.jsonl` is reported by task 16.
