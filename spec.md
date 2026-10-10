# RFQ-to-Quote Agent — Product Spec

| | |
|---|---|
| **Version** | 2.0 — draft for review (pre-technical) |
| **Event** | Get Hired Hack @ Columbia Startup Lab, Oct 10, 2026 |
| **Track** | RudCo: RFQ to Quote |
| **Submission deadline** | 4:30 PM EDT, Oct 10 (target: submitted by 4:15) |
| **Working name** | RFQ-to-Quote Agent (placeholder) |
| **Priority key** | **M** = hackathon MVP (must ship today) · **S** = stretch (today, if time) · **L** = later (product roadmap, shown in pitch only) |

### What changed from v1, and why

| v1 assumption | v2 position | Why |
|---|---|---|
| Ambiguous line → hold it and ask the buyer | Quote everything that can be quoted; for ambiguous lines, **price labeled alternates and ask in parallel**. Hold a line only when no reasonable option exists | In distribution, the first credible quote usually wins. A tool that stalls on every ambiguity loses the deal. Alternates are not guesses: they are explicit, priced options |
| Agent output = finished quote | Agent output = **draft quote that a quoting specialist reviews, edits and approves** | This is how RFQ automation is built and bought in the industry; autonomy is a dial, not a default |
| One kind of "needs attention" | Two kinds: **needs buyer input** (external) vs. **needs specialist review** (internal, e.g. margin below floor, weak match) | Internal problems must never turn into buyer emails, and vice versa |
| Price = weight × benchmark $/lb | Price reflects how metals are actually quoted: **base + extras/processing + alloy surcharge (stainless)**, in the buyer's unit of measure, with minimum charges and a short validity window | Matches real metals pricing; judges from the industry will look for it |
| No availability | **Stock check and lead time** per line | Core to every real quote |
| AI's self-reported confidence | Confidence comes from **verifiable signals** (source evidence found, rules satisfied, two independent matching methods agreeing) | Model self-confidence is not reliable; agreement between independent checks is |
| Catalog matching only | Matching also uses **customer part-number cross-references** that are learned from confirmed answers | Cross-referencing customer part numbers is the single biggest manual time sink distributors report |
| Edge cases implicit | **Explicit edge-case catalogue** (Section 12) with expected behavior | Overlooked cases are where trust is lost |

---

## 1. Summary

Industrial buyers send requests for quotes (RFQs) as messy emails, PDFs and spreadsheets. Every line has to be decoded into a precise specification, matched to stock, priced, and checked for compliance. Today a person does this by hand, line by line, while a competitor races to answer the same RFQ.

The RFQ-to-Quote Agent turns a messy RFQ into a **reviewable draft quote in under a minute**. Every value on it is traceable to its source. Every price is explained against a market benchmark. Every compliance requirement is marked met, not met, or unknown. Where the RFQ is ambiguous, the agent offers priced alternates and drafts a specific question, instead of guessing. A quoting specialist reviews, adjusts and approves, then sends.

**One-line description:** An RFQ agent that drafts the quote in a minute, shows its work on every line, and never hides a guess.

---

## 2. Background: how RFQ quoting works today

- **Speed decides most RFQs.** Distributors report that the first credible quote usually wins, even at a slightly higher price, and the first hour after an RFQ arrives is the best window.
- **Manual flow:** read the RFQ → decide what to quote → translate each line into the supplier's own items (often cross-referencing the customer's part numbers) → look up price, stock and history → assemble and send the quote.
- **Industry-standard automation** parses the RFQ as-is, resolves each line to a sellable item (with alternatives when the exact item isn't available), prices by the supplier's own rules, and hands a rep a **draft to review, adjust, approve and send**. Buyers of this software judge it on matching accuracy *and* honesty about uncertainty: stated confidence per line, weak matches surfaced, uncertain lines routed to a person.
- **Metals pricing specifics:** stainless steel is typically priced as a **base price, plus extras** (non-standard thickness, finish, packaging), **plus an alloy surcharge** that tracks nickel, chrome and molybdenum costs, published monthly per grade and often applied at time of shipment. Market prices are commonly expressed per hundredweight (cwt). Because metal prices move, quotes carry short validity windows.

---

## 3. Problem statement

1. **Inconsistent descriptions.** "304 SS sheet 16ga 4x8" and "Stainless 304, 0.060 in, 48 x 96" describe the same item; the specialist must recognize that every time.
2. **Hidden requirements.** Certification, country-of-melt and mill test report requirements are buried in headers, footers and email threads.
3. **Pricing judgment lives in someone's head.** Competitive vs. below cost, which surcharge applies, what this customer paid last time.
4. **Ambiguity is expensive in both directions.** A wrong guess (feet vs. inches, 304 vs. 304L) creates a bad quote; a slow round of questions loses the deal.
5. **Untrustworthy automation is worse than none.** A tool that confidently fills blanks makes errors invisible.

---

## 4. Users and jobs to be done

| User | Job to be done | What success looks like |
|---|---|---|
| **Quoting specialist** (primary) | "When an RFQ lands, help me get an accurate quote out before competitors, and show me exactly which lines need my judgment." | Clean lines need no edits; risky lines are obvious; approving a quote takes minutes |
| **Buyer** (recipient) | "Give me a complete, accurate quote fast, with clear assumptions and as few back-and-forth questions as possible." | Every line answered (priced, alternates, or no-bid with reason); short, specific questions |
| **Sales manager** (secondary) | "Make sure we're competitive without giving away margin, and that we never ship non-compliant material." | Margin floors enforced; compliance gaps visible; full audit trail |

The quoting specialist must be able to use the product without a walkthrough.

---

## 5. Goals and non-goals

### Goals
1. Turn a messy RFQ (email, PDF or spreadsheet) into a reviewable draft quote in under a minute.
2. Answer **every** line: priced, priced with alternates, needs input, or no-bid with a reason.
3. Make every value traceable to its source: RFQ text, catalog, cross-reference, benchmark or rule.
4. Never hide a guess; minimize unnecessary questions.
5. Explain every price against a market benchmark in plain language.
6. Catch compliance requirements and show whether each is met.
7. Keep a human in control of what is sent.
8. Resist manipulated input and never leak internal data (cost, margin) to the buyer.
9. Demonstrate measured accuracy on a labeled test set.

### Non-goals (hackathon)
- Automatically sending emails or quotes to buyers.
- Live ERP, live inventory or live market price integration (synthetic data, clearly labeled).
- Handwritten or image-only scans; CAD/drawing interpretation.
- Order entry, invoicing, negotiation.
- Products beyond common metals (stainless, carbon steel, aluminum) in sheet, plate, bar, tube and pipe.

---

## 6. Product principles

1. **Answer every line, hide no guess.** Each line ends with a clear status. Inferences are visible.
2. **Options before questions.** When a reasonable set of options exists, price them as labeled alternates and ask the buyer to pick. Hold a line only when no reasonable option exists.
3. **Ask only what blocks the quote, and ask it once.** Questions are grouped, specific, and offer options.
4. **The AI reads and writes language; rules make decisions.** Interpreting messy text and wording questions are AI tasks. Unit conversion, matching thresholds, pricing math, compliance verdicts and line status follow fixed, documented rules.
5. **Confidence is earned, not self-reported.** A line is "confident" when its source evidence is found, rules are satisfied, and independent checks agree.
6. **Internal stays internal.** Cost, margin, supplier names and internal notes never reach buyer-facing output.
7. **Unknown is never shown as OK.**
8. **Human approves what is sent.** Autonomy is a setting the business can widen later.
9. **Honest data.** Synthetic catalog and benchmarks are labeled as such everywhere.

---

## 7. Approach and alternatives considered

| Option | Description | Verdict |
|---|---|---|
| A. Single AI prompt | Send the RFQ to a model, ask for a quote | **Rejected.** Unverifiable, hallucinates specs and prices, and is the "thin wrapper" the event excludes |
| B. Rules only | Pattern-matching parsers and lookup tables | **Partially used.** Reliable for unit conversion, spreadsheets and pricing math; too brittle for free-text emails |
| C. Extract → standardize → match | AI reads the line into fields; rules standardize; catalog lookup finds the item | **Used** as the primary path |
| D. Catalog-constrained selection | Retrieve likely catalog items first, then have the AI choose among that closed list (or "none of these") | **Used** as an independent second path |
| E. Multi-agent system | Several autonomous agents negotiating the quote | **Rejected for now.** Harder to inspect and explain; no accuracy benefit at this scale |

**Chosen approach:** a hybrid (B + C + D). Paths C and D resolve each line independently. **When they agree, the match is confident; when they disagree, the line goes to review.** This turns "confidence" into something the product can show and prove.

**Where the "agent" is:** the agent decides, per line, which checks and lookups to run. It retries with relaxed criteria when a strict match fails (to find alternates). It decides whether a line needs the buyer, the specialist, or neither. It processes buyer replies to re-quote affected lines (stretch).

---

## 8. The flow

Each line item carries a running list of **issues** (missing, conflict, assumption, risk). Each issue is tagged **buyer-facing** or **internal**. Line status is decided from that list by fixed rules. Every stage is recorded in Block Convey's PRISM, so the full run for any RFQ can be inspected.

| # | Stage | Purpose | Takes in | Produces | Boundary |
|---|---|---|---|---|---|
| 0 | **Triage** | Decide what this message is | Incoming email/file | Type (new RFQ / revision / not an RFQ), customer, due date, requested response format | Non-RFQs are labeled and not quoted |
| 1 | **Intake & segmentation** | Split the RFQ into its parts | The RFQ and attachments | RFQ-wide terms, line items (with the buyer's line numbers and a pointer to the source location), notes, attachment references | Strips forwarded history, signatures and disclaimers; interprets nothing |
| 2 | **Safety screen** | Detect text trying to manipulate the AI | All RFQ text | Clean / flagged / blocked, with offending passages | Flagged passages are withheld from processing and shown to the specialist; the rest continues |
| 3 | **Interpret** (AI) | Read each line into specification fields | One line plus relevant RFQ terms | Material, grade, form, dimensions, quantity, unit, standard, finish/temper, tolerances, certifications, each with the exact source text | Leaves unstated fields blank. Any field whose cited source text isn't actually in the RFQ is discarded and logged |
| 4 | **Standardize & validate** (rules) | One standard form so different wordings become identical | Interpreted fields | Standardized spec, item fingerprint, issues (missing, conflict, assumption) | Fixed conversion rules only; every inference logged as an assumption |
| 5 | **Resolve to catalog** | Find the item(s) that fulfill the line | Standardized spec, customer cross-references, catalog | Best match, alternates, match strength, whether both matching paths agreed | Weak, tied or disagreeing matches are never silently accepted; substitutions are always offered, never assumed |
| 6 | **Availability** | Can we ship it, and when | Matched item(s), quantity | In stock / partial / not stocked, plus lead time | Never promises a date the data doesn't support |
| 7 | **Price** (rules) | Competitive, explainable price | Spec, matched item, benchmarks, pricing rules | Price in the buyer's unit, components (base, processing, surcharge), minimum charges, benchmark comparison, margin, plain-language rationale, validity | Never below the margin floor without specialist approval; flags prices outside the benchmark range or based on stale benchmarks |
| 8 | **Compliance** | Required certifications and documents | RFQ-wide and line requirements, matched item attributes | Each requirement: met / not met / unknown, with evidence | "Unknown" is never shown as met |
| 9 | **Decide** | Assign status; draft questions | All issues on the line | Line status (Section 9); buyer question with options (AI words it); internal review note | AI words questions only; status comes from rules |
| 10 | **Verify** | Check the draft before a human sees it | Completed lines and draft documents | Per-line verification; leak check on buyer-facing output; borderline items sent to review queue | — |
| 11 | **Specialist review** (human) | Approve what goes out | Draft quote | Approved quote; edits and overrides recorded with reasons | Nothing is "ready to send" without approval |
| 12 | **Assemble** | Produce deliverables | Approved lines | Buyer-facing quote, buyer email with grouped questions, internal summary | Buyer-facing documents contain no internal data |
| 13 | **Buyer reply loop** (stretch) | Close the loop | Buyer's reply | Affected lines re-run; new quote revision | Unclear answers produce a follow-up question, not a guess |
| 14 | **Learn** (later) | Corrections stick | Specialist edits, buyer answers | New customer cross-references and aliases | Only confirmed answers are learned |

---

## 9. Statuses

### Line status

| Status | Meaning | Audience | What the quote shows |
|---|---|---|---|
| ✅ **Quoted** | Confident match, priced, no open issues | — | Price, spec, availability |
| ⚠️ **Quoted with assumptions** | Priced; relies on low-risk stated assumptions | Buyer sees assumptions | Price plus each assumption in plain language |
| 🔀 **Quoted with alternates** | Ambiguous, but a small set of reasonable options exists; each option priced | Buyer picks | Each alternate priced and labeled, plus one question |
| ❓ **Needs buyer input** | Can't be priced until the buyer answers; no reasonable options exist | Buyer | The question; no price |
| 👤 **Needs specialist review** | Internal concern: margin below floor, matching paths disagree, guardrail flag, unverifiable compliance on a critical requirement | Internal only | Held from the buyer quote until resolved |
| ⛔ **No bid** | Can't be supplied as requested | Buyer | The reason (and a suggested alternative if one exists) |
| ℹ️ **Not an item** | A note, requirement or service line (freight, cutting, certs) | — | Applied as a term or charge |

### Quote status
**Draft → In review → Approved → Sent (by a human) → Revised (after buyer reply).** An approved quote may be **complete** or **partial** (some lines awaiting buyer input). Partial quotes go out by default, because speed matters; the specialist can choose to hold.

---

## 10. Functional requirements

### 10.1 Triage and intake
| ID | Requirement | Pri | Acceptance |
|---|---|---|---|
| IN-1 | Accept RFQs as email text, PDF and spreadsheet | M (email, PDF), S (spreadsheet) | Each fixture yields the correct line count |
| IN-2 | Classify messages as new RFQ, revision, or not an RFQ | S | Non-RFQ fixture is not quoted |
| IN-3 | Ignore forwarded/quoted email history, signatures and disclaimers | M | Thread fixture yields only the newest request's lines |
| IN-4 | Separate RFQ-wide terms, line items, notes and attachment references | M | Header requirement applies to all lines |
| IN-5 | Preserve the buyer's line numbers and a pointer to each line's source location | M | Quote lines use buyer numbering |
| IN-6 | Detect references to missing attachments ("per drawing 1234") | M | Line asks the buyer for the drawing |
| IN-7 | Join descriptions that wrap across lines or pages; split one line that requests multiple items | S | — |

### 10.2 Safety and confidentiality
| ID | Requirement | Pri | Acceptance |
|---|---|---|---|
| SF-1 | Screen all incoming text for manipulation attempts using a PRISM guardrail | M | Seeded injection is caught |
| SF-2 | Withhold flagged passages; show them to the specialist | M | Injection has no effect on any price or status |
| SF-3 | Keep processing the rest of a flagged RFQ | M | Clean lines still quoted |
| SF-4 | Block internal data (cost, margin, supplier/mill names, internal notes) from all buyer-facing output | M | Leak check passes on every generated quote and email |
| SF-5 | Buyer questions contain no commitments not backed by the quote | M | — |

### 10.3 Interpret and standardize
| ID | Requirement | Pri | Acceptance |
|---|---|---|---|
| RD-1 | Interpret each line into material, grade, form, dimensions, quantity, unit, standard, finish/temper, tolerances, certifications | M | Field accuracy reported on test set |
| RD-2 | Record the exact source text for every interpreted value | M | Every field can show its source |
| RD-3 | Discard values whose cited source text isn't in the RFQ, and log it | M | Visible in run record |
| RD-4 | Leave unstated fields blank; never fill from general knowledge | M | Missing-grade line shows grade missing |
| RD-5 | Standardize units, fractions, gauges (by material), abbreviations, metric/imperial | M | Track's two example strings produce the same fingerprint |
| RD-6 | Log every inference as a visible assumption | M | Assumptions appear on the quote |
| RD-7 | Detect internal conflicts (e.g. thickness vs. gauge) | M | Conflict fixture routes correctly |
| RD-8 | Link duplicate lines written differently | S | Duplicate fixture linked |
| RD-9 | Handle "same as above" lines by inheriting from the previous line, logged | S | — |

### 10.4 Resolve to catalog
| ID | Requirement | Pri | Acceptance |
|---|---|---|---|
| MT-1 | Match each line to catalog items with a match strength, best match and alternates | M | Match accuracy reported |
| MT-2 | Run two independent matching paths; agreement = confident, disagreement = specialist review | S | Disagreement fixture goes to review |
| MT-3 | Resolve customer part numbers via a cross-reference table | M (lookup), L (learning) | Known part number resolves with "cross-reference" shown as source |
| MT-4 | Offer substitutions (dual-certified grades, near sizes, cut from larger stock) only as labeled alternates | M | — |
| MT-5 | No viable match → no bid with reason | M | Not-in-catalog fixture is no-bid |
| MT-6 | Ground matching claims in reference data loaded into the PRISM Knowledge Base | M | Claims checkable against the Knowledge Base |

### 10.5 Availability
| ID | Requirement | Pri | Acceptance |
|---|---|---|---|
| AV-1 | Show in stock / partial / not stocked per line | M | Shortage fixture shows partial |
| AV-2 | Show lead time for non-stock or shortfall quantity | S | — |
| AV-3 | Flag when the requested delivery date can't be met | S | — |

### 10.6 Pricing
| ID | Requirement | Pri | Acceptance |
|---|---|---|---|
| PR-1 | Compute price from weight/size, cost and pricing rules, in the buyer's unit of measure (each, per lb, per cwt, per foot) | M | Price shown in buyer's unit plus extended total |
| PR-2 | Enforce a margin floor; below-floor lines go to specialist review | M | Below-floor fixture goes to review |
| PR-3 | Compare each price to a benchmark range and show position, source and date | M | Visible per line |
| PR-4 | Plain-language price rationale built from the calculated numbers | M | Every number matches the calculation |
| PR-5 | Show stainless alloy surcharge as a separate, month-specific component | S | Surcharge line on stainless items |
| PR-6 | Apply processing charges (cutting) and minimum order charges, shown separately | S | — |
| PR-7 | Price buyer-requested quantity breaks | S | — |
| PR-8 | Show quote validity period (short, because of metal price volatility) | M | Validity date on quote |
| PR-9 | Show the customer's previous price for the same item when available | L | — |
| PR-10 | Flag prices above benchmark range or based on stale benchmarks | S | — |

### 10.7 Compliance
| ID | Requirement | Pri | Acceptance |
|---|---|---|---|
| CP-1 | Detect mill test report requirements (including "3.1 certs") | M | — |
| CP-2 | Detect domestic-sourcing requirements, and distinguish country of **melt** (e.g. DFARS specialty metals) from country of manufacture; ambiguous "domestic" → question | M | DFARS fixture flags a non-compliant item |
| CP-3 | Detect specification certification requirements (ASTM, ASME pressure-vessel grades, dual certification) | M | — |
| CP-4 | Detect industry-specific requirements (e.g. sour-service, positive material identification, RoHS/REACH) and mark unknown if data can't confirm | S | — |
| CP-5 | Apply RFQ-wide requirements to all lines; line-level requirements override | M | — |
| CP-6 | Mark each requirement met / not met / unknown, with evidence | M | — |

### 10.8 Decisions and buyer questions
| ID | Requirement | Pri | Acceptance |
|---|---|---|---|
| DC-1 | Assign each line exactly one status using documented rules | M | Rules listed in README |
| DC-2 | Separate buyer-facing issues from internal issues | M | Internal issues never appear in buyer email |
| DC-3 | Prefer priced alternates over open questions when reasonable options exist | M | 304/304L fixture yields alternates, not a stall |
| DC-4 | Draft one specific question per open item, with options; group all questions in one buyer email, blocking questions first | M | — |
| DC-5 | Process a buyer reply and re-quote affected lines as a new revision | S | — |

### 10.9 Verification and observability
| ID | Requirement | Pri | Acceptance |
|---|---|---|---|
| VR-1 | Re-check every number in each price rationale | M | — |
| VR-2 | Attach a PRISM Evaluator to at least one output (line status or price claim) | M | Verdict visible in PRISM |
| VR-3 | Send borderline evaluator results to PRISM's review queue | S | — |
| VR-4 | Record every stage of every RFQ as one PRISM run under a consistent agent name | M | Full run visible |

### 10.10 Review and output experience
| ID | Requirement | Pri | Acceptance |
|---|---|---|---|
| UX-1 | One review screen: all lines, status badges, summary counts by status | M | — |
| UX-2 | Expand any line to see source text, interpreted spec, assumptions, matched item and alternates, availability, price breakdown and benchmark, compliance, issues | M | — |
| UX-3 | Specialist can approve the quote | M | — |
| UX-4 | Specialist can edit a line (price, match, status), with the change and reason recorded | S | — |
| UX-5 | Buyer-facing quote: quote number and revision, buyer's line numbers, specs, unit of measure, prices, alternates, availability/lead time, assumptions, compliance notes, exceptions and no-bids, validity, terms | M | — |
| UX-6 | Buyer email with grouped questions | M | — |
| UX-7 | Printable/exportable quote | S | — |
| UX-8 | Link each RFQ to its PRISM run | S | — |

### 10.11 Quality measurement
| ID | Requirement | Pri | Acceptance |
|---|---|---|---|
| QA-1 | Labeled test set (~25 lines) covering the edge-case catalogue, with expected spec and status | M | — |
| QA-2 | Report field accuracy, routing accuracy, silent-error count and over-ask count (Section 13) | M | Shown in demo and Devpost |

---

## 11. Non-functional requirements

| ID | Requirement | Pri |
|---|---|---|
| NF-1 | **Traceability:** every value on the quote links to its source (RFQ text, catalog, cross-reference, benchmark, rule) | M |
| NF-2 | **Repeatability:** the same RFQ produces the same matches, prices and statuses; only AI wording may vary | M |
| NF-3 | **Speed:** a 20-line RFQ produces a draft in under 60 seconds | M |
| NF-4 | **Audit trail:** every specialist edit and approval is recorded with who, what and why | S |
| NF-5 | **Confidentiality:** internal fields are never in buyer-facing output; data from one customer never appears in another's quote | M |
| NF-6 | **Graceful degradation:** if the AI service fails on a line, that line becomes "needs specialist review"; the rest of the quote still completes | S |
| NF-7 | **Scale:** large RFQs (hundreds of lines) process progressively with partial results visible | L |
| NF-8 | **Usability:** a quoting specialist can review and approve without instructions | M |

---

## 12. Edge-case catalogue

Each case has an expected behavior. Cases marked M are covered by the hackathon test set.

### Document level
| # | Case | Example | Expected behavior | Pri |
|---|---|---|---|---|
| D1 | Email thread with prior messages | RFQ forwarded with an old quote below | Only the newest request is read | M |
| D2 | Signatures, disclaimers, phone numbers | "Cell 212-555-0148" | Not read as items or dimensions | M |
| D3 | Not an RFQ | Order-status question, invoice dispute | Labeled; no quote | S |
| D4 | Revised RFQ | "Rev 2: line 4 now 316" | Only changed lines re-quoted; new revision | L |
| D5 | Missing drawing | "Per dwg 4471 rev B" | Buyer asked for the drawing | M |
| D6 | Table split across PDF pages; wrapped descriptions | — | One line, not two | S |
| D7 | Requirements mixed into the item list | "All material DFARS compliant" between lines | Applied as RFQ-wide requirement, not an item | M |
| D8 | Response due date already passed | — | Shown to specialist | S |
| D9 | Multiple ship-to locations / split deliveries | — | Specialist review | L |
| D10 | Buyer's own line numbering | Lines 10, 20, 30 | Preserved on the quote | M |

### Line parsing
| # | Case | Example | Expected behavior | Pri |
|---|---|---|---|---|
| L1 | Same item, different wording | Track's two example strings | Identical fingerprint | M |
| L2 | Shorthand | SS, CRS, HRP&O, AL, ga, dia, sch | Expanded correctly | M |
| L3 | Typos / OCR confusions | "3O4", "6O61-T6" | Corrected only if unambiguous, logged as assumption; else question | S |
| L4 | "Same as above, but 316" | — | Inherits prior line, logged | S |
| L5 | Customer part number only | "ACME-PN 88213" | Cross-reference if known; else buyer question | M |
| L6 | Multiple items in one line | "304 & 316 sheet, 16ga, 4x8, 10 ea" | Split into linked lines | S |
| L7 | Buyer asks for alternates | "Quote 304 and 316", "or equal" | Both priced as labeled alternates | S |
| L8 | Quantity breaks | "Price @ 10 / 50 / 100" | Each tier priced | S |
| L9 | Service/charge lines | Freight, cutting, cert fee | Treated as charge/term, not catalog item | S |

### Units and dimensions
| # | Case | Example | Expected behavior | Pri |
|---|---|---|---|---|
| U1 | Fractions in all forms | 1-1/2, 1 1/2, 1.5", 1½ | Same value | M |
| U2 | Feet vs. inches | "4x8", "10'", "120 in" | Explicit units used; feet inferred only for standard sheet sizes, logged | M |
| U3 | Metric and decimal commas | "1,5 mm", "1219 x 2438" | Converted; unusual sizes flagged | S |
| U4 | Gauge depends on material; tube gauge differs from sheet gauge | "16ga" on stainless vs. aluminum | Material-specific conversion; gauge with unknown material → question | M |
| U5 | Pipe nominal size and schedule | "2 in sch 40" | Treated as pipe sizing, never as a literal 2.000" diameter | S |
| U6 | Dimension order unclear | "48 x .25 x 96" | Thickness = smallest for flat products; logged | M |
| U7 | Thickness conflicts with gauge | "16ga, 0.075 in" | Within tolerance → note; beyond → question | M |
| U8 | Tolerances | "+/- .005", "min wall" | Carried to quote; "unknown" if catalog can't confirm | S |
| U9 | Sheet vs. plate naming | "1/4 sheet" | Form inferred from thickness (boundary differs by material); noted, not an error | S |

### Material and specification
| # | Case | Example | Expected behavior | Pri |
|---|---|---|---|---|
| M1 | Grade missing | "stainless sheet 16ga 4x8" | Alternates (common grades) + question | M |
| M2 | Low-carbon variants | 304 vs. 304L | Dual-certified stock offered as alternate; confirm | M |
| M3 | Aluminum temper missing | "6061 plate 1/2" | Alternates by temper or question | S |
| M4 | Finish missing or unavailable | #4, 2B, mill, PVC-coated | Standard finish as stated assumption; question if finish-critical | S |
| M5 | Standard missing | — | Default standard for grade and form, as a stated assumption | M |
| M6 | Standard conflicts with form | Bar standard on a sheet line | Question | S |
| M7 | Pressure-vessel spec | "SA-240" vs. "A240" | Match only items certified to it; else flag | S |
| M8 | Carbon sheet condition | Hot rolled vs. cold rolled vs. pickled & oiled | Specified or question | S |

### Quantity and unit of measure
| # | Case | Example | Expected behavior | Pri |
|---|---|---|---|---|
| Q1 | Quantity missing | — | Buyer question | M |
| Q2 | Quantity by weight or length | "2,000 lbs", "20 cwt", "240 ft" | Converted; priced in buyer's unit | M |
| Q3 | "Lot" / "as required" | — | Buyer question | S |
| Q4 | Quantity exceeds stock | — | Partial availability + lead time | M |
| Q5 | Very small order | 1 piece | Minimum charge applied and shown | S |

### Commercial
| # | Case | Example | Expected behavior | Pri |
|---|---|---|---|---|
| C1 | Metal price volatility | — | Short validity; stainless surcharge shown separately and dated | S |
| C2 | Repeat customer with prior price | — | Prior price shown to specialist | L |
| C3 | Cut-to-size requested | "Cut to 12 x 24" | Processing charge or specialist review | S |
| C4 | Freight/delivery terms requested | "FOB destination" | Stated as a term; freight not priced but called out | S |
| C5 | Requested date can't be met | — | Flagged | S |
| C6 | Non-USD currency | — | Specialist review | L |

### Compliance
| # | Case | Example | Expected behavior | Pri |
|---|---|---|---|---|
| P1 | Mill test reports | "MTRs required", "3.1 certs" | Per-item check | M |
| P2 | "Domestic" is ambiguous | Melted vs. manufactured | Question which rule applies; DFARS = country of melt | M |
| P3 | Header requirement vs. line override | — | Line overrides header | M |
| P4 | Industry-specific requirements | Sour service, PMI, RoHS/REACH | Detected; "unknown" if unverifiable | S |
| P5 | Requirement can't be verified | No data on the item | "Unknown", never "met" | M |

### Matching
| # | Case | Expected behavior | Pri |
|---|---|---|---|
| X1 | Exact match | Quoted | M |
| X2 | Near size, or cut from larger stock | Labeled alternate or processing, never silent substitution | S |
| X3 | Two equally good matches | Alternates or specialist review | M |
| X4 | No match | No bid with reason | M |
| X5 | Item exists but out of stock, substitute in stock | Alternate | S |
| X6 | Matching paths disagree | Specialist review | S |

### Security and confidentiality
| # | Case | Expected behavior | Pri |
|---|---|---|---|
| S1 | Hidden/injected instructions in RFQ | Withheld, no effect | M |
| S2 | Internal data in buyer output | Blocked by leak check | M |
| S3 | AI-drafted question promises price or date | Blocked by verification | M |

### Buyer interaction
| # | Case | Expected behavior | Pri |
|---|---|---|---|
| B1 | Many small ambiguities | Resolved via alternates and stated assumptions; only blocking questions asked | M |
| B2 | Buyer answers some questions | Affected lines re-quoted; new revision | S |
| B3 | Buyer answer still ambiguous | Follow-up question, not a guess | L |

---

## 13. Success metrics

| Metric | Definition | Target (test set) |
|---|---|---|
| **Silent-error count** | Lines quoted (✅/⚠️) whose spec, match or price is wrong | **0** |
| **Routing accuracy** | Lines given the expected status | ≥ 85% |
| **Over-ask count** | Buyer questions where the test set says the answer was determinable | ≤ 2 |
| **Field accuracy** | Interpreted fields matching the labeled answer | ≥ 90% |
| **Touchless rate** | Lines needing no specialist edit | Reported |
| **Rationale consistency** | Price explanations whose numbers match the calculation | 100% |
| **Leak count** | Internal fields in buyer-facing output | 0 |
| **Manipulation effect** | Seeded injection changes any output | No |
| **Time to draft** | 20-line RFQ | < 60 s |

The first two pull in opposite directions on purpose. Asking about everything drives silent errors to zero but makes the tool useless. The product is judged on both together.

---

## 14. Release scope

| Phase | Includes |
|---|---|
| **Hackathon MVP (M)** | Email + PDF intake, thread/signature stripping, safety screen, interpret with source evidence, standardize, catalog + cross-reference matching, stock status, pricing with margin floor, benchmark and validity, compliance checks, all line statuses, alternates, grouped buyer questions, leak check, verification, PRISM tracing/guardrail/evaluator/Knowledge Base, review screen with approve, buyer-facing quote, test-set metrics |
| **Stretch today (S)** | Spreadsheet intake, dual-path matching agreement, alloy surcharge and processing charges, quantity breaks, lead times, line edits, buyer-reply loop, export, more edge cases |
| **Later (L)** | Learning cross-references from corrections, customer price history, revisions, multi-ship-to, large-RFQ streaming, ERP/live price integration, adjustable autonomy per customer |

**Cut order if behind:** spreadsheet intake → export → quantity breaks → surcharge/processing charges → dual-path matching (keep single path plus thresholds).
**Never cut:** source evidence, rules-based pricing, the line statuses (including alternates), buyer vs. internal separation, leak check, the three PRISM requirements, the test-set metrics.

---

## 15. Event and platform requirements

| ID | Requirement | Covered by |
|---|---|---|
| EV-1 | Built entirely during the event | — |
| EV-2 | Uses NicrronNinoo for AI model access | Stages 0, 3, 5 (path D), 9 |
| EV-3 | Uses Block Convey PRISM; one workspace per team, project named after the team, agent name on every recorded call | VR-4 |
| EV-4 | PRISM Guardrail on at least one input | SF-1 |
| EV-5 | PRISM Evaluator on at least one scored or classified output | VR-2 |
| EV-6 | At least one claim grounded through the PRISM Knowledge Base | MT-6 |
| EV-7 | Shows what it does when it isn't sure | Sections 6, 9; DC-1–DC-4 |
| EV-8 | A judge can check the output | NF-1, UX-2, PR-3, PR-4 |
| EV-9 | Devpost page: name and one-liner, track, what and why, accuracy and uncertainty handling, tools (NicrronNinoo and Block Convey), team and roles, video link, GitHub link | Submission checklist |

### Track traceability

| RudCo asks for... | Requirements |
|---|---|
| Handle messy emails, PDFs and spreadsheets | IN-1 to IN-7 |
| Recognize the same item written different ways | RD-5, RD-8, L1–L2 |
| Parse each line into a standard spec | RD-1 to RD-9 |
| Match each line to a supplier catalog | MT-1 to MT-6 |
| Price against benchmarks and explain why it's competitive | PR-1 to PR-10 |
| Flag compliance (MTRs, origin, spec certs) | CP-1 to CP-6 |
| Send ambiguous lines back with a question instead of guessing | DC-1 to DC-5, Section 9 |
| Ready-to-send quote | UX-3, UX-5, UX-6, SF-4 |

---

## 16. Demo data

All synthetic and labeled.

- **Catalog** (~60 items): stainless, carbon and aluminum in sheet, plate, bar, tube and pipe. Each has cost, stock quantity, lead time, country of melt, MTR availability, certifications (including dual-certified 304/304L and 316/316L items).
- **Customer cross-reference table:** a few customer part numbers mapped to catalog items.
- **Benchmarks:** price ranges by material and form, with source label and date; a monthly stainless surcharge table.
- **Reference tables:** gauge by material, densities, abbreviations, default standards, substitution rules, pricing rules (margin floor, minimum charge, cutting charge, validity days).
- **Three RFQs:**
  - **Email (thread):** forwarded history and signature (D1, D2); track's two example strings (L1); missing grade (M1); "4x8" (U2); customer part number (L5); "DFARS" note in the list (D7, P2)
  - **PDF:** gauge/thickness conflict (U7); 304 vs. 304L (M2); quantity in lbs (Q2); quantity above stock (Q4); missing drawing (D5); not-in-catalog item (X4); hidden injection text (S1)
  - **Spreadsheet (stretch):** buyer line numbers (D10); quantity breaks (L8); missing quantity (Q1)
- **Test set:** ~25 labeled lines drawn from the above.

---

## 17. Demo script (~2 minutes)

1. Drop in the messy email thread. A draft appears in seconds; status counts at the top.
2. The two differently written lines became the same item.
3. Expand a quoted line: source text → spec → matched item → price breakdown vs. benchmark → compliance.
4. The missing-grade line: priced alternates, not a stall.
5. The buyer email: few, grouped, specific questions.
6. A "needs specialist review" line (below margin floor) that never reaches the buyer.
7. The withheld injection attempt.
8. PRISM: the run, guardrail catch, evaluator verdict.
9. Approve → buyer-facing quote (no internal data on it).
10. Close on the metrics: 0 silent errors, routing accuracy, over-ask count.

---

## 18. Assumptions and dependencies

- NicrronNinoo provides model access; PRISM provides tracing, guardrails, evaluators and Knowledge Base.
- All business data (catalog, stock, costs, benchmarks, surcharges, cross-references) is synthetic.
- Pricing rules (margin floor, minimum charge, validity) are illustrative defaults a business would configure.
- English-language RFQs, USD.

---

## 19. Risks and open questions

| # | Item | Plan |
|---|---|---|
| Q1 | Does PRISM's Knowledge Base support direct lookups, or only grounding checks after the fact? | Ask the PRISM team at setup |
| Q2 | PRISM blocks (vs. only flags) only on traffic through its proxy, which supports specific model providers. Can it screen NicrronNinoo traffic? | Ask at setup; fallback is screening via a supported provider plus our own check |
| Q3 | Evaluator runs cost limited PRISM credits | Run on demo sessions only |
| Q4 | How does RudCo actually price (per lb, cwt, piece)? Do they send partial quotes? Do buyers accept alternates? Typical validity window? | Ask RudCo on the floor early; adjust defaults |
| Q5 | Can we get a real anonymized RFQ from RudCo? | Ask early |
| R1 | Scope vs. ~4 hours | Phased scope and cut order (Section 14) |
| R2 | Synthetic data mistaken for real pricing | Labeled everywhere |
| R3 | Over-asking makes the product useless | Over-ask metric; alternates-first principle |

---

## 20. Out of scope

Sending messages, live market/ERP/inventory data, scanned or handwritten documents, CAD/drawing reading, freight pricing, order entry, invoicing, user accounts and permissions.

---

## 21. Glossary

| Term | Meaning |
|---|---|
| **RFQ** | Request for quote: a buyer's list of items and quantities needing prices |
| **Alternate** | A clearly labeled, separately priced option offered when the request is ambiguous or the exact item isn't available |
| **Cross-reference** | Mapping from a customer's part number to the supplier's own item |
| **MTR** | Mill test report: certifies chemistry and mechanical properties of a specific heat of metal (often "EN 10204 3.1") |
| **Alloy surcharge** | A monthly, grade-specific price component for stainless that tracks alloy (nickel, chrome, moly) costs |
| **cwt** | Hundredweight (100 lb); a common pricing unit for steel |
| **Dual-certified** | Material certified to meet two grades or standards at once (e.g. 304/304L) |
| **Country of melt** | Where the metal was melted; the basis for some domestic-sourcing rules (e.g. DFARS specialty metals) |
| **Gauge** | A thickness designation whose actual value depends on the material |
| **Margin floor** | Minimum acceptable margin; below it, a person must approve |
| **Touchless rate** | Share of lines approved without any human edit |

---

## 22. References

- Get Hired Hack Devpost — https://get-hired-hack-nyc.devpost.com/ and /resources
- Block Convey PRISM docs — https://blockconvey.com/docs ; Evaluators — https://blockconvey.com/prism/evaluators
- Proton.ai, "RFQ Automation Software" (distributor workflow, matching, review dial, cross-referencing) — https://www.proton.ai/blog/rfq-automation-software
- Kodiak, metal service center RFQ problem statement — https://kodiakllc.notion.site/Take-Home-Screen-ec3477d8d6ec49dbbf123ebf407b4d36
- Outokumpu, stainless price structure and alloy surcharges — https://www.outokumpu.com/surcharges
- Cleveland-Cliffs stainless surcharge table (applied at time of shipment) — https://www.clevelandcliffs.com/
- Fastmarkets, stainless sheet assessed per cwt — https://fastmarkets.com/insights/stainless-surcharges-set-to-soar-in-april
