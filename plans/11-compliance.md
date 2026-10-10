# 11: Compliance check (stage 6)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 02 |
| **Unblocks** | 14 |

## Goal

For each requirement on a line, say whether the matched item meets it, with evidence, and never show "unknown" as "met".

## Spec requirements

CP-1 to CP-5 (all Must).

## Inputs

Header requirements and line requirements (each with its source text), and the matched catalog item.

## Outputs

`RequirementResult[]` and `Issue`s.

## Rules

| Requirement, recognized from wording | Check | Result |
|---|---|---|
| Mill test report ("MTR", "mill certs", "CMTR", "EN 10204 3.1") | Item's `mtr_available` | met / not met / unknown |
| Domestic sourcing ("domestic only", "melted and manufactured in USA", "Buy America") | Country of origin is US | met / not met |
| DFARS | Item's `dfars_compliant` | met / not met |
| Country of origin disclosure | Always answerable | met, with the country |
| Specification ("ASTM A240", "per A36") | Item's `standard` | met / not met |
| Anything else | Not checkable | unknown |

- Header requirements apply to every line; each result records whether it came from the header or the line, with its source text.
- `not_met` adds an `unmet_requirement` issue (leads to No bid).
- `unknown` adds an `unconfirmed` issue (leads to Needs clarification).

Recognition is by fixed wording patterns, not a model call.

## Out of scope

- Choosing a different item to satisfy a requirement; task 09 already ranks compliant items first.

## Acceptance criteria

- The "domestic material only" header is applied to every line of the PDF fixture and marks the non-domestic item not met.
- A DFARS line against a non-compliant item is flagged.
- An unrecognized requirement is shown as unknown, with an issue.
- Every result carries the source text of the requirement.
