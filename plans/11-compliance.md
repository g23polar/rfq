# 11: Compliance (stage 8)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 02 |
| **Unblocks** | 14 |

## Goal

For each requirement on a line, say whether the matched item meets it, with evidence, and never show "unknown" as "met".

## Spec requirements

M: CP-1, CP-2, CP-3, CP-5, CP-6. S: CP-4. Edge cases P1, P2, P3, P5.

## Inputs

RFQ-wide requirements and line requirements (each with its source text), and each offer's matched item.

## Outputs

`RequirementResult[]` on each offer, and `Issue`s.

## Rules (M)

| Requirement, recognized from wording | Check | Result |
|---|---|---|
| Mill test report ("MTR", "mill certs", "CMTR", "3.1 certs", "EN 10204 3.1") | Item's `mtr_available` | met / not met / unknown |
| DFARS | Item's country of **melt** is a qualifying country | met / not met |
| "Melted and manufactured in USA", "domestic melt" | Country of melt is US | met / not met |
| Unqualified "domestic" | Cannot be checked until the buyer says which rule applies | unknown; buyer-facing `open_question` issue asking melt or manufacture. The line is still priced |
| Specification ("ASTM A240", "per A36", dual certification) | Item's `standard` and `certifications` | met / not met |
| Anything else | Not checkable | unknown |

- RFQ-wide requirements apply to every line; a line-level requirement on the same subject overrides the RFQ-wide one (P3). Each result records which it came from, with its source text.
- `not_met` adds an `unmet_requirement` issue (leads to no bid, unless another offer is compliant).
- `unknown` because the item's data is missing, on a critical requirement (MTR, origin, DFARS, specification), adds an internal `unconfirmed` issue (leads to specialist review). `unknown` because the buyer's wording is unclear adds an `open_question` instead. Other unknowns are shown as unknown on the quote.

Recognition is by fixed wording patterns, not a model call.

## Stretch (S)

- Industry-specific requirements: sour service, positive material identification, RoHS/REACH. Detected and marked unknown unless the data confirms (CP-4, P4).
- Pressure-vessel specifications ("SA-240") matched only to items certified to them (M7).

## Out of scope

- Choosing a different item to satisfy a requirement; task 09 already ranks compliant items first.

## Acceptance criteria

- The DFARS note in the email fixture is applied to every line and flags the item melted in a non-qualifying country.
- An unqualified "domestic" produces a question, not a verdict; the line keeps its price and shows the requirement as unknown.
- A line-level requirement overrides the RFQ-wide one in a test.
- An item with no MTR data shows "unknown", and the line goes to specialist review.
- Every result carries the source text of the requirement.
