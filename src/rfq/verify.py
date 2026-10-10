"""Stage 10, verify: fixed checks on each line, and the leak check on the rendered buyer
documents (plans/12-decide-and-verify.md). No model calls.

A failed line check appends `verification_failed`, which sends the line to specialist review.
"""

import re
from collections.abc import Iterable, Iterator

from rfq.context import Context
from rfq.decide import REVIEW_KINDS, assign_status, decide
from rfq.models import (PRICED_STATUSES, LeakCheck, Line, Offer, Run, Spec, Verification,
                        buyer_view, issue)
from rfq.reference import ReferenceData, load_reference

# Spec field -> Reading fields that can source it, and issue fields that can name an assumption.
_READING = {
    "material": ("material", "grade"),  # the material follows from the grade
    "grade": ("grade",), "form": ("form",),
    "thickness_in": ("thickness", "gauge"), "width_in": ("width",), "length_in": ("length",),
    "diameter_in": ("diameter",), "wall_in": ("wall",),
    "quantity": ("quantity",), "quantity_unit": ("quantity",),
    "standard": ("standard",), "finish": ("finish", "material"),  # "CRS" names both
    "temper": ("temper",),
}
_DIMENSIONS = ("thickness_in", "width_in", "length_in", "diameter_in", "wall_in")
_ASSUMPTION_KINDS = ("assumption", "substitution")

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?|\.\d+")
_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_DATES = re.compile(rf"\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}/\d{{1,2}}/\d{{2,4}}"
                    rf"|\b{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?"
                    rf"|\b\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}(?:,?\s+\d{{4}})?", re.I)
_ALNUM_WORD = re.compile(r"\b(?=[A-Za-z0-9-]*[A-Za-z])(?=[A-Za-z0-9-]*\d)[A-Za-z0-9-]+\b")


# --- Line checks ------------------------------------------------------------------

def _has_source(line: Line, ctx: Context, name: str) -> bool:
    reading = line.reading
    if reading is None:
        return False
    if any(getattr(reading, f, None) for f in _READING[name]):
        return True
    if name in _DIMENSIONS and reading.unlabeled_dimensions:
        return True
    if reading.customer_part_no and any(o.candidate and o.candidate.via == "cross_reference"
                                        for o in line.offers):
        return True
    return False


def _has_assumption(line: Line, name: str) -> bool:
    names = {name, name.removesuffix("_in")}
    if name == "thickness_in":
        names.add("gauge")
    if name == "quantity_unit":
        names.add("quantity")
    return any(i.kind in _ASSUMPTION_KINDS and i.field in names for i in line.issues)


def _unsourced_fields(line: Line, ctx: Context) -> list[str]:
    spec: Spec | None = line.spec
    if spec is None:
        return []
    return [name for name in _READING
            if getattr(spec, name) not in (None, "")
            and not _has_source(line, ctx, name) and not _has_assumption(line, name)]


def _grade_names(line: Line, offer: Offer, ref: ReferenceData) -> list[str]:
    names = {g for g in (offer.spec.grade, line.spec and line.spec.grade) if g}
    names |= {f for g in list(names) if (f := ref.grade_family(g))}
    return sorted(names, key=len, reverse=True)


def _cited_numbers(text: str, grades: Iterable[str]) -> list[tuple[float, int]]:
    """(value, decimals) for each figure in a rationale, leaving out the digits of dates,
    grade names and alphanumeric designations (6061-T6, A240, 304L)."""
    text = _DATES.sub(" ", text)
    for g in grades:
        text = re.sub(rf"(?<![A-Za-z0-9]){re.escape(g)}[A-Za-z]*", " ", text, flags=re.I)
    text = _ALNUM_WORD.sub(" ", text)
    found = []
    for token in _NUMBER.findall(text):
        token = token.replace(",", "")
        found.append((float(token), len(token.split(".")[1]) if "." in token else 0))
    return found


def _rationale_failures(line: Line, ctx: Context) -> list[str]:
    failures = []
    for offer in line.offers:
        price = offer.price
        if price is None:
            continue
        known = [abs(v) for v in price.numbers.values()]
        for value, decimals in _cited_numbers(price.rationale, _grade_names(line, offer, ctx.ref)):
            tolerance = 0.5 * 10 ** -decimals + 1e-9  # the rationale may round a figure
            if not any(abs(k - value) <= tolerance for k in known):
                failures.append(f"Rationale for \"{offer.label}\" cites {value:g}, which is not "
                                f"in the price's numbers.")
    return failures


def _price_failures(line: Line) -> list[str]:
    if line.status not in PRICED_STATUSES and assign_status(line) not in PRICED_STATUSES:
        return []
    failures = [f"Offer \"{o.label}\" has a price but no matched catalog item."
                for o in line.offers if o.price and o.candidate is None]
    internal = sorted({i.kind for i in line.issues if i.kind in REVIEW_KINDS})
    if internal:
        failures.append("Priced line carries internal issues: " + ", ".join(internal) + ".")
    return failures


def verify(line: Line, ctx: Context) -> Line:
    """Run the line checks. On failure, add `verification_failed` and re-run the status rules."""
    if line.segment.kind != "item":
        return line
    failures = [f"Spec field {name} has neither a source in the RFQ nor a named assumption."
                for name in _unsourced_fields(line, ctx)]
    failures += _rationale_failures(line, ctx)
    failures += _price_failures(line)
    line.verification = Verification(passed=not failures, failures=failures)
    if failures:
        message = "Verification failed: " + " ".join(failures)
        if not any(i.kind == "verification_failed" and i.message == message for i in line.issues):
            line.issues.append(issue("verification_failed", message))
        decide(line, ctx)
    return line


# --- Leak check -------------------------------------------------------------------

def _numeric_strings(strings: Iterable[str]) -> Iterator[float]:
    for s in strings:
        for token in _NUMBER.findall(s):
            if "." in token:
                yield float(token.replace(",", ""))


def _walk(node) -> Iterator:
    if isinstance(node, dict):
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)
    else:
        yield node


def _visible(run: Run) -> tuple[set[float], list[str]]:
    """Decimal figures and strings the buyer is allowed to see in this run."""
    leaves = list(_walk(buyer_view(run).model_dump()))
    strings = [x.lower() for x in leaves if isinstance(x, str)]
    numbers = {round(x, 2) for x in leaves if isinstance(x, float)}
    numbers |= {round(x, 2) for x in _numeric_strings(strings)}
    return numbers, strings


def _internal_numbers(run: Run, ref: ReferenceData) -> list[tuple[str, float]]:
    found = []
    for line in run.lines:
        hidden = line.status not in PRICED_STATUSES
        for offer in line.offers:
            where = f"line {line.buyer_line_no}"
            if offer.candidate and (item := ref.item(offer.candidate.sku)):
                found.append((f"catalog cost, {where}", item.cost_per_lb))
            if (price := offer.price) is None:
                continue
            found += [(f"cost, {where}", price.cost_per_lb), (f"margin, {where}", price.margin_pct),
                      (f"floor margin, {where}", price.floor_margin_pct)]
            if hidden:
                found += [(f"unit price of a line not shown to the buyer, {where}",
                           price.unit_price),
                          (f"extended price of a line not shown to the buyer, {where}",
                           price.extended)]
                found += [(f"price component of a line not shown to the buyer, {where}", c.amount)
                          for c in price.components]
    return found


def _internal_strings(run: Run, ref: ReferenceData) -> list[tuple[str, str]]:
    found = [(f"supplier name {name}", name) for name in {i.supplier for i in ref.catalog}]
    found += [("withheld text", w.text) for w in run.withheld]
    for line in run.lines:
        where = f"line {line.buyer_line_no}"
        if line.review_note:
            found.append((f"review note, {where}", line.review_note))
        found += [(f"internal issue ({i.kind}), {where}", i.message)
                  for i in line.issues if i.audience == "internal"]
        if line.status not in PRICED_STATUSES:
            found += [(f"price rationale of a line not shown to the buyer, {where}",
                       o.price.rationale) for o in line.offers if o.price]
            found += [(f"SKU of a line not shown to the buyer, {where}", o.candidate.sku)
                      for o in line.offers if o.candidate]
    return found


def _tokens(text: str) -> list[tuple[float, int, bool]]:
    """(value, decimals, marked) for each figure; marked means a $ before or a % after."""
    out = []
    for m in re.finditer(r"(\$\s*)?(\d[\d,]*(?:\.\d+)?|\.\d+)(\s*%)?", text):
        digits = m.group(2).replace(",", "")
        out.append((float(digits), len(digits.split(".")[1]) if "." in digits else 0,
                    bool(m.group(1) or m.group(3))))
    return out


def _matches(value: float, token: tuple[float, int, bool]) -> bool:
    shown, decimals, marked = token
    if decimals >= 2:
        return round(value, decimals) == round(shown, decimals)
    if decimals == 1:
        return abs(value - shown) < 1e-9  # "2.7" is not a rounded 2.71, but "5.3" is a 5.3
    return marked and value == int(value) and value == shown


def leak_check(run: Run, buyer_texts: list[str], ref: ReferenceData | None = None) -> LeakCheck:
    """Search the rendered buyer documents for internal values of the run.

    Searched: cost, margin and floor figures (also the catalog cost of each matched item);
    for lines that are not priced in the buyer view, their prices, rationale and SKUs;
    supplier names; review notes; withheld text; messages of internal issues.

    Skipped, to avoid false alarms: an internal figure that equals (to 2 decimals) a figure
    the buyer is allowed to see in the same run, and an internal string that also appears
    in buyer-visible text. Whole numbers match only with a "$" before or a "%" after, and
    only when the internal value is itself whole (a floor of 12 matches "12%", not "12").
    One-decimal figures must equal the internal value exactly; two or more decimals may be a
    rounding of it (1.7234 matches "1.72").
    """
    ref = ref or load_reference()
    visible_numbers, visible_strings = _visible(run)
    docs = [" ".join(t.split()) for t in buyer_texts]
    lowered = [d.lower() for d in docs]
    hits: list[str] = []

    for label, value in dict.fromkeys(_internal_numbers(run, ref)):
        if round(value, 2) in visible_numbers:
            continue
        for n, doc in enumerate(docs):
            if any(_matches(value, t) for t in _tokens(doc)):
                hits.append(f"{label}: {value:g} appears in document {n}")
                break

    for label, text in dict.fromkeys(_internal_strings(run, ref)):
        needle = " ".join(text.split()).lower()
        if len(needle) < 4 or any(needle in s for s in visible_strings):
            continue
        for n, doc in enumerate(lowered):
            if needle in doc:
                hits.append(f"{label} appears in document {n}")
                break
    return LeakCheck(passed=not hits, hits=hits)
