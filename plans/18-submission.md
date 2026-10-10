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

EV-9, and the demo script in spec section 12.

## Checklist

| Item | Source |
|---|---|
| Name and one-line description | Spec section 1; the working name is still a placeholder |
| Track | RudCo: RFQ to Quote |
| What it does and why | Spec sections 1 and 2 |
| Accuracy and how uncertainty is handled | `out/eval_report.md` (task 16), spec section 7 |
| Tools used | NicrronNinoo (model access), Block Convey PRISM (recording, guardrail, evaluator, Knowledge Base) |
| Team and roles | To be filled in |
| Video link | Recorded from the demo script, about 2 minutes |
| GitHub link | github.com/g23polar/rfq, pushed, with README |

## Before recording

- Run each fixture once so repeat runs are served from Nicrron's cache.
- Keep a finished run open in a second tab in case the live upload is slow.
- Open the PRISM run for the PDF fixture in advance.

## Demo run-through (spec section 12)

1. Upload the messy RFQ.
2. Two differently written lines, one item.
3. Expand a quoted line: text → spec → match → price math.
4. The questions and the buyer email; answer one and watch it re-quote, if built.
5. The No bid line and its reason.
6. The withheld manipulation attempt.
7. The PRISM run: stages, guardrail flag, evaluator result.
8. The accuracy numbers.

## Acceptance criteria

- Every item in the checklist is on the Devpost page.
- The repo is pushed and runs from a clean checkout by following the README.
- No keys are in the repo.
- Submitted by 4:15 PM EDT.
