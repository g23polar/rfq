# 13: PRISM recording

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01 |
| **Unblocks** | 14, 17 |

## Goal

Record every stage of every RFQ as one inspectable run in Block Convey PRISM, under one agent name.

## Spec requirements

M: VR-4, EV-3. S: UX-8.

## Outputs

`src/rfq/prism.py` and `scripts/smoke_prism.py`.

## How

- Direct HTTP with header `X-PRISMtrace-Key`; settings from `.env` (`PRISMTRACE_HOST`, `PRISMTRACE_API_KEY`, `PRISMTRACE_PROJECT_ID`).
- **One trace per RFQ revision**, id built from the `rfq_id` and revision. `POST /api/spans/ingest` sends a root span for the run and one child span per stage per line, with the stage's input and output as text, timing and status.
- **Model calls** are also sent to `POST /api/traces` with `agent_name`, model, messages, token counts and latency, sharing the run's `session_id`. This is the only documented place `agent_name` can be set.
- Specialist approval and edits are recorded as spans on the same trace.
- Agent name is one constant. Project is the one named after the team.
- Spans are sent after the run finishes, in one request, so recording never slows a quote. A recording failure is logged and does not fail the run.
- With no key set, the client does nothing.
- Run data goes to PRISM in full, including internal fields; all of it is synthetic. Keys and other `.env` values are never sent.

## Stretch (S)

- The run stores a dashboard link so the review screen can open it (UX-8).

## Open points

- Whether spans sent over HTTP appear as an agent run in the dashboard the way SDK runs do. The smoke test plus a look at the dashboard answers it; fallback is the `prismtrace-sdk` Python package.
- The dashboard URL format for a trace, needed for the link.

## Out of scope

- Guardrail, Knowledge Base and evaluator setup (task 17, dashboard-only).

## Acceptance criteria

- `GET /api/setup-doctor` reports a healthy setup.
- The smoke test's run appears in the dashboard with nested stages and the agent name.
- With the PRISM key removed, a quote still completes.
