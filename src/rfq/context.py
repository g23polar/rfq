"""What every stage receives besides the line, and the conventions stages share.

Stage contract (see also models.py): `stage(line: Line, ctx: Context) -> Line`. A stage
fills its own fields and appends issues; it never removes what an earlier stage wrote.
A stage returns the line untouched when it has nothing to work on (a segment that is not
an item, or a missing input from an earlier stage).

Stage order and entry points:

    standardize.standardize  reading -> line.spec, issues                    (task 08)
    match.resolve            spec -> line.offers (label, spec, candidate)    (task 09)
    jury.cross_check         second_reading -> line.jury, paths_disagree     (model jury)
    availability.check       offers -> offer.availability                    (task 19)
    price.price              offers -> offer.price                           (task 10)
    compliance.check         offers -> offer.compliance                      (task 11)
    decide.decide            issues -> status, question, review_note         (task 12)
    verify.verify            line -> verification (may send it to review)    (task 12)

Conventions between stages:

- Issues are built with `models.issue(kind, message, field, options)`; the audience comes
  from the kind. Messages are written for the audience that will read them.
- `ambiguous_options` and `tie` issues carry their choices in `Issue.options`. For a missing
  or unclear grade, `field="grade"` and the options are grade families ("304", "316").
- `Offer.spec` is a complete Spec for that offer: the line's spec with the option's own
  values filled in. Pricing and availability read `offer.spec`, never `line.spec`.
- The catalog item behind an offer is `ctx.ref.item(offer.candidate.sku)`.
- Tube and pipe wall thickness is `Spec.wall_in`; `Spec.thickness_in` is for flat product.
- `Spec.quantity` is in `Spec.quantity_unit`, the buyer's own unit (ea, lb, cwt or ft).
- Requirements come from two places: `ctx.terms.requirements` (RFQ-wide) and
  `line.reading.requirements` (line-level, which wins on the same subject).
- An issue that concerns only some offers is not raised at line level unless it applies to
  every offer: `unmet_requirement` means no offer on the line is compliant.
- Cost, margin, supplier and review notes are internal. Never put them in an issue whose
  audience is the buyer, in `Offer.label`, or in `Price.rationale`.
"""

from dataclasses import dataclass
from datetime import date

from rfq.models import Terms
from rfq.reference import ReferenceData


@dataclass(frozen=True)
class Context:
    terms: Terms
    ref: ReferenceData
    today: date

    @property
    def customer(self) -> str | None:
        return str(self.terms.customer.value) if self.terms.customer else None
