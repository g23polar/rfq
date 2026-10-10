# 07: Model client

| | |
|---|---|
| **Status** | Done |
| **Depends on** | 01 |
| **Unblocks** | 04, 05, 06, 12, and the second matching path in 09 |

## Goal

One small wrapper for every model call, going through the Nicrron gateway, that returns validated JSON or fails clearly.

## Spec requirements

M: EV-2 (NicrronNinoo for model access), NF-2 (repeatability). S: NF-6 (graceful degradation).

## Outputs

`src/rfq/llm.py` with one function: given a system prompt, a user prompt and a pydantic shape, return an instance of that shape. Plus `scripts/smoke_nicrron.py`.

## How

- OpenAI SDK with `base_url=https://api.nicrron.ai/v1` and `NICRRON_API_KEY` from `.env`.
- Models, set in one place: `anthropic/claude-sonnet-5` (segmentation, interpretation), `anthropic/claude-haiku-4-5` (safety screen, question wording).
- `temperature: 0` only where the model accepts it (see "As built"). Repeatability comes from a local response cache, not from Nicrron's.
- JSON is requested in the prompt, parsed, validated; on failure, one retry that includes the validation error.
- Each call returns its token counts and latency so task 13 can record them.
- Every response is saved to a local cache keyed by the exact request (`.cache/llm/`, git-ignored; `RFQ_LLM_CACHE` points it elsewhere). With no key set, calls are answered from saved responses, which is how tests run offline.

## Stretch (S)

- A call that still fails after the retry raises a typed error the pipeline turns into "needs specialist review" for that line, while the rest of the quote completes (NF-6).

## As built

- `call_json(system, user, shape, model)` returns a `ModelResult` with `.value` (the validated shape) and `.calls` (one `CallRecord` per attempt: model, messages, output, tokens, latency, live or cache). Task 13 records those.
- A failure is always a `ModelCallError` carrying the attempts made, so the pipeline can turn it into "needs specialist review" for that line (NF-6).
- Calls are synchronous; run lines concurrently with a thread pool.

## What the smoke test found (Oct 10)

| Model | `temperature` | `response_format` | Latency |
|---|---|---|---|
| `anthropic/claude-sonnet-5` | Rejected by the provider (HTTP 502 through Nicrron) | Accepted | about 0.9 s |
| `anthropic/claude-haiku-4-5` | Accepted | Accepted but not enforced: replies still arrive in a code fence | about 0.7 s |

Consequences:

- `temperature` is sent only to haiku. Nicrron's own cache needs `temperature: 0`, so it never applies to sonnet-5.
- `response_format` is not used. JSON is requested in the prompt, extracted from any code fence, and validated.
- The local cache is what makes the same RFQ give the same reading (NF-2) and makes demo reruns instant. `RFQ_LLM_NO_CACHE=1` forces live calls.
- `anthropic/claude-sonnet-4-6` accepts `temperature: 0` and is the fallback if sonnet-5's readings vary too much between first runs.

## Out of scope

- Tool calling, streaming, fallbacks across providers.

## Acceptance criteria

- The smoke test returns valid JSON from both models and prints latency.
- A malformed model reply triggers exactly one retry, then a clear error.
- Tests run with no network and no key.
