"""Model jury: compare two independent readings of a line (runs after `match.resolve`).

The first reading comes from MODEL_READ, the second from the model named by RFQ_JURY_MODEL
(interpret.py). Both have already passed the source-text check. Here the second reading is
standardized by exactly the same rules as the first, and the two standard specs are compared
on the fields that decide which item is matched and what it costs.

- They agree: `line.jury.agreed` is True and every candidate is marked `paths_agree=True`.
- They differ: `line.jury` names each difference, and a `paths_disagree` issue (internal)
  holds the line for the specialist. A model's word is never taken over the other's.

No second reading (jury off, or the second model failed): the line is left untouched.

Comparing standard specs rather than raw readings means harmless differences in how a model
wrote things down ("16" with unit "ga" vs "16ga") cancel out; only differences that would
change the quote remain.
"""

from rfq import standardize
from rfq.context import Context
from rfq.llm import MODEL_READ, jury_model
from rfq.models import JuryResult, Line, Spec, issue

# Spec fields that change the matched item, the quantity or the price.
COMPARED = ("material", "grade", "form", "thickness_in", "width_in", "length_in",
            "diameter_in", "wall_in", "quantity", "quantity_unit")
LABEL = {"thickness_in": "thickness", "width_in": "width", "length_in": "length",
         "diameter_in": "diameter", "wall_in": "wall", "quantity_unit": "quantity unit"}
REL_TOL = 0.001


def _short(model: str | None) -> str:
    return (model or "second model").split("/")[-1]


def _show(value) -> str:
    if value is None:
        return "not stated"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _same(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= REL_TOL * max(abs(a), abs(b), 1e-9)
    return a == b


def _part_no(line: Line) -> str | None:
    r = line.reading
    if r is None or r.customer_part_no is None:
        return None
    return "".join(str(r.customer_part_no.value).split()).upper()


def _differences(first: Spec, second: Spec, first_part: str | None,
                 second_part: str | None) -> list[str]:
    diffs = []
    for name in COMPARED:
        a, b = getattr(first, name), getattr(second, name)
        if not _same(a, b):
            diffs.append(f"{LABEL.get(name, name)}: {_show(a)} / {_show(b)}")
    if first_part != second_part:
        diffs.append(f"customer part number: {_show(first_part)} / {_show(second_part)}")
    return diffs


def cross_check(line: Line, ctx: Context) -> Line:
    if (line.segment.kind != "item" or line.reading is None or line.second_reading is None
            or line.spec is None):
        return line
    other = Line(buyer_line_no=line.buyer_line_no, segment=line.segment,
                 reading=line.second_reading)
    other = standardize.standardize(other, ctx)
    if other.spec is None:
        return line
    second_part = (None if line.second_reading.customer_part_no is None else
                   "".join(str(line.second_reading.customer_part_no.value).split()).upper())
    diffs = _differences(line.spec, other.spec, _part_no(line), second_part)
    model = jury_model() or "second model"
    line.jury = JuryResult(model=model, agreed=not diffs, differences=diffs)
    for offer in line.offers:
        if offer.candidate is not None:
            offer.candidate.paths_agree = not diffs
    if diffs:
        line.issues.append(issue(
            "paths_disagree",
            f"Two independent readings disagree ({_short(MODEL_READ)} / {_short(model)}) on "
            + "; ".join(diffs) + ". Check the buyer's wording before quoting."))
    return line
