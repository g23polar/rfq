# RFQ-to-Quote Agent — Product Spec

| | |
|---|---|
| **Status** | Draft v2, revised after product review (pre-technical); changes listed in Section 15 |
| **Event** | Get Hired Hack @ Columbia Startup Lab, Oct 10, 2026 |
| **Track** | RudCo: RFQ to Quote |
| **Submission deadline** | 4:30 PM EDT, Oct 10 (target: submitted by 4:15) |
| **Working name** | RFQ-to-Quote Agent (placeholder) |

---

## 1. Product description

Industrial buyers send requests for quotes (RFQs) as messy emails, PDFs and spreadsheets. The same item gets written many different ways, and every line needs to be decoded into a precise specification, matched to stock, priced competitively and checked for compliance requirements. Today a person does this by hand, line by line.

The RFQ-to-Quote Agent takes a messy RFQ and turns it into a ready-to-send quote. For every line it shows what it understood, where in the original document that came from, which catalog item it matched, how the price was calculated and how it compares to the market, and which compliance requirements are or are not met.

When the agent isn't sure, it says so. Lines that are ambiguous, conflicting or incomplete are not guessed. They are held back and turned into a clear question for the buyer.

**One-line description:** An RFQ agent that quotes what it can prove and asks about what it can't.

---

## 2. The problem

- **Inconsistent descriptions.** "304 SS sheet 16ga 4x8" and "Stainless 304, 0.060 in, 48 x 96" describe the same item. A quoting specialist has to recognize that every time.
- **Hidden requirements.** Certification, country-of-origin and mill test report requirements are often buried in an email header or a footnote, not on the line itself.
- **Pricing judgment.** Each price needs to be competitive against the market without going below cost, and today the reasoning lives in someone's head.
- **Costly guesses.** A wrong assumption (feet vs. inches, 304 vs. 304L, a missing quantity) produces a wrong quote, lost margin or a rejected shipment.
- **Untrustworthy automation.** A tool that confidently fills in blanks is worse than no tool, because errors become invisible.

---

## 3. Users

| User | Role | What they need |
|---|---|---|
| **Quoting specialist** (primary) | Works at a metals supplier or distributor such as RudCo; turns RFQs into quotes | Speed on routine lines, a clear view of what needs their judgment, and confidence that nothing was silently guessed |
| **Buyer** (recipient) | Purchasing agent at an industrial customer | An accurate quote, clearly stated assumptions, and short, specific questions on anything unclear |
| **Sales manager** (secondary) | Oversees quoting quality | Evidence that prices are competitive and margins are protected |

The primary user should be able to use the product without a walkthrough.

---

## 4. Goals and non-goals

### Goals
1. Turn a messy RFQ in any of the three common formats into a structured, priced quote.
2. Make every value on the quote traceable to its source (the RFQ text, the catalog or the price benchmark).
3. Never guess on an ambiguous line; route it to the buyer with a specific question.
4. Explain every price in plain language against a market benchmark.
5. Catch compliance requirements and show whether each one is met.
6. Resist manipulated input (text in an RFQ trying to instruct the AI).
7. Demonstrate measured accuracy on a labeled test set.

### Non-goals (for this event)
- Sending emails or quotes directly to buyers (we produce them; a human sends them).
- Real supplier inventory, real live market pricing or integration with an ERP system.
- Handwritten or scanned image-only documents.
- Negotiation, order entry or invoicing after the quote.
- Materials beyond common metals (stainless, carbon steel, aluminum) and forms beyond sheet, plate, bar and tube.

---

## 5. Guiding principles

1. **Quote what you can prove, ask about what you can't.** No line is quoted on a guess. The only inferences allowed on a quoted line are the named ones in Section 7.1; anything else is a question.
2. **Show your work.** Every value can be clicked back to where it came from.
3. **The AI reads language; rules make decisions.** AI is used to interpret messy text and to word questions. Decisions with a right answer (unit conversions, matching, pricing math, status) follow fixed, explainable rules. This is also the main defense against manipulated input: text in an RFQ cannot change a price or a status, because the AI never sets either.
4. **Assumptions are visible, never hidden.** If the agent assumes something minor, the quote says so on that line.
5. **"Unknown" is never shown as "OK."** A requirement that can't be confirmed is shown as unconfirmed.
6. **Honest data.** Demo catalog and price benchmarks are synthetic and labeled as such.
7. **Two audiences, two views.** The specialist sees cost, margin and the full reasoning. The buyer document shows price, spec, assumptions and compliance, and never cost or margin.

---

## 6. The flow

The agent processes an RFQ in ten stages. Each line item carries a running list of **issues** (missing information, conflicts, assumptions) that grows as it moves through the stages. The final status of each line is decided from that list.

| # | Stage | Purpose | Takes in | Produces | Boundary (what it does NOT do) |
|---|---|---|---|---|---|
| 0 | **Intake** | Read the RFQ and split it into header terms and individual line items | An email, PDF or spreadsheet | The RFQ's general terms (due date, delivery, blanket requirements) and a list of raw line items, each with a pointer to where it appears in the original | Does not interpret any line |
| 1 | **Safety screen** | Detect text that tries to instruct or manipulate the AI | All RFQ text | A clean / flagged / blocked verdict and the offending passages | Flagged passages are removed and set aside for review; the rest of the RFQ continues |
| 2 | **Read the line** | Interpret each line into specification fields (material, grade, form, dimensions, quantity, standard, certifications) | One raw line plus relevant header terms | Each field with its value and the exact source text it came from; fields not stated are left blank | Does not fill in anything the text doesn't say. Any field whose cited source text isn't actually in the document is discarded and logged |
| 3 | **Standardize** | Convert the reading into one standard form so different wordings of the same item become identical | The interpreted fields | A standardized specification and an item "fingerprint"; any assumptions or conflicts are added as issues | Applies fixed conversion rules only (units, gauges, abbreviations); every inference is recorded as an assumption |
| 4 | **Match to catalog** | Find the supplier catalog item that fulfills the line | The standardized spec, plus the line's compliance requirements as constraints | Best match, its match strength, up to two runner-ups, and differences from the request | Does not accept a weak or tied match; substitutions are proposed, never assumed; an item that meets the line's requirements is preferred over a closer one that doesn't |
| 5 | **Price** | Calculate a competitive price and explain it | The spec, the matched item and market benchmarks | Unit and extended price, how it compares to the benchmark range, margin, and a plain-language explanation | Never prices below cost; flags prices above the benchmark range or based on stale benchmarks |
| 6 | **Compliance check** | Report, with evidence, whether the matched item meets each requirement read in stage 2 | Header and line requirements, plus the matched item's attributes | Each requirement marked met / not met / unknown, with evidence | Does not treat "unknown" as met |
| 7 | **Decide and ask** | Assign each line a status and, where needed, draft a question for the buyer | All issues collected for the line | A line status (see Section 7) and, for unclear lines, a specific question with options | The AI only words the question; it does not choose the status |
| 8 | **Verify** | Run fixed checks before anything goes out: every shown value has a verified source or a named assumption, every number in a price explanation equals the calculated number, and no price is below the floor | The completed lines | Pass or fail per line; a failed line is not quoted and gets the specialist review flag (Section 7.3) | Does not use AI to judge its own work |
| 9 | **Assemble** | Produce the deliverables | All verified lines | A ready-to-send quote and a buyer email listing all open questions | Produces documents for a human to send; does not send them |

Every stage is recorded in Block Convey's PRISM so the full run for any RFQ can be inspected step by step.

---

## 7. Line statuses

| Status | Meaning | When it is used | What the quote shows |
|---|---|---|---|
| ✅ **Quoted** | Fully understood, matched and priced | No issues on the line | Price and spec |
| ⚠️ **Quoted with assumptions** | Quoted, but relies on a minor stated assumption | Only assumptions on the allowed list in Section 7.1 | Price, spec and each assumption in plain language |
| ❓ **Needs clarification** | Not quoted until the buyer answers | Missing required information, conflicting information, a proposed substitution, two equally good catalog matches, or a compliance requirement that cannot be confirmed either way | A specific question to the buyer, with options where possible |
| ⛔ **No bid** | Cannot be supplied as requested | No catalog item fits, or no catalog item can meet a stated compliance requirement | The reason |

### 7.1 Allowed assumptions

This is the complete list. An inference that is not on it makes the line "Needs clarification".

| Assumption | Example | Why it is low-risk |
|---|---|---|
| A sheet or plate size written as two bare numbers, both 12 or less, is in feet | "4x8" → 48 x 96 in | These are the standard stock sizes; a 4 in x 8 in piece would be written with units |
| A stated thickness within normal tolerance of a standard gauge or stock thickness means that standard thickness | 0.060 in stainless → 16 ga (0.0625 in) | Buyers round thickness; the tolerance value is set in the technical plan |
| No standard stated: the default standard for that grade and form applies | 304 sheet → ASTM A240 | Taken from the reference table, not from the AI |
| Dual-certified stock fills a request for either grade | 304 requested → 304/304L supplied | The material is certified to both grades |

Both example strings from the track rely on one of these, so they come out as "Quoted with assumptions", not "Quoted". That is intended.

### 7.2 Status rules

Applied in this order; the first rule that fits decides the status.

1. Any missing required field, conflict, unlisted inference, tied or weak match, proposed substitution, or unconfirmable requirement → **Needs clarification**.
2. No catalog item fits, or none meets a stated requirement → **No bid**.
3. The line relies on one or more allowed assumptions → **Quoted with assumptions**.
4. Otherwise → **Quoted**.

### 7.3 Specialist review flag

Some problems are for the specialist, not the buyer. A line gets a review flag, separate from its status, when its price is above the benchmark range, its benchmark is out of date, it fails verification (stage 8), or text was withheld from it by the safety screen. A flagged line stays off the buyer document until the specialist clears it.

---

## 8. Product requirements

Priority: **Must** = required for submission; **Should** = strongly improves judging score; **Could** = if time allows.

### 8.1 Intake
| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| IN-1 | Accept an RFQ pasted or uploaded as email text | Must | Email fixture produces correct line count |
| IN-2 | Accept an RFQ as a PDF | Must | PDF fixture produces correct line count |
| IN-3 | Accept an RFQ as a spreadsheet | Should | Spreadsheet fixture produces correct line count |
| IN-4 | Separate RFQ-wide terms (due date, delivery, blanket certification requirements) from line items | Must | Blanket requirements apply to every line |
| IN-5 | Keep a reference from every line back to its location in the original document | Must | Each line shows its source location |

### 8.2 Safety
| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| SF-1 | Screen all incoming RFQ text for attempts to instruct or manipulate the AI, using a PRISM guardrail | Must | Seeded injection in the PDF fixture is caught |
| SF-2 | Remove flagged passages from processing and show them to the user as withheld | Must | Injected instruction has no effect on any price or status |
| SF-3 | Continue processing the rest of a flagged RFQ | Should | Clean lines in the same RFQ are still quoted |
| SF-4 | Treat buyer commercial requests ("best price", "can you do 10% off") as terms shown to the specialist, neither as manipulation nor as instructions | Should | Discount-request fixture changes no price and is not withheld |

### 8.3 Reading and standardizing
| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| RD-1 | Interpret each line into material, grade, form, dimensions, quantity, unit, standard and certification requirements | Must | Golden-set field accuracy reported |
| RD-2 | For every interpreted value, record the exact source text it came from | Must | Every displayed field can show its source text |
| RD-3 | Discard any value whose cited source text does not appear in the RFQ, and log it | Must | Demonstrable in the run record |
| RD-4 | Leave fields blank when the RFQ doesn't state them. The AI never fills a field from its own knowledge; the only source of unstated values is the reference tables, applied as allowed assumptions (Section 7.1) | Must | Missing-grade fixture line shows grade as missing |
| RD-5 | Convert all dimensions to one unit system, including fractions and gauge numbers (gauge interpreted by material) | Must | Both example strings from the track produce the same fingerprint, each shown as quoted with assumptions |
| RD-6 | Expand common abbreviations and alternate names (e.g. "SS" → stainless) | Must | — |
| RD-7 | Record any inference (e.g. "4x8" read as feet, default standard from grade) as a visible assumption | Must | Assumption appears on the quote line |
| RD-8 | Detect conflicts within a line (e.g. stated thickness disagrees with stated gauge) | Must | Conflict fixture line becomes "Needs clarification" |
| RD-9 | Detect duplicate lines written differently within one RFQ. Both are still quoted separately and each notes the other; quantities are never merged | Should | Duplicate fixture lines are linked |

### 8.4 Catalog matching
| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| MT-1 | Match each standardized line to a supplier catalog item | Must | Golden-set match accuracy reported |
| MT-2 | Show match strength, the best match and up to two alternatives | Must | Visible in line detail |
| MT-3 | Treat weak or tied matches as "Needs clarification" | Must | — |
| MT-4 | Propose substitutions (a different grade or standard, e.g. 316 for 304) only as a question to the buyer. Dual-certified stock that meets the requested grade is not a substitution; it is an allowed assumption (Section 7.1) | Should | Substitution fixture line produces a question |
| MT-5 | Mark lines with no viable match as "No bid" with a reason | Must | Not-in-catalog fixture line is "No bid" |
| MT-6 | Load the reference tables into the PRISM Knowledge Base and ground at least one stated claim against it (e.g. a gauge conversion or a default standard). Matching itself stays a fixed lookup against the catalog | Must | The grounded claim and its Knowledge Base source are visible in PRISM |

### 8.5 Pricing
| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| PR-1 | Price each matched line from its weight, cost and a market benchmark | Must | Price shown per unit and extended |
| PR-2 | Never price below cost plus a minimum margin | Must | Below-cost scenario is blocked |
| PR-3 | Show the benchmark range, where the price sits in it, the margin, and the benchmark's source and date. Cost and margin are specialist-only and never appear on the buyer document | Must | Visible in line detail; absent from the quote document |
| PR-4 | Provide a plain-language explanation of why the price is competitive, built from the calculated numbers | Must | Every number in the explanation matches the calculation |
| PR-5 | Flag prices above the benchmark range or based on outdated benchmarks | Should | Line carries the specialist review flag (Section 7.3) |
| PR-6 | Label demo benchmarks as synthetic | Must | Label visible in UI and quote |
| PR-7 | Use one documented pricing rule: where in the benchmark range we aim, the minimum margin, and what happens when the floor is above the range | Must | Rule listed in README; every price reproduces from it |

### 8.6 Compliance
| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| CP-1 | Detect mill test report requirements | Must | — |
| CP-2 | Detect country-of-origin / domestic-sourcing requirements | Must | "Domestic only" fixture is detected |
| CP-3 | Detect specification certification requirements (e.g. ASTM) | Must | — |
| CP-4 | Check each requirement against the matched item and mark it met / not met / unknown | Must | Non-compliant item is flagged on the DFARS fixture |
| CP-5 | Apply RFQ-wide requirements to every line | Must | — |

### 8.7 Decisions and buyer questions
| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| DC-1 | Assign every line exactly one of the four statuses using fixed, documented rules | Must | Status rules listed in README |
| DC-2 | For every "Needs clarification" line, draft a specific question, with options where possible | Must | Every ❓ line has a question |
| DC-3 | Combine all questions into one buyer email | Must | Email produced alongside the quote |
| DC-4 | Allow the specialist to answer a question or correct a field and re-quote that line | Should | Answering the question on a ❓ fixture line turns it into a quoted line |

### 8.8 Verification
| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| VR-1 | Re-check that every number in each price explanation matches the calculation | Must | — |
| VR-2 | Attach a PRISM Evaluator to at least one output (line status or price claim) | Must | Evaluator result visible in PRISM |
| VR-3 | Send borderline results to PRISM's review queue | Should | At least one item in the queue during demo |
| VR-4 | Record every stage of every RFQ as one run in PRISM, under a consistent agent name | Must | Full run visible in PRISM |

### 8.9 Output and experience
| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| UX-1 | Show all lines in one quote table with clear status badges | Must | — |
| UX-2 | Let the user expand any line to see: original text, interpreted spec, matched item and alternatives, price math, compliance results and issues | Must | — |
| UX-3 | Show summary counts by status at the top | Should | — |
| UX-4 | Produce a ready-to-send quote document (header, priced lines, assumptions, compliance notes, validity, pending lines; no cost or margin) | Must | — |
| UX-5 | Export the quote as a printable document | Should | — |
| UX-6 | Link each RFQ to its PRISM run | Should | — |
| UX-7 | Usable by a quoting specialist without a walkthrough | Must | Judged in demo |

### 8.10 Quality measurement
| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| QA-1 | Maintain a labeled test set of ~20 RFQ lines with expected specs and statuses | Must | — |
| QA-2 | Report results on that set as expected vs. actual status, stating the set size, with the two error types separated: wrongly quoted (dangerous) and wrongly asked (annoying) | Must | Table and headline numbers shown in demo and Devpost |
| QA-3 | Let a judge type their own line and see it processed live | Should | Works in demo |

---

## 9. Event and platform requirements

| ID | Requirement | Covered by |
|---|---|---|
| EV-1 | Built entirely during the event | — |
| EV-2 | Uses NicrronNinoo for AI model access | Stages 2, 7 |
| EV-3 | Uses Block Convey PRISM; one workspace per team, project named after the team, agent name on every recorded call | VR-4 |
| EV-4 | PRISM Guardrail on at least one input | SF-1 |
| EV-5 | PRISM Evaluator on at least one scored or classified output | VR-2 |
| EV-6 | At least one claim grounded through the PRISM Knowledge Base | MT-6 |
| EV-7 | Demonstrates what the product does when it isn't sure | Section 7, DC-1/2 |
| EV-8 | A judge can check the output | RD-2, UX-2, PR-3 |
| EV-9 | Devpost page: name and one-liner, track, what and why, accuracy and uncertainty handling, tools (NicrronNinoo and Block Convey), team and roles, video link, GitHub link | Submission checklist |

### Track requirement traceability

| RudCo asks for... | Requirements |
|---|---|
| Handle messy emails, PDFs and spreadsheets | IN-1, IN-2, IN-3 |
| Recognize the same item written different ways | RD-5, RD-6, RD-9 |
| Parse each line into a standard spec | RD-1 to RD-8 |
| Match to a supplier catalog | MT-1 to MT-6 |
| Price against benchmarks and explain why it's competitive | PR-1 to PR-6 |
| Flag compliance requirements | CP-1 to CP-5 |
| Send ambiguous lines back with a question instead of guessing | DC-1 to DC-3, MT-3, MT-4, RD-8 |
| A ready-to-send quote | UX-4, UX-5, DC-3 |

---

## 10. Demo data

All demo data is synthetic and labeled as such.

- **Supplier catalog:** ~60 items across stainless, carbon steel and aluminum in sheet, plate, bar and tube, each with cost, origin, mill test report availability and certifications.
- **Market benchmarks:** price ranges by grade and form, each with a source label and date.
- **Reference tables:** gauge-to-thickness by material, material densities, abbreviations, default standards by grade, allowed substitutions.
- **Three sample RFQs** (email, PDF, spreadsheet), seeded with:
  - the two equivalent strings from the track description
  - a duplicate item written two ways
  - a line with no grade
  - a bare "4x8" sheet size (quoted, with the feet assumption shown)
  - a bar length with no unit (sent to clarification)
  - a buyer discount request in the email header (shown as a term; changes nothing)
  - a gauge/thickness conflict
  - a "domestic material only" requirement against a non-domestic catalog item
  - an item not in the catalog
  - a hidden instruction trying to change prices (PDF)
- **Labeled test set:** ~20 lines with expected results.

---

## 11. Success measures

| Measure | Target |
|---|---|
| Test-set accuracy (correct quote or correct referral to buyer) | ≥ 85% |
| Lines wrongly quoted when they should have been asked or declined | 0 |
| Share of test-set lines quoted without a question | Reported, no target |
| Price explanations whose numbers don't match the calculation | 0 |
| Seeded manipulation attempt has any effect | No |
| Time to process a sample RFQ | Under 1 minute, with lines appearing as they finish |
| Every displayed value traceable to a source | 100% |

---

## 12. Demo script (~2 minutes)

1. Upload the messy sample RFQ (a pre-processed copy is ready in case the live run is slow).
2. Point to the two differently written lines that became the same item.
3. Expand one quoted line: original text → interpreted spec → matched item → price math against the benchmark.
4. Show the ❓ lines and the buyer email with specific questions; answer one and watch that line re-quote (if DC-4 is built).
5. Show the ⛔ line and its reason.
6. Show the withheld manipulation attempt.
7. Open the PRISM run: every stage, the guardrail catch, the evaluator verdict.
8. Close on the test-set accuracy number.

---

## 13. Open questions and risks

| # | Question / risk | Impact | Plan |
|---|---|---|---|
| Q1 | Does the PRISM Knowledge Base support direct lookups from our product, or only grounding checks after the fact? | Determines how MT-6 is demonstrated | Ask the PRISM team at setup |
| Q2 | PRISM can only *block* (not just flag) on traffic routed through its proxy, which supports specific model providers. Can it screen NicrronNinoo traffic? | Determines how SF-1 is demonstrated | Ask at setup; fallback is screening through a supported provider plus our own check |
| Q3 | Evaluator runs cost PRISM credits (limited supply) | Limits how often VR-2 can run | Run on demo sessions only |
| Q4 | Can we get a real (anonymized) RFQ from RudCo? | Grounds the demo in their actual problem | Ask RudCo on the floor early |
| Q5 | We do not have a PRISM workspace or API key yet, and its public docs only describe run recording; guardrails, evaluators and the Knowledge Base may be dashboard-only | Four Musts (SF-1, MT-6, VR-2, VR-4) depend on it | Get the key and answers to Q1 and Q2 before the technical plan is final |
| Q6 | Statuses and prices are rule-made, so an evaluator on them checks little. Does an evaluator on an AI-written output (the line reading or the buyer question) satisfy EV-5's "scored or classified output"? | Decides where VR-2 attaches | Ask the PRISM team; default stays line status |
| R1 | Time: ~4 hours of build | Scope | Cut order: printable export → duplicate linking → review queue → AI-worded questions (use templates) → substitution proposals → re-quote after an answer → spreadsheet intake (cheap, and one of the three formats the track names, so cut last). Never cut: source tracing, fixed pricing rules, the four statuses, the three PRISM requirements |
| R2 | Synthetic data could be mistaken for real pricing | Trust | Label it everywhere |

---

## 14. Out of scope

Sending messages to buyers, live market data, real inventory, ERP integration, scanned or handwritten documents, multi-currency, freight and lead-time quoting, user accounts and permissions.

---

## 15. Changes in this revision

- **Closed list of allowed assumptions (7.1).** "Low-risk assumption" was undefined, so the status rules were not fixed. The track's own two example strings need an assumption each and now come out as "Quoted with assumptions".
- **Status rules written out in order (7.2)**, including the missing case: a requirement that can't be confirmed is a question.
- **Specialist review flag (7.3).** Internal problems (price above market, failed verification, withheld text) no longer have to be forced into a buyer-facing status.
- **Dual-certified stock is not a substitution (MT-4).** Otherwise every 304 line would become a question.
- **Compliance requirements constrain matching (stages 4 and 6).** Previously a non-compliant item could be chosen when a compliant one existed.
- **Verify stage made concrete (stage 8)**: fixed checks, no AI judging its own work.
- **Knowledge Base grounds a claim, not the matching (MT-6).**
- **Buyer and specialist views separated (principle 7, PR-3, UX-4)** so cost and margin can't leak onto the quote.
- **Pricing rule must be stated (PR-7)** and benchmarks are by grade, not material.
- **Buyer discount requests are terms, not attacks (SF-4).**
- **Accuracy reported as expected vs. actual with error types split (QA-2)**, plus a judge-typed line (QA-3).
- **Re-quote after an answer promoted to Should (DC-4); spreadsheet intake moved to the end of the cut order (R1).**
- **Field confidence levels removed (stage 2)**: nothing used them.
- **Demo data:** the ambiguous-units case is now a bar length; a bare "4x8" sheet is an allowed assumption.
- **New open questions Q5 and Q6** on PRISM access and where the evaluator attaches.
