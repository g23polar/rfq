# 13: PRISM recording

| | |
|---|---|
| **Status** | Done (M) |
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

## As built

- `Recorder(rfq_id, revision)` in `src/rfq/prism.py`. Wrap each stage in `with rec.stage(name, input=..., line=...) as s:` and set `s.output`. Record approval and edits with `rec.event(...)`. Call `rec.flush()` once after the run; it returns whether PRISM accepted everything and never raises.
- Model calls are collected automatically: `stage()` wraps its block in `llm.capture()`, so every `call_json` inside becomes an `llm` child span and a `/api/traces` record with `agent_name` `rfq-to-quote` and the run's `session_id`. `interpret_all` passes the context into its threads; other thread pools must do the same (`contextvars.copy_context()`).
- Span payloads copy the `prismtrace` SDK's own `/api/spans/ingest` format (span types `agent`, `chain`, `llm`, `tool`; ISO UTC times; text truncated to 10,000 characters).
- The trace id is a UUID built from `rfq_id`, revision and start time, so demo reruns of the same revision don't merge into one trace. Store `rec.trace_id` on `Run.prism_trace_id`.
- Smoke test (`uv run python scripts/smoke_prism.py`) runs the real email fixture through intake, safety and interpret. PRISM accepted 19 spans and 8 model-call traces. `setup-doctor` went from `in_progress` to `connected`, with `live_connected` and `app_connected` both true.
- The run is also sent to `/api/trajectories` as labeled steps (each stage, then its model calls). The dashboard's "Agent Run" panel is built from these; without them it shows only unlabeled "LLM Call" rows. The format comes from the SDK, not the docs. Confirmed in the dashboard on Oct 10.
- Calls answered from the local cache show 0 ms latency in PRISM. Use `RFQ_LLM_NO_CACHE=1` or a fresh RFQ for the demo run.
- The pipeline (task 14) records through `record_run(run, trace)`, which `rfq.app` picks up automatically. It replays the pipeline's stage list and matches each model call to its stage by that stage's system prompt; each interpret call becomes its own "interpret line N" span. A full PDF run recorded 82 stage spans and 14 model calls.
- `llm.py` now has two hooks: the pipeline's `watching()` (every thread) and the recorder's `capture()` (this context only). Both see every call.
- Still open: the dashboard URL format for the stretch link.

## Out of scope

- Guardrail, Knowledge Base and evaluator setup (task 17, dashboard-only).

## Acceptance criteria

- `GET /api/setup-doctor` reports a healthy setup.
- The smoke test's run appears in the dashboard with nested stages and the agent name.
- With the PRISM key removed, a quote still completes.
