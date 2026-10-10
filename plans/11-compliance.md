# 11: Compliance (stage 8)

| | |
|---|---|
| **Status** | Done |
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

## As built

- Entry point: `compliance.check(line, ctx) -> Line` in `src/rfq/compliance.py`. Mutates and returns the line. Returns it untouched when no offer has a candidate. Offers without a candidate are skipped; offers with one get `offer.compliance` replaced (reruns do not duplicate results or issues).
- Requirements: `ctx.terms.requirements` (scope `rfq`) and `line.reading.requirements` (scope `line`). Each is classified from `source_text` first (the buyer's words), and from `value` only when the source text yields nothing. Text is split into clauses on `;`, newline, "but", and ", no/not" so "DFARS required, no MTRs needed" is read as two requirements.
- Wording recognized (case-insensitive):
  - MTR: MTR, CMTR, mill test report/cert(s), material or test report/cert(s), "3.1 certs", EN 10204. Result name `Mill test report`.
  - DFARS: DFARS, 252.225, specialty metals. Name `DFARS`. Country of melt in `rules.dfars.qualifying_countries`.
  - Domestic with melt (domestic/USA/U.S./American/"no imports" plus the word melt): name `Domestic melt`, melt country must be US. "Melted and manufactured in USA" is this case.
  - Domestic with manufacture only ("Made in USA"): name `Domestic manufacture`; unknown (the catalog has no manufacture country).
  - Unqualified domestic: name `Domestic`; unknown. Not raised if DFARS is in the same clause.
  - Specification: ASTM/ASME codes (`A240`, `ASTM A-240`, `SA-240`, `per A36`, `AMS-QQ-A-250/11`), compared as codes with case, spaces and hyphens ignored, against the item's `standard` and `certifications`. One result per code, or one result if the text says "or". `SA-240` is not satisfied by `A240` or the reverse; grade/type suffixes ("Grade B") are ignored. Name `Specification: ASTM A240`.
  - Dual certification: `dual cert...`, optionally naming a pair (`304/304L`). Name `Dual certification[: 304/304L]`. Met when the item grade is dual-certified and names both grades.
  - Anything else: result name is the earlier stage's label, result unknown, no issue.
- Override: each requirement has a subject (mtr, origin = DFARS/domestic/manufacture, specification, dual; unrecognized ones are their own subject). If any line-level requirement has a subject, all RFQ-wide requirements of that subject are dropped. A waiver ("not required", "N/A", "import OK", "waived", "exempt") on a subject takes part in the override and produces no result, so the DFARS note is not shown for that line.
- Issues:
  - `open_question` (buyer, field `requirement`, options "Melted in the USA" / "Manufactured in the USA"): once per unqualified-domestic requirement.
  - `unconfirmed` (internal, field `compliance`): unknown from missing item data (MTR unknown, blank/invalid melt country, manufacture-only, no recorded standard, SKU not in catalog) on MTR, origin or specification requirements. One per SKU and requirement.
  - `unmet_requirement` (buyer, field `requirement`): one per distinct failed requirement, only when every offer with a candidate has at least one `not_met`.
- Evidence states the fact only ("Country of melt: US.", "Mill test report available.").

Deviations and decisions:
- `RequirementResult.source_text` falls back to the label (`value`) when the Sourced has no `source_text`, so every result carries text.
- Waived requirements leave no result at all (the plan does not say). Say so if the quote should show "not required".
- Only the requirement lists are read; `reading.standard` (the line's own spec) is the matcher's concern.
- Not built: stretch items (industry-specific requirements, SA-240-only matching beyond the code compare above).
