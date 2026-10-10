# 09: Match to catalog (stage 4)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01, 02 |
| **Unblocks** | 14 |

## Goal

Find the catalog item that fulfills a standardized line, say how strong the match is, and refuse to pick when the choice is weak or tied.

## Spec requirements

MT-1, MT-2, MT-3, MT-5 (Must), MT-4 (Should). MT-6 is covered by tasks 02 and 17.

## Inputs

A `Spec`, the line's requirements (header and line), the catalog.

## Outputs

A `Match` (best candidate plus up to two alternatives, each with strength and differences) and `Issue`s.

## Rules

- **Filter**: same form family (sheet and plate are one family), grade equal or covered by a dual-certified item, section dimensions within tolerance, stock size equal within 0.25 in. No cut-to-size.
- **Strength** starts at 1.0 and drops for each difference (thickness not identical, standard differs). Differences are listed in words.
- **Requirements as constraints**: among candidates, one that meets the line's requirements ranks above one that doesn't.
- **Dual-certified** stock filling a single-grade request: accepted, with an `assumption` issue (spec 7.1).
- **Weak** (best strength below 0.8) → `weak_match` issue.
- **Tied** (two different products within 0.05) → `tie` issue listing the options.
- **Substitution**: if nothing matches but the substitutions table offers another grade that does, add a `substitution` issue proposing it. The line is not matched to it.
- **Nothing fits** → `no_match` issue with the reason.

## Out of scope

- Compliance verdicts (task 11). Stock availability.

## Acceptance criteria

- Both track strings match the same SKU.
- The not-in-catalog fixture line produces `no_match` with a reason.
- A 304 request matched to 304/304L stock carries an assumption, not a substitution.
- A test with two equally good items produces a `tie`, and no best match is chosen.
- Match accuracy against `golden.jsonl` is reported by task 16.
