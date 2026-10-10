# 18: Submission

| | |
|---|---|
| **Status** | Not started |
| **Owner** | User |
| **Depends on** | all |
| **Deadline** | 4:30 PM EDT; target 4:15 PM |

## Goal

Submit a Devpost page that meets the event checklist, with a video and a repo a judge can run.

## Spec requirements

EV-9, and the demo script in spec section 17.

## Checklist

| Item | Source |
|---|---|
| Name and one-line description | Spec section 1; the working name is still a placeholder |
| Track | RudCo: RFQ to Quote |
| What it does and why | Spec sections 1 to 3 |
| Accuracy and how uncertainty is handled | `out/eval_report.md` (task 16); statuses in spec section 9 |
| Tools used | NicrronNinoo (model access), Block Convey PRISM (recording, guardrail, evaluator, Knowledge Base) |
| Team and roles | To be filled in |
| Video link | Recorded from the demo script, about 2 minutes |
| GitHub link | github.com/g23polar/rfq, pushed, with README |

## Before recording

- Run each fixture once so repeat runs are served from Nicrron's cache.
- Keep a finished run open in a second tab in case the live upload is slow.
- Open the PRISM run for the PDF fixture in advance.

## Demo run-through (spec section 17)

1. Drop in the email thread; the draft appears with status counts.
2. Two differently written lines, one item.
3. Expand a quoted line: source text → spec → matched item → price against the benchmark → compliance.
4. The missing-grade line: priced alternates, not a stall.
5. The buyer email: few, grouped, specific questions.
6. A "needs specialist review" line (below the margin floor) that never reaches the buyer.
7. The withheld manipulation attempt.
8. PRISM: the run, the guardrail flag, the evaluator verdict.
9. Approve → the buyer-facing quote, with no internal data on it.
10. The metrics: silent errors, routing accuracy, over-ask count.

Step 7 uses the PDF fixture; the rest use the email thread. Have both loaded.

## Acceptance criteria

- Every item in the checklist is on the Devpost page.
- The repo is pushed and runs from a clean checkout by following the README.
- No keys are in the repo.
- Submitted by 4:15 PM EDT.
