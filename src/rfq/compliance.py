"""Stage 8: compliance (plans/11-compliance.md).

For every offer with a candidate, says whether the catalog item meets each requirement on
the line, with buyer-safe evidence. Requirements are recognized from fixed wording patterns
(no model call); "unknown" is never reported as "met".
"""

import re
from dataclasses import dataclass

from rfq.context import Context
from rfq.models import Line, Offer, RequirementResult, Sourced, issue
from rfq.reference import CatalogItem

# --- Wording patterns -------------------------------------------------------------------

_MTR = re.compile(
    r"\bc?mtrs?\b|\bmill\s+(?:test\s+)?(?:reports?|certs?|certificates?)\b"
    r"|\b(?:material|test)\s+(?:test\s+)?(?:reports?|certs?|certificates?)\b"
    r"|\b3\.1\s*(?:certs?|certificates?|certification)\b|\ben\s*10204\b", re.I)
_DFARS = re.compile(r"\bdfars?\b|\b252\.225\b|\bspecialty\s+metals?\b", re.I)
_MELT = re.compile(r"\bmelt(?:ed|s|ing)?\b", re.I)
_MANUFACTURE = re.compile(r"\b(?:manufactur\w*|made|produced|fabricat\w*)\b", re.I)
_DOMESTIC = re.compile(
    r"(?i:\bdomestic(?:ally)?\b|\busa\b|\bu\.s\.(?:a\.)?|united\s+states|\bamerican?\b"
    r"|\bno\s+(?:imports?|foreign|offshore)\b)|\bUS\b")
_ORIGIN_WORDS = re.compile(r"\b(?:imports?|imported|foreign|offshore|non[- ]?domestic|origin)\b", re.I)
_SPEC_CODE = re.compile(
    r"\bAMS[-\s]?(?:QQ[-\s]?A[-\s]?)?\d+(?:/\d+)?"
    r"|(?:(?:ASTM|ASME)[-\s]*(?:SA|A|B)[-\s]?|(?<![\w])(?:SA|A|B)-?)\d{2,4}\b", re.I)
_DUAL = re.compile(r"\bdual[-\s]?cert\w*", re.I)
_GRADE_PAIR = re.compile(r"\b(\d{3}[A-Z]?)\s*/\s*(\d{3}[A-Z]?)\b", re.I)
_OR = re.compile(r"\bor\b", re.I)
_WAIVER = re.compile(
    r"\b(?:not|no|without)\b[^.;]{0,25}\b(?:required|needed|necessary|req|applicable|apply|applies)\b"
    r"|\bnot\s+(?:a\s+)?requirement\b|\bwaive[ds]?\b|\bexempt\b|\bn/?a\b"
    r"|\b(?:imports?|foreign|offshore|non[- ]?domestic)\w*\s+(?:is\s+|are\s+)?"
    r"(?:ok|okay|acceptable|allowed|fine|accepted)\b"
    r"|\b(?:ok|okay|fine)\s+to\s+import\b", re.I)
_CLAUSES = re.compile(r";|\n|\bbut\b|\band\s+(?=no\b|not\b)|,\s*(?=no\b|not\b)", re.I)

SUBJECT_MTR, SUBJECT_ORIGIN, SUBJECT_SPEC, SUBJECT_DUAL = "mtr", "origin", "specification", "dual"
CRITICAL_KINDS = {"mtr", "dfars", "domestic_melt", "manufacture", "specification", "dual"}
_SUBJECT = {"mtr": SUBJECT_MTR, "dfars": SUBJECT_ORIGIN, "domestic_melt": SUBJECT_ORIGIN,
            "domestic": SUBJECT_ORIGIN, "manufacture": SUBJECT_ORIGIN,
            "specification": SUBJECT_SPEC, "dual": SUBJECT_DUAL}


@dataclass(frozen=True)
class _Req:
    kind: str  # mtr, dfars, domestic_melt, domestic, manufacture, specification, dual, other, waived
    subject: str
    scope: str  # "rfq" or "line"
    source_text: str
    name: str
    codes: tuple[str, ...] = ()  # specification: canonical codes
    shown: tuple[str, ...] = ()  # specification: codes as written
    any_of: bool = False
    pair: tuple[str, str] = ()  # dual certification grades, when named


def _canon(code: str) -> str:
    return re.sub(r"^(?:ASTM|ASME)", "", re.sub(r"[^A-Z0-9/]", "", code.upper()))


def _codes(text: str) -> list[tuple[str, str]]:
    """(canonical, as written) for each specification code in the text."""
    return [(_canon(m.group(0)), re.sub(r"\s+", " ", m.group(0).strip().upper()))
            for m in _SPEC_CODE.finditer(text)]


def _clause_subjects(text: str) -> set[str]:
    subjects = set()
    if _MTR.search(text):
        subjects.add(SUBJECT_MTR)
    if _DFARS.search(text) or _DOMESTIC.search(text) or _ORIGIN_WORDS.search(text):
        subjects.add(SUBJECT_ORIGIN)
    if _SPEC_CODE.search(text):
        subjects.add(SUBJECT_SPEC)
    if _DUAL.search(text):
        subjects.add(SUBJECT_DUAL)
    return subjects


def _classify_clause(text: str) -> list[tuple]:
    """(kind, extra) for each recognized requirement in one clause."""
    if _WAIVER.search(text):
        subjects = _clause_subjects(text)
        if subjects:
            return [("waived", s) for s in sorted(subjects)]
    found: list[tuple] = []
    if _MTR.search(text):
        found.append(("mtr", None))
    dfars = bool(_DFARS.search(text))
    if dfars:
        found.append(("dfars", None))
    if _DOMESTIC.search(text):
        if _MELT.search(text):
            found.append(("domestic_melt", None))
        elif _MANUFACTURE.search(text):
            found.append(("manufacture", None))
        elif not dfars:
            found.append(("domestic", None))
    codes = _codes(text)
    if codes:
        found.append(("specification", (codes, bool(_OR.search(text)))))
    if _DUAL.search(text):
        pair = _GRADE_PAIR.search(text)
        found.append(("dual", (pair.group(1).upper(), pair.group(2).upper()) if pair else ()))
    return found


def _classify(req: Sourced) -> list[tuple]:
    """Buyer's wording first; the earlier stage's label only when the wording says nothing."""
    for text in (req.source_text, str(req.value)):
        if not text:
            continue
        found: list[tuple] = []
        for clause in _CLAUSES.split(text):
            for entry in _classify_clause(clause):
                if entry not in found:
                    found.append(entry)
        if found:
            return found
    return []


def _name(kind: str, shown: tuple[str, ...], any_of: bool, pair: tuple, label: str) -> str:
    if kind == "mtr":
        return "Mill test report"
    if kind == "dfars":
        return "DFARS"
    if kind == "domestic_melt":
        return "Domestic melt"
    if kind == "manufacture":
        return "Domestic manufacture"
    if kind == "domestic":
        return "Domestic"
    if kind == "specification":
        return "Specification: " + (" or " if any_of else ", ").join(shown)
    if kind == "dual":
        return "Dual certification" + (f": {pair[0]}/{pair[1]}" if pair else "")
    return label


def _expand(req: Sourced, scope: str) -> list[_Req]:
    source = req.source_text or str(req.value)
    label = str(req.value)
    out = []
    for kind, extra in _classify(req):
        if kind == "waived":
            out.append(_Req("waived", extra, scope, source, label))
        elif kind == "specification":
            codes, any_of = extra
            canon = tuple(dict.fromkeys(c for c, _ in codes))
            shown = tuple(dict.fromkeys(s for _, s in codes))
            groups = [(canon, shown)] if any_of else [((c,), (s,)) for c, s in zip(canon, shown)]
            for cs, ss in groups:
                out.append(_Req(kind, SUBJECT_SPEC, scope, source,
                                _name(kind, ss, any_of, (), label), cs, ss, any_of))
        elif kind == "dual":
            out.append(_Req(kind, SUBJECT_DUAL, scope, source, _name(kind, (), False, extra, label),
                            pair=extra))
        else:
            out.append(_Req(kind, _SUBJECT[kind], scope, source, _name(kind, (), False, (), label)))
    if not out:
        out.append(_Req("other", f"other:{re.sub(r'[^a-z0-9]', '', label.lower())}", scope, source,
                        label))
    return out


def _requirements(rfq_wide: list[Sourced], line_level: list[Sourced]) -> list[_Req]:
    """Line-level requirements replace RFQ-wide ones on the same subject. Waivers (for
    example "import OK for this line") take part in the override but produce no result."""
    line_reqs = [r for q in line_level for r in _expand(q, "line")]
    overridden = {r.subject for r in line_reqs}
    rfq_reqs = [r for q in rfq_wide for r in _expand(q, "rfq") if r.subject not in overridden]
    merged: list[_Req] = []
    for r in [*rfq_reqs, *line_reqs]:
        if r.kind == "waived" or r in merged:
            continue
        merged.append(r)
    return merged


# --- Judging an item --------------------------------------------------------------------

def _country(item: CatalogItem) -> str | None:
    value = (item.country_of_melt or "").strip().upper()
    return value if len(value) == 2 and value.isalpha() else None


def _item_codes(item: CatalogItem) -> set[str]:
    text = "; ".join([item.standard or "", *item.certifications])
    return {c for c, _ in _codes(text)}


def _judge(req: _Req, item: CatalogItem | None, ctx: Context) -> tuple[RequirementResult, bool]:
    """The result, and whether "unknown" is because the item's data is missing."""
    result, evidence, missing = "unknown", "", False
    kind = req.kind
    if kind == "other":
        evidence = "This requirement cannot be checked against our catalog data."
    elif kind == "domestic":
        evidence = ("Cannot be judged: it is not stated whether domestic means melted "
                    "or manufactured in the USA.")
    elif item is None:
        evidence, missing = "This item could not be found in the catalog data.", True
    elif kind == "mtr":
        if item.mtr_available == "yes":
            result, evidence = "met", "Mill test report available."
        elif item.mtr_available == "no":
            result, evidence = "not_met", "No mill test report is available for this item."
        else:
            evidence, missing = "Mill test report availability is not confirmed for this item.", True
    elif kind in ("dfars", "domestic_melt"):
        country = _country(item)
        qualifying = ctx.ref.rules.dfars.qualifying_countries
        if country is None:
            evidence, missing = "Country of melt is not confirmed for this item.", True
        elif kind == "dfars":
            ok = country in qualifying
            result = "met" if ok else "not_met"
            evidence = (f"Country of melt: {country}." if ok else
                        f"Country of melt: {country}, which is not a DFARS-qualifying country.")
        else:
            ok = country == "US"
            result = "met" if ok else "not_met"
            evidence = f"Country of melt: {country}." if ok else \
                f"Country of melt: {country}, not the US."
    elif kind == "manufacture":
        evidence, missing = "Country of manufacture is not recorded for this item.", True
    elif kind == "specification":
        have = _item_codes(item)
        if not have:
            evidence, missing = "The item's specifications are not recorded.", True
        else:
            hits = [s for c, s in zip(req.codes, req.shown) if c in have]
            ok = bool(hits) if req.any_of else len(hits) == len(req.codes)
            result = "met" if ok else "not_met"
            listed = item.standard or "; ".join(item.certifications)
            evidence = (f"Item is certified to {', '.join(hits)}." if ok else
                        f"Item is certified to {listed}, not {', '.join(req.shown)}.")
    elif kind == "dual":
        grade = item.grade.upper()
        named = all(re.sub(r"[^A-Z0-9]", "", g) in re.sub(r"[^A-Z0-9/]", "", grade).split("/")
                    for g in req.pair) if req.pair else True
        ok = item.dual_certified and named
        result = "met" if ok else "not_met"
        evidence = (f"Dual-certified {item.grade}." if ok else
                    f"Item is certified as {item.grade}, not dual-certified"
                    + (f" {req.pair[0]}/{req.pair[1]}." if req.pair else "."))
    return (RequirementResult(requirement=req.name, scope=req.scope, source_text=req.source_text,
                              result=result, evidence=evidence),  # type: ignore[arg-type]
            missing)


# --- Entry point ------------------------------------------------------------------------

def _add(line: Line, new) -> None:
    if not any(i.kind == new.kind and i.message == new.message for i in line.issues):
        line.issues.append(new)


def check(line: Line, ctx: Context) -> Line:
    offers: list[Offer] = [o for o in line.offers if o.candidate]
    if not offers:
        return line
    reqs = _requirements(ctx.terms.requirements,
                         line.reading.requirements if line.reading else [])
    for offer in offers:
        offer.compliance = []
    if not reqs:
        return line

    for req in reqs:
        if req.kind == "domestic":
            _add(line, issue(
                "open_question",
                f'Your request says "{req.source_text}". Does domestic mean melted in the USA '
                "or manufactured in the USA?", field="requirement",
                options=["Melted in the USA", "Manufactured in the USA"]))

    failures: dict[tuple[str, str], str] = {}
    all_failed = True
    for offer in offers:
        failed = False
        for req in reqs:
            item = ctx.ref.item(offer.candidate.sku)  # type: ignore[union-attr]
            res, missing = _judge(req, item, ctx)
            offer.compliance.append(res)
            if res.result == "not_met":
                failed = True
                failures.setdefault((res.requirement, req.source_text), res.evidence)
            if missing and req.kind in CRITICAL_KINDS:
                _add(line, issue(
                    "unconfirmed",
                    f"Cannot confirm {res.requirement} for {offer.candidate.sku}: "  # type: ignore[union-attr]
                    "catalog data is missing.", field="compliance"))
        all_failed = all_failed and failed

    if all_failed:
        for (name, source), evidence in failures.items():
            _add(line, issue("unmet_requirement",
                             f'Requirement not met ({name}, "{source}"): {evidence}',
                             field="requirement"))
    return line
