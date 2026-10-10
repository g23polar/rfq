# 07: Model client

| | |
|---|---|
| **Status** | Not started |
| **Depends on** | 01 |
| **Unblocks** | 04, 05, 06 |

## Goal

One small wrapper for every model call, going through the Nicrron gateway, that returns validated JSON or fails clearly.

## Spec requirements

EV-2 (uses NicrronNinoo for model access).

## Outputs

`src/rfq/llm.py` with one function: given a system prompt, a user prompt and a pydantic shape, return an instance of that shape. Plus `scripts/smoke_nicrron.py`.

## How

- OpenAI SDK with `base_url=https://api.nicrron.ai/v1` and `NICRRON_API_KEY` from `.env`.
- Models: `anthropic/claude-sonnet-5` (intake, reading), `anthropic/claude-haiku-4-5` (safety screen). Both set in one place.
- `temperature: 0`, so identical demo reruns hit Nicrron's cache.
- JSON is requested in the prompt, parsed, validated; on failure, one retry that includes the validation error.
- Each call returns its token counts and latency so task 13 can record them.
- A recorded-response mode for tests: with no key set, calls are answered from saved responses in `tests/recordings/`.

## Open point resolved by the smoke test

Nicrron's docs do not say whether `response_format` (structured output) or `temperature` is accepted for these models. The smoke test tries both and the client uses whichever works.

## Out of scope

- Tool calling, streaming, fallbacks across providers.

## Acceptance criteria

- The smoke test returns valid JSON from both models and prints latency.
- A malformed model reply triggers exactly one retry, then a clear error.
- Tests run with no network and no key.
