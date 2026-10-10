# 08: Standardize and validate (stage 4)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 02 |
| **Unblocks** | 14 |

## Goal

Convert a reading into one canonical specification so that different wordings of the same item become identical, and record every inference as a visible assumption.

## Spec requirements

M: RD-5, RD-6, RD-7. S: RD-8, RD-9. Edge cases L1, L2, U1, U2, U4, U6, U7, M5, Q1, Q2.

## Inputs

A `Reading` and the reference tables.

## Outputs

A `Spec` with a `fingerprint`, and `Issue`s added to the line.

## Rules (M)

| Case | Rule | Issue |
|---|---|---|
| U1 | Fractions in every form (1-1/2, 1 1/2, 1.5", 1½), and units in, ft, mm, cm, m → inches | none |
| L2 | Shorthand expanded from the reference table | none |
| U2 | Explicit units are used. A sheet or plate size as two bare numbers is read in whichever unit makes it a standard sheet size: "4x8" as feet, "48 x 96" as inches | `assumption` |
| U2 | Any other bare number where the unit matters | `missing` (buyer) |
| U4 | Gauge → thickness from the table for that material | none; unknown material → `missing` on grade |
| U6 | Unlabeled dimensions on flat product: the smallest is the thickness | `assumption` |
| L1 | A stated decimal thickness within tolerance (0.005 in or 5%) of a standard thickness for that material becomes the standard thickness, so "0.060 in" and "16ga" stainless agree | `assumption` |
| U7 | Gauge and decimal thickness both stated: within the same tolerance keep the standard thickness | `assumption`; beyond tolerance → `conflict` (buyer) |
| M5 | No standard stated: default for the grade and form | `assumption` |
| Q2 | Quantity in lb, cwt or ft kept in the buyer's unit, with the conversion to pieces alongside | none |
| Q1 | Quantity missing | `missing` (buyer) |
| M1 | Grade missing but material and form known | `ambiguous_options`, listing the common grades from the reference table |
| M2 | Grade wording unclear between variants ("304/L?") | `ambiguous_options`, listing the variants |
| — | Material stated disagrees with the grade's material | `conflict` (buyer) |

Required fields: grade, form, quantity always; thickness, width, length for sheet and plate; diameter and length for bar; diameter, wall and length for tube. A line that is only a customer part number skips these checks and goes to cross-reference in task 09.

The fingerprint is the canonical fields joined in a fixed order.

## Stretch (S)

- Duplicate lines: equal fingerprints within one RFQ are linked through `duplicate_of` (RD-8).
- "Same as above, but 316": inherit the previous line's fields, logged as an assumption (RD-9, L4).
- Typos and OCR confusions ("3O4"), metric decimal commas, pipe nominal size and schedule, tolerances, sheet versus plate naming (L3, U3, U5, U8, U9).

## Out of scope

- Choosing a catalog item; filling 304 from dual-certified stock (both task 09).

## Acceptance criteria

- The track's two example strings produce the same fingerprint, each with assumption issues.
- 16 gauge gives a different thickness for stainless, carbon steel and aluminum.
- "48 x .25 x 96" yields 0.25 in thickness with an assumption.
- The conflict fixture line carries a buyer-facing `conflict`.
- The missing-grade line carries `ambiguous_options`, not `missing`.
- A test asserts every inference made is present as an issue.
