"""Shared data shapes for the RFQ-to-Quote pipeline (plans/01-contracts-and-skeleton.md).

Stage contract: every stage is a function

    stage(line: Line, context) -> Line

where `context` carries the RFQ terms, the customer, and the catalog, stock,
cross-reference, benchmark and rule tables. A stage only adds to the line: it fills
its own fields and appends issues, and never removes what an earlier stage wrote.
Line status is decided from the issue list alone (plans/12-decide-and-verify.md).

Buyer-facing output is built only through `buyer_view`, which returns shapes that
have no internal fields at all.
"""

from typing import Literal

from pydantic import BaseModel, Field

Source = Literal["rfq_line", "rfq_terms", "catalog", "cross_reference", "benchmark", "rule",
                 "specialist"]
SegmentKind = Literal["item", "requirement", "note", "service"]
Audience = Literal["buyer", "internal"]
LineStatus = Literal["quoted", "quoted_with_assumptions", "quoted_with_alternates",
                     "needs_buyer_input", "needs_specialist_review", "no_bid", "not_an_item"]
QuoteStatus = Literal["draft", "in_review", "approved", "sent", "revised"]
PriceUnit = Literal["ea", "lb", "cwt", "ft"]
IssueKind = Literal[
    "missing", "conflict", "missing_attachment", "ambiguous_options", "tie", "substitution",
    "open_question", "assumption", "no_match", "unmet_requirement",
    "below_floor", "weak_match", "paths_disagree", "withheld_text", "unconfirmed",
    "verification_failed", "model_failed", "price_out_of_range", "stale_benchmark",
]

# Who an issue is for. Internal issues never reach buyer-facing output.
ISSUE_AUDIENCE: dict[str, Audience] = {
    "missing": "buyer", "conflict": "buyer", "missing_attachment": "buyer",
    "ambiguous_options": "buyer", "tie": "buyer", "substitution": "buyer",
    "open_question": "buyer", "assumption": "buyer", "no_match": "buyer",
    "unmet_requirement": "buyer",
    "below_floor": "internal", "weak_match": "internal", "paths_disagree": "internal",
    "withheld_text": "internal", "unconfirmed": "internal", "verification_failed": "internal",
    "model_failed": "internal", "price_out_of_range": "internal", "stale_benchmark": "internal",
}

# Statuses whose prices may be shown to the buyer.
PRICED_STATUSES = ("quoted", "quoted_with_assumptions", "quoted_with_alternates")


class Location(BaseModel):
    page: int | None = None
    row: int | None = None
    start: int | None = None  # character range in the cleaned document text
    end: int | None = None


class Sourced(BaseModel):
    """A value plus the evidence for it. `value` is as written; `unit` is kept separate."""

    value: str | float
    unit: str | None = None
    source_text: str | None = None  # exact RFQ text; None when the source is not the RFQ
    source: Source = "rfq_line"


class Segment(BaseModel):
    buyer_line_no: str
    text: str
    location: Location = Field(default_factory=Location)
    kind: SegmentKind = "item"


class Terms(BaseModel):
    customer: Sourced | None = None
    due_date: Sourced | None = None
    delivery: Sourced | None = None
    requirements: list[Sourced] = Field(default_factory=list)
    commercial_requests: list[Sourced] = Field(default_factory=list)
    attachment_refs: list[Sourced] = Field(default_factory=list)


class Withheld(BaseModel):
    text: str
    location: Location = Field(default_factory=Location)
    reason: str
    detector: Literal["pattern", "model"]


class Discarded(BaseModel):
    field: str
    value: str
    source_text: str | None = None
    reason: str


class Reading(BaseModel):
    """Stage 3 output: what the RFQ says, as written. Nothing converted, nothing inferred."""

    material: Sourced | None = None
    grade: Sourced | None = None
    form: Sourced | None = None
    thickness: Sourced | None = None
    gauge: Sourced | None = None  # kept apart from thickness so a conflict can be detected
    width: Sourced | None = None
    length: Sourced | None = None
    diameter: Sourced | None = None
    wall: Sourced | None = None  # tube and pipe wall thickness
    unlabeled_dimensions: list[Sourced] = Field(default_factory=list)  # "48 x .25 x 96"
    quantity: Sourced | None = None
    standard: Sourced | None = None
    finish: Sourced | None = None
    temper: Sourced | None = None
    tolerance: Sourced | None = None
    customer_part_no: Sourced | None = None
    drawing_ref: Sourced | None = None
    requirements: list[Sourced] = Field(default_factory=list)
    discarded: list[Discarded] = Field(default_factory=list)


class Issue(BaseModel):
    kind: IssueKind
    audience: Audience
    message: str
    field: str | None = None
    options: list[str] = Field(default_factory=list)  # the choices, for ambiguous_options and tie


def issue(kind: IssueKind, message: str, field: str | None = None,
          options: list[str] | None = None) -> Issue:
    """Build an issue with the audience its kind always has."""
    return Issue(kind=kind, audience=ISSUE_AUDIENCE[kind], message=message, field=field,
                 options=options or [])


class Spec(BaseModel):
    """Stage 4 output: one canonical form, dimensions in inches."""

    material: str | None = None
    grade: str | None = None
    form: str | None = None
    thickness_in: float | None = None
    width_in: float | None = None
    length_in: float | None = None
    diameter_in: float | None = None
    wall_in: float | None = None  # tube and pipe
    quantity: float | None = None
    quantity_unit: PriceUnit | None = None
    standard: str | None = None
    finish: str | None = None
    temper: str | None = None
    fingerprint: str | None = None


class Candidate(BaseModel):
    sku: str
    description: str
    strength: float
    differences: list[str] = Field(default_factory=list)
    via: Literal["spec", "cross_reference"] = "spec"
    paths_agree: bool | None = None  # None until the second matching path has run


class Availability(BaseModel):
    status: Literal["in_stock", "partial", "not_stocked"]
    available_qty: float = 0
    shortfall_qty: float = 0
    lead_time_days: int | None = None


class Benchmark(BaseModel):
    low: float
    mid: float
    high: float
    source: str
    as_of: str


class PriceComponent(BaseModel):
    name: str  # "base", "surcharge", "processing", "minimum"
    amount: float


class Price(BaseModel):
    unit: PriceUnit
    unit_price: float
    extended: float
    components: list[PriceComponent] = Field(default_factory=list)
    weight_lb: float
    benchmark: Benchmark | None = None
    position: Literal["below_mid", "within_range", "above_range"] | None = None
    rationale: str = ""
    numbers: dict[str, float] = Field(default_factory=dict)  # every figure the rationale cites
    valid_until: str
    # Internal: never in buyer-facing output.
    cost_per_lb: float
    margin_pct: float
    floor_margin_pct: float


class RequirementResult(BaseModel):
    requirement: str
    scope: Literal["rfq", "line"]
    source_text: str | None = None
    result: Literal["met", "not_met", "unknown"]
    evidence: str


class Offer(BaseModel):
    """One priced way to fill a line. Alternates are simply several offers on one line."""

    label: str
    spec: Spec
    candidate: Candidate | None = None
    availability: Availability | None = None
    price: Price | None = None
    compliance: list[RequirementResult] = Field(default_factory=list)


class Question(BaseModel):
    text: str
    options: list[str] = Field(default_factory=list)
    blocking: bool = True  # False when the line is already priced


class Verification(BaseModel):
    passed: bool
    failures: list[str] = Field(default_factory=list)


class Edit(BaseModel):
    field: str
    old: str | None = None
    new: str
    reason: str
    by: str
    at: str


class Line(BaseModel):
    buyer_line_no: str
    segment: Segment
    reading: Reading | None = None
    spec: Spec | None = None
    issues: list[Issue] = Field(default_factory=list)
    offers: list[Offer] = Field(default_factory=list)
    status: LineStatus | None = None  # set by the decide stage
    question: Question | None = None
    review_note: str | None = None  # internal
    duplicate_of: list[str] = Field(default_factory=list)
    verification: Verification | None = None
    edits: list[Edit] = Field(default_factory=list)


class RunSource(BaseModel):
    filename: str | None = None
    kind: Literal["email", "pdf", "spreadsheet", "text"]


class LeakCheck(BaseModel):
    passed: bool
    hits: list[str] = Field(default_factory=list)


class Run(BaseModel):
    rfq_id: str
    revision: int = 1
    created: str
    source: RunSource
    terms: Terms = Field(default_factory=Terms)
    withheld: list[Withheld] = Field(default_factory=list)
    lines: list[Line] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    total: float = 0.0
    quote_status: QuoteStatus = "draft"
    completeness: Literal["complete", "partial"] | None = None
    approved_by: str | None = None
    email: str | None = None
    leak_check: LeakCheck | None = None
    prism_trace_id: str | None = None


# --- Buyer view -------------------------------------------------------------------
# Separate shapes, so internal fields cannot leak by omission: they have nowhere to go.

class BuyerPrice(BaseModel):
    unit: PriceUnit
    unit_price: float
    extended: float
    components: list[PriceComponent]
    benchmark: Benchmark | None
    position: str | None
    rationale: str
    valid_until: str


class BuyerOffer(BaseModel):
    label: str
    sku: str | None
    description: str | None
    availability: Availability | None
    price: BuyerPrice | None
    compliance: list[RequirementResult]


class BuyerLine(BaseModel):
    buyer_line_no: str
    text: str
    status: LineStatus
    offers: list[BuyerOffer] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    question: Question | None = None
    reason: str | None = None  # why a line is no bid


class BuyerQuote(BaseModel):
    rfq_id: str
    revision: int
    quote_status: QuoteStatus
    completeness: Literal["complete", "partial"] | None
    customer: str | None
    terms: list[str]
    lines: list[BuyerLine]
    total: float  # single-offer priced lines only; alternates are not summed
    email: str | None


def _buyer_offer(offer: Offer) -> BuyerOffer:
    price = offer.price
    return BuyerOffer(
        label=offer.label,
        sku=offer.candidate.sku if offer.candidate else None,
        description=offer.candidate.description if offer.candidate else None,
        availability=offer.availability,
        price=price and BuyerPrice(
            unit=price.unit, unit_price=price.unit_price, extended=price.extended,
            components=price.components, benchmark=price.benchmark, position=price.position,
            rationale=price.rationale, valid_until=price.valid_until),
        compliance=offer.compliance,
    )


def buyer_view(run: Run) -> BuyerQuote:
    """The buyer-facing form of a run. Lines in specialist review are left out entirely."""
    lines = []
    total = 0.0
    for line in run.lines:
        if line.status is None or line.status == "needs_specialist_review":
            continue
        buyer_issues = [i for i in line.issues if i.audience == "buyer"]
        priced = line.status in PRICED_STATUSES
        offers = [_buyer_offer(o) for o in line.offers] if priced else []
        if priced and len(offers) == 1 and offers[0].price:
            total += offers[0].price.extended
        lines.append(BuyerLine(
            buyer_line_no=line.buyer_line_no,
            text=line.segment.text,
            status=line.status,
            offers=offers,
            assumptions=[i.message for i in buyer_issues if i.kind == "assumption"],
            question=line.question,
            reason="; ".join(i.message for i in buyer_issues
                             if i.kind in ("no_match", "unmet_requirement"))
            if line.status == "no_bid" else None,
        ))
    return BuyerQuote(
        rfq_id=run.rfq_id,
        revision=run.revision,
        quote_status=run.quote_status,
        completeness=run.completeness,
        customer=str(run.terms.customer.value) if run.terms.customer else None,
        terms=[str(r.value) for r in run.terms.requirements],
        lines=lines,
        total=round(total, 2),
        email=run.email,
    )
