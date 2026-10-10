# 08: Standardize (stage 3)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 02 |
| **Unblocks** | 14 |

## Goal

Convert a reading into one canonical specification so that different wordings of the same item become identical, and record every inference as an issue.

## Spec requirements

RD-5, RD-6, RD-7, RD-8 (Must), RD-9 (Should). Implements the allowed assumptions in spec 7.1.

## Inputs

A `Reading` and the reference tables.

## Outputs

A `Spec` with a `fingerprint`, and `Issue`s added to the line.

## Rules

| Rule | Result |
|---|---|
| Units (in, ft, mm, cm, m), fractions and mixed numbers | Inches |
| Gauge | Thickness from the table for that material; unknown material → `missing` issue on grade |
| Abbreviations and alternate names ("SS", "T-304", "CRS") | Canonical material and grade |
| Sheet or plate size as two bare numbers, both 12 or less | Feet; `assumption` issue |
| Thickness within tolerance of a standard thickness (proposed: 0.005 in or 5%, whichever is larger) | Standard thickness; `assumption` issue |
| No standard stated | Default from the table; `assumption` issue |
| Any other bare number where units matter (bar length) | `missing` issue; no value |
| Gauge and decimal thickness both stated and disagreeing beyond tolerance | `conflict` issue |
| Material stated disagrees with the grade's material | `conflict` issue |
| A required field for the form is blank | `missing` issue naming the field |

Required fields: grade, form, quantity always; thickness, width, length for sheet and plate; diameter and length for bar; diameter, wall and length for tube.

The fingerprint is the canonical fields joined in a fixed order. Lines in one RFQ with equal fingerprints are linked through `duplicate_of`; they are still quoted separately.

## Out of scope

- Choosing a catalog item. Dual-certified stock is handled in task 09.

## Acceptance criteria

- Both track strings produce the same fingerprint, each with assumption issues.
- 16 gauge gives a different thickness for stainless, carbon steel and aluminum.
- The conflict fixture line and the unitless bar length each carry the expected issue.
- Every inference made is present as an issue; a test asserts no silent defaults.
