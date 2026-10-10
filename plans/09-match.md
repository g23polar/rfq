# 09: Resolve to catalog (stage 5)

| | |
|---|---|
| **Status** | Done |
| **Depends on** | 01, 02 (and 07 for the stretch path) |
| **Unblocks** | 14 |

## Goal

Find the catalog item or items that fulfill a line, say how strong each match is, and build labeled alternates when the request is ambiguous. Never accept a weak, tied or disputed match silently.

## Spec requirements

M: MT-1, MT-3 (lookup), MT-4, MT-5, DC-3. S: MT-2. MT-6 is covered by tasks 02 and 17. Edge cases L5, M1, M2, X1, X3, X4.

## Inputs

A `Spec` with its issues, the customer, the line's requirements, the catalog and the cross-reference table.

## Outputs

`Offer[]` on the line, each with a `Candidate` (strength, differences, how it was found), and `Issue`s.

## Rules (M)

1. **Cross-reference first.** A customer part number is looked up for that customer only. Found: the item is the match, with source "cross-reference". Not found and no description: buyer-facing `missing` issue asking what the part is.
2. **Spec match.** Filter by form family, grade, section dimensions within tolerance, and stock size within 0.25 in. Strength starts at 1.0 and drops for each difference, listed in words.
3. **Requirements as constraints.** An item that meets the line's requirements ranks above one that doesn't.
4. **Dual-certified stock** filling a plain 304 or 304L request: accepted with an `assumption` issue, no question. A request for 304H or "straight 304 only" does not match dual-certified stock.
5. **Alternates.** For a line with an `ambiguous_options` issue, run the match once per option and return every one that matches as a labeled offer. There is no limit on the number of alternates.
6. **Tie.** Two different products within 0.05 of each other become alternates.
7. **Weak.** Best strength below 0.8: internal `weak_match` issue.
8. **Nothing fits.** Retry with relaxed criteria (a substitute grade from the rules table). A hit is a labeled alternate with a buyer-facing `substitution` issue, never the match. No hit: `no_match` with the reason.

## Stretch (S)

- **Second matching path** (MT-2, X6): shortlist items by text similarity to the raw line, then one model call chooses from that closed list or answers "none of these". Agreement with the rule path marks the match confident; disagreement adds an internal `paths_disagree` issue.
- Near sizes, cut from larger stock, and an in-stock substitute for an out-of-stock item, each as a labeled alternate (X2, X5).

## Out of scope

- Compliance verdicts (task 11), stock levels (task 19), learning cross-references (L).

## Acceptance criteria

- Both track strings match the same SKU, with a dual-certified assumption and no question.
- The missing-grade line returns priced alternates for the common grades.
- A known customer part number resolves with "cross-reference" as its source; another customer's does not.
- Two equally good items come back as alternates.
- The not-in-catalog fixture line produces `no_match` with a reason.
- Match accuracy against `golden.jsonl` is reported by task 16.

## As built

- Changed after the first live end-to-end run: a standard is held against an item only when the buyer stated it. A default standard that the standardize stage assumed no longer lowers match strength (a 304 square tube stocked to ASTM A554 was being marked weak against an assumed A269).
- Changed during wiring (tests/test_chain.py): a grade that dual-certified stock cannot fill (304H, straight 304) is never offered a substitute; it is `no_match`. On bar, "cold rolled", "cold drawn" and "cold finished" are treated as one finish, because buyers write "CRS" for any cold-finished bar.

- Entry point: `rfq.match.resolve(line, ctx) -> Line` in `src/rfq/match.py`; tests in `tests/test_match.py`. M scope only.
- Order: not an item or no spec -> untouched. Customer part number found for `ctx.customer` -> one offer, `via="cross_reference"`, strength 1.0, `Offer.spec` from the catalog item plus the line's quantity (cross-reference runs before the blocking check). Not found: spec match if the line has a form and a grade, grade options or grade words, else a buyer `missing` issue (`field="customer_part_no"`).
- Blocking: any `missing` or `conflict` issue whose field is not one of quantity, quantity_unit, standard, finish, temper, tolerance, drawing_ref, customer_part_no leaves the line untouched. A line with no `spec.form` is also untouched.
- Strength: 1.0 minus 0.02 per dimension that is in tolerance but not equal, 0.25 for a standard the item does not carry (item standard or certifications), 0.25 for a finish mismatch, 0.15 for a temper mismatch, 0.15 for a grade variant that is neither an alias nor dual-certified fill. Thickness, diameter and wall tolerance: the larger of 0.005 in and 5% (`thickness_tolerance`); stock size (sheet and plate width and length, bar, tube and pipe length): 0.25 in. Anything outside tolerance is not a candidate (near-size and cut alternates are stretch).
- Dual-certified stock fills a request only if the request is in `dual_certified[...].fills` and the line is not marked straight-grade (the word "straight" in the grade text or a line requirement). No strength penalty; the fill is listed in `differences`.
- Alternates: each `ambiguous_options` option on `field="grade"` is matched on its own; offers are labeled "Option A: 304/304L" (the item's own grade). Options filled by the same SKU collapse to one offer labeled "As requested" (golden pdf-2).
- Tie: candidates within 0.05 of the best become one offer each, labeled "Option A: 304/304L, 2B finish", plus a `tie` issue whose `options` are the distinguishing words ("2B finish", "#4 finish").
- Assumptions (buyer): dual-certified fill (only when the grade was stated, not for grade alternates, whose labels already show it) and in-tolerance size. Each is raised only if it applies to every offer.
- Weak: best strength below 0.8 gives internal `weak_match`; the weak offer is still returned.
- Nothing fits: substitutions table (by grade family) gives `Substitute: <grade>` offers and a buyer `substitution` issue, no `no_match`. No hit gives `no_match` with a reason (grade not carried, form stocked only as a grade that does not meet the request, or size not stocked). A grade the reference data does not know (Inconel 625) is a `no_match` when standardize left no grade.

Deviations and gaps:
- Rule 3 (requirements as constraints) is not implemented; it needs compliance and is applied at wiring time.
- A substitute offer's `Offer.spec` carries the substitute grade and its default standard.
- `Offer.spec.material` is filled from the item when the spec has none.
- Stretch items (second matching path, near sizes, cut from larger stock) are not built; `paths_agree` stays None.
