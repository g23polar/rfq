# 14: Pipeline, review and API (stages 11 and 12, and orchestration)

| | |
|---|---|
| **Status** | Done (M scope); PRISM recording plugs in through one hook when task 13 lands |
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

## As built

- `pipeline.process(data, filename, today, ref, recorder) -> Processed(run, trace)` in `src/rfq/pipeline.py` runs: read → safety screen → segment → interpret (lines concurrently) → standardize → resolve → availability → price → compliance → decide → verify → reword questions → assemble.
- `Trace` holds one `Span` per stage (per line for the rule stages) and every model `CallRecord`, collected with `llm.watching`. Two RFQs processed at the same instant would mix their call lists.
- **PRISM hook (task 13):** define `rfq.prism.record_run(run, trace) -> str | None` (the trace id). `app.py` picks it up automatically; it is called once after the run, and an exception in it is logged and ignored.
- **Endpoints** (`src/rfq/app.py`, run with `uv run uvicorn rfq.app:app --reload`):
  - `POST /api/rfq` (multipart `file`, or form field `text`) → the `Run`
  - `GET /api/samples`, `POST /api/samples/{email|pdf}` → run a fixture
  - `GET /api/rfq/{id}` → the `Run` (moves draft to in review)
  - `POST /api/rfq/{id}/approve` with optional `{"by": "name"}` → the `Run`; 409 if the leak check failed
  - `GET /quote/{id}` → buyer quote page; `GET /api/rfq/{id}/summary` → internal summary text; `GET /api/rfq/{id}/trace` → the trace
  - `GET /` serves `static/index.html` when task 15 adds it
- `render.py`: `quote_html`, `email_text`, `internal_summary`. Buyer documents are built from `buyer_view` only; the quote page was designed with the frontend-design skill (mill-document look, print rules included).
- The leak check runs on the visible text of the quote page plus the email.
- A stage that raises sends only that line to specialist review (NF-6).
- **Guard added:** an RFQ-wide requirement is kept only if its wording appears outside the item lines. Segmentation sometimes lifts a line's own standard ("ASTM A36") into the RFQ-wide list, which made every line fail compliance in one live run.
- Offers that meet the line's requirements are listed ahead of those that don't (the ranking deferred from task 09).
- Offline tests replay `tests/recordings/`; `scripts/record_fixtures.py` adds responses for changed prompts.
- Timing, live and uncached: email thread about 11 s, PDF about 31 s.
- Not built (stretch): line edits, the buyer reply loop, audit trail. Export is covered by the quote page's print rules.

## Out of scope

- Persistence beyond the process, user accounts, sending the email, learning (stage 14, L).

## Acceptance criteria

- Each M fixture completes in under 60 seconds and returns a valid `Run`.
- The buyer quote and email pass the leak check; approval is refused when it fails.
- The buyer quote uses the buyer's line numbers and shows a validity date.
- A line in specialist review appears nowhere in buyer output.
- With recordings in place of live model calls, an end-to-end test of the email fixture passes offline and gives identical statuses and prices on a second run (NF-2).
