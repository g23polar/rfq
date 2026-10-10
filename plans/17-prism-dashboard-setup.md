# 17: PRISM dashboard setup (done by a person)

| | |
|---|---|
| **Status** | Not started |
| **Owner** | User |
| **Depends on** | 02 (Knowledge Base document), 13 (a recorded run to attach to) |
| **Unblocks** | 18 |

## Goal

Configure the three PRISM features that have no API, so the event requirements are met and visible in the demo.

## Spec requirements

SF-1, MT-6, VR-2 (Must), VR-3 (Should). Event rules EV-3 to EV-6.

## Checklist

Steps 1 to 3 can be done before any code exists.

1. **Workspace and project.** One workspace for the team; project named after the team. Copy the project ID and an API key with `ingest` scope into `.env`.
2. **Ask the PRISM team** (spec Q1, Q2, Q6):
   - Can the Knowledge Base show a claim as grounded, or is it upload-only?
   - Can a guardrail act on runs recorded over HTTP from another gateway, and where does the flag appear?
   - Does an evaluator on an AI-written output count as "scored or classified output"?
3. **Check the plan.** Evaluators are listed as a Builder feature and cost 5 credits per run; the free tier has 100 credits a month.
4. **Guardrail.** Create a Prompt Injection rule with action "flag" on the project.
5. **Knowledge Base.** Upload `out/knowledge_base.md` (from task 02).
6. **Evaluator.** Create one on the recorded line output. Default target is the line status; move it to the line reading if the PRISM team says that qualifies. Run it on demo runs only, to save credits.
7. **Review queue.** Confirm how items arrive (PRISM sends low-scoring traces there on its own). If one appears during testing, keep it for the demo.
8. **Verify** with a run of the PDF fixture: the run shows every stage, the guardrail flag on the injected passage and the evaluator result.

## What the code provides for this

- The recorded run with the original text as the safety stage's input (tasks 05, 13).
- The Knowledge Base document (task 02).
- The line outputs the evaluator scores (task 13).

## Acceptance criteria

- A guardrail flag, a Knowledge Base source and an evaluator result are each visible in the dashboard for one demo run.
- The answers to the three questions are written into spec section 13.
