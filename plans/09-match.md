# 09: Resolve to catalog (stage 5)

| | |
|---|---|
| **Status** | Not started |
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
