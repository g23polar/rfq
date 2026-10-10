# 14: Pipeline, review and API (stages 11 and 12, and orchestration)

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 04 to 13, 19 |
| **Unblocks** | 16, 18, and the live half of 15 |

## Goal

Run the stages in order for an uploaded RFQ, hold the result as a draft until a specialist approves it, and produce the deliverables: the buyer-facing quote, the buyer email and an internal summary.

## Spec requirements

M: UX-3, UX-5, UX-6, NF-3, NF-5. S: UX-4, UX-7, DC-5, NF-4.

## Outputs

`src/rfq/pipeline.py`, `src/rfq/render.py`, `src/rfq/app.py`.

## Endpoints (M)

| Endpoint | Does |
|---|---|
| `POST /api/rfq` | Accepts a file or pasted text; runs all stages; returns the `Run` as a draft |
| `GET /api/rfq/{id}` | Returns a stored run (kept in memory) |
| `POST /api/rfq/{id}/approve` | Marks the quote approved, as complete or partial. Refused if the leak check failed |
| `GET /quote/{id}` | The buyer-facing quote. Marked "DRAFT" until approved |
| `GET /` | The review screen |

## How (M)

- Order: intake → safety → interpret (lines concurrently) → standardize → resolve → availability → price → compliance → decide → verify → record to PRISM.
- Quote status moves draft → in review (first opened) → approved. Nothing is "ready to send" before approval.
- **Partial quotes go out by default**: lines awaiting buyer input are listed as pending; lines in specialist review are left off entirely. The specialist can hold the whole quote instead.
- **Buyer-facing quote**, built only from the buyer view helper (task 01): quote number and revision, buyer's line numbers, specs, unit of measure, prices, alternates, availability, assumptions, compliance notes, exceptions and no-bids with reasons, validity, terms, the synthetic-data label.
- **Buyer email**: every open question grouped in one message, blocking questions first, with options.
- **Internal summary**: counts by status, lines in specialist review with their notes, withheld text.
- A 20-line RFQ must produce a draft in under 60 seconds: interpretation calls run concurrently and nothing else calls a model per line in M scope except question wording.

## Stretch (S)

- **Line edits** (UX-4): `POST /api/rfq/{id}/lines/{n}/edit` changes a price, match or status, with a reason; the edit is recorded with who, what and why (NF-4) and its source is "specialist".
- **Buyer reply loop** (stage 13, DC-5): apply a buyer's answer to the affected lines, re-run stages 4 to 10 for them, and issue a new revision. An unclear answer produces a follow-up question.
- **Export** (UX-7): a print stylesheet on the quote page.

## Out of scope

- Persistence beyond the process, user accounts, sending the email, learning (stage 14, L).

## Acceptance criteria

- Each M fixture completes in under 60 seconds and returns a valid `Run`.
- The buyer quote and email pass the leak check; approval is refused when it fails.
- The buyer quote uses the buyer's line numbers and shows a validity date.
- A line in specialist review appears nowhere in buyer output.
- With recordings in place of live model calls, an end-to-end test of the email fixture passes offline and gives identical statuses and prices on a second run (NF-2).
