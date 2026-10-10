# 13: PRISM recording

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01 |
| **Unblocks** | 14, 17 |

## Goal

Record every stage of every RFQ as one inspectable run in Block Convey PRISM, under one agent name.

## Spec requirements

VR-4, EV-3 (Must), UX-6 (Should).

## Outputs

`src/rfq/prism.py` and `scripts/smoke_prism.py`.

## How

- Direct HTTP with header `X-PRISMtrace-Key`; settings from `.env` (`PRISMTRACE_HOST`, `PRISMTRACE_API_KEY`, `PRISMTRACE_PROJECT_ID`).
- **One trace per RFQ**, id equal to the `rfq_id`. `POST /api/spans/ingest` sends a root span for the run and one child span per stage per line, with the stage's input and output as text, timing and status.
- **Model calls** are also sent to `POST /api/traces` with `agent_name`, model, messages, token counts and latency, sharing the run's `session_id`. This is the only documented place `agent_name` can be set.
- Agent name is one constant. Project is the one named after the team.
- Spans are sent after the run finishes, in one request, so recording never slows a quote. A recording failure is logged and does not fail the run.
- With no key set, the client does nothing.
- The run stores its trace id so the UI can link to it.

## Open points

- Whether spans sent over HTTP appear as an agent run in the dashboard the way SDK runs do. The smoke test plus a look at the dashboard answers it; fallback is the `prismtrace-sdk` Python package.
- The exact dashboard URL for a trace, needed for the link.

## Out of scope

- Guardrail, Knowledge Base and evaluator setup (task 17, dashboard-only).

## Acceptance criteria

- `GET /api/setup-doctor` reports a healthy setup.
- The smoke test's run appears in the dashboard with nested stages and the agent name.
- With the PRISM key removed, a quote still completes.
