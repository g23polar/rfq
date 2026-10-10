# 14: Pipeline and API (stage 9 and orchestration)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 04 to 13 |
| **Unblocks** | 16, 18, and the live half of 15 |

## Goal

Run the stages in order for an uploaded RFQ, expose the result to the UI, and produce the two deliverables: the buyer quote and the buyer email.

## Spec requirements

UX-4, DC-3 (Must), UX-5, DC-4 (Should).

## Outputs

`src/rfq/pipeline.py`, `src/rfq/render.py`, `src/rfq/app.py`.

## Endpoints

| Endpoint | Does |
|---|---|
| `POST /api/rfq` | Accepts a file or pasted text; runs all stages; returns the `Run` |
| `GET /api/rfq/{id}` | Returns a stored run (kept in memory) |
| `POST /api/rfq/{id}/lines/{n}/answer` | Applies a specialist's answer or field correction and re-runs stages 3 to 8 for that line. No model call |
| `GET /quote/{id}` | The buyer quote as an HTML page with a print stylesheet |
| `GET /` | The static UI |

## How

- Order: intake → safety → reading (lines concurrently) → standardize → match → price → compliance → decide → verify → assemble → record to PRISM.
- A failure in one line marks that line for review and does not stop the others.
- **Buyer quote**: header, priced lines, each assumption in plain words, compliance notes, validity period, pending lines, the synthetic-data label. No cost or margin. Lines with the review flag are left off until cleared.
- **Buyer email**: one message listing every open question by line, with options.
- A corrected field from the specialist is recorded with source "specialist", so it stays traceable.

## Out of scope

- Persistence beyond the process, user accounts, sending the email.

## Acceptance criteria

- Each of the three fixtures completes in under one minute and returns a valid `Run`.
- The buyer quote contains no cost or margin anywhere in its HTML.
- Answering the question on a Needs clarification fixture line turns it into a quoted line without a model call.
- With recordings in place of live model calls, an end-to-end test of the email fixture passes offline.
