"""Stage 5: resolve a standardized line to catalog items (plans/09-match.md).

`resolve(line, ctx)` sets `line.offers` and appends issues. Strength starts at 1.0 for an
item and drops for each difference (see the PENALTY_* constants); differences are kept in
words on the Candidate. Requirement-based ranking (plan rule 3) is not done here: it needs
the compliance stage and is applied when the stages are wired together.
"""

import re
from dataclasses import dataclass, field

from rfq.context import Context
from rfq.models import Candidate, Issue, Line, Offer, Spec, issue
from rfq.reference import CatalogItem

TIE_WINDOW = 0.05
WEAK_BELOW = 0.8
STOCK_SIZE_TOL_IN = 0.25

PENALTY_INEXACT_DIM = 0.02  # within tolerance but not equal
PENALTY_GRADE_VARIANT = 0.15
PENALTY_STANDARD = 0.25
PENALTY_FINISH = 0.25
PENALTY_TEMPER = 0.15

# Issues on these fields do not stop a match.
_NOT_NEEDED = {"quantity", "quantity_unit", "standard", "finish", "temper", "tolerance",
               "drawing_ref", "customer_part_no"}

# (spec field, catalog field, kind): "section" uses the thickness tolerance table,
# "stock" the stock-size tolerance.
_DIMS: dict[str, list[tuple[str, str, str]]] = {
    "sheet": [("thickness_in", "thickness_in", "section"), ("width_in", "width_in", "stock"),
              ("length_in", "length_in", "stock")],
    "plate": [("thickness_in", "thickness_in", "section"), ("width_in", "width_in", "stock"),
              ("length_in", "length_in", "stock")],
    "round_bar": [("diameter_in", "diameter_in", "section"), ("length_in", "length_in", "stock")],
    "flat_bar": [("thickness_in", "thickness_in", "section"),
                 ("width_in", "width_in", "section"), ("length_in", "length_in", "stock")],
    "round_tube": [("diameter_in", "diameter_in", "section"), ("wall_in", "wall_in", "section"),
                   ("length_in", "length_in", "stock")],
    "square_tube": [("width_in", "width_in", "section"), ("wall_in", "wall_in", "section"),
                    ("length_in", "length_in", "stock")],
    "pipe": [("diameter_in", "diameter_in", "section"), ("wall_in", "wall_in", "section"),
             ("length_in", "length_in", "stock")],
}


def _norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _num(x: float) -> str:
    return f"{x:.4f}".rstrip("0").rstrip(".")


@dataclass
class _Hit:
    candidate: Candidate
    item: CatalogItem
    dual: bool = False  # dual-certified stock filling a single-grade request
    inexact: list[str] = field(default_factory=list)  # in-tolerance dimension notes


def resolve(line: Line, ctx: Context) -> Line:
    if line.segment.kind != "item" or line.spec is None:
        return line

    part_no = line.reading.customer_part_no if line.reading else None
    if part_no is not None:
        found = _cross_reference(line, ctx, str(part_no.value))
        if found:
            return line

    spec = line.spec
    options = _grade_options(line)
    wanted = _wanted_text(line, ctx)

    if part_no is not None and not _usable_description(spec, options, wanted):
        line.issues.append(issue(
            "missing",
            f"We could not find part number {part_no.value} in our records for your account. "
            "What is the part (material, grade, form and size)?",
            field="customer_part_no"))
        return line

    if _blocked(line) or spec.form is None or ctx.ref.form_family(spec.form) is None:
        return line

    if not options and spec.grade is None:
        if wanted and ctx.ref.grade_family(wanted) is None and not _is_material(wanted, ctx):
            line.issues.append(_no_match(line, wanted, None, ctx, unknown=True))
        return line
    if not options and ctx.ref.grade_family(spec.grade) is None:
        line.issues.append(_no_match(line, spec.grade, None, ctx, unknown=True))
        return line

    straight = _straight_only(line)
    grades = options or [spec.grade]
    plain = not options

    groups: list[tuple[str, list[_Hit]]] = []
    seen: set[str] = set()
    # A standard we assumed ourselves is not a request, so a different stocked standard is
    # not a mismatch; only a standard the buyer stated is held against the item.
    stated_standard = not any(i.kind == "assumption" and i.field == "standard"
                              for i in line.issues)
    for grade in grades:
        hits = _rank(spec, grade, straight, ctx, check_standard=stated_standard)
        best = _top(hits)
        best = [h for h in best if h.item.sku not in seen]
        seen.update(h.item.sku for h in best)
        if best:
            groups.append((grade, best))

    if not groups:
        _substitute(line, ctx, grades, straight)
        return line

    flat = [(g, h) for g, hs in groups for h in hs]
    labeled = len(flat) > 1
    index = 0
    for grade, hs in groups:
        words = _distinguish(hs) if len(hs) > 1 else []
        for n, hit in enumerate(hs):
            if labeled:
                what = hit.item.grade
                if words:
                    what = words[n] if hit.item.grade in words[n] else f"{what}, {words[n]}"
                label = f"Option {chr(ord('A') + index) if index < 26 else index + 1}: {what}"
            else:
                label = "As requested"
            line.offers.append(Offer(label=label, spec=_offer_spec(spec, grade, hit.item, ctx),
                                     candidate=hit.candidate))
            index += 1

    tie_groups = [hs for _, hs in groups if len(hs) > 1]
    if tie_groups:
        words = []
        for hs in tie_groups:
            words.extend(_distinguish(hs))
        line.issues.append(issue(
            "tie", "More than one item fits this line equally well. Which do you want?",
            options=words))

    _assumptions(line, flat, plain, grades, ctx)

    best_strength = max(h.candidate.strength for _, h in flat)
    if best_strength < WEAK_BELOW:
        line.issues.append(issue(
            "weak_match", f"Best match is {best_strength:.2f}: "
            + "; ".join(flat[0][1].candidate.differences or ["differences not listed"]),
            field="match"))
    return line


# --- cross-reference -------------------------------------------------------------------

def _cross_reference(line: Line, ctx: Context, part_no: str) -> bool:
    if not ctx.customer:
        return False
    ref = ctx.ref.lookup_part(ctx.customer, part_no)
    item = ctx.ref.item(ref.sku) if ref else None
    if item is None:
        return False
    spec = line.spec
    offer_spec = Spec(
        material=item.material, grade=item.grade, form=item.form, thickness_in=item.thickness_in,
        width_in=item.width_in, length_in=item.length_in, diameter_in=item.diameter_in,
        wall_in=item.wall_in, quantity=spec.quantity, quantity_unit=spec.quantity_unit,
        standard=item.standard, finish=item.finish)
    line.offers = [Offer(
        label="As requested", spec=offer_spec,
        candidate=Candidate(sku=item.sku, description=item.description, strength=1.0,
                            via="cross_reference"))]
    return True


def _usable_description(spec: Spec, options: list[str], wanted: str | None) -> bool:
    return spec.form is not None and bool(options or spec.grade or wanted)


# --- inputs from the earlier stage -----------------------------------------------------

def _grade_options(line: Line) -> list[str]:
    for i in line.issues:
        if i.kind == "ambiguous_options" and i.field == "grade" and i.options:
            return list(i.options)
    return []


def _blocked(line: Line) -> bool:
    return any(i.kind in ("missing", "conflict") and i.field not in _NOT_NEEDED
               for i in line.issues)


def _straight_only(line: Line) -> bool:
    texts = [line.spec.grade or ""]
    if line.reading:
        if line.reading.grade:
            texts += [str(line.reading.grade.value), line.reading.grade.source_text or ""]
        texts += [str(r.value) for r in line.reading.requirements]
    return any("straight" in t.lower() for t in texts)


def _is_material(text: str, ctx: Context) -> bool:
    low = text.lower()
    return any(m in low for m in (*ctx.ref.tables.materials, "steel"))


def _wanted_text(line: Line, ctx: Context) -> str | None:
    """Grade or material words from the buyer that standardize could not turn into a grade."""
    r = line.reading
    for src in (line.spec.grade, r.grade if r else None, r.material if r else None):
        if src is not None:
            return str(getattr(src, "value", src))
    material = line.spec.material
    return material if material and material not in ctx.ref.tables.materials else None


# --- ranking ---------------------------------------------------------------------------

def _grade_fit(item: CatalogItem, grade: str, straight: bool,
               ctx: Context) -> tuple[bool, list[str], float, bool]:
    """Returns (fits, differences, penalty, dual)."""
    ref = ctx.ref
    if ref.grade_family(item.grade) != ref.grade_family(grade):
        return False, [], 0.0, False
    if _norm(item.grade) == _norm(grade):
        return True, [], 0.0, False
    if item.dual_certified:
        rules = ref.tables.dual_certified.get(item.grade)
        fills = {_norm(g) for g in rules.fills} if rules else set()
        if straight or _norm(grade) not in fills:
            return False, [], 0.0, False
        return True, [f"{item.grade} dual-certified stock fills a {grade} request"], 0.0, True
    a, b = _norm(grade), _norm(item.grade)
    if a.startswith(b) or b.startswith(a):
        return True, [], 0.0, False
    return True, [f"grade {grade} requested, {item.grade} stocked"], PENALTY_GRADE_VARIANT, False


def _score(item: CatalogItem, spec: Spec, grade: str, straight: bool, ctx: Context,
           check_standard: bool = True) -> _Hit | None:
    ref = ctx.ref
    if ref.form_family(item.form) != ref.form_family(spec.form):
        return None
    if spec.form in ref.tables.forms and item.form != spec.form:
        return None
    if spec.material and item.material != spec.material:
        return None
    fits, diffs, penalty, dual = _grade_fit(item, grade, straight, ctx)
    if not fits:
        return None
    diffs = list(diffs)
    inexact: list[str] = []

    tol = ref.tables.thickness_tolerance
    for sfield, cfield, kind in _DIMS.get(item.form, []):
        want, have = getattr(spec, sfield), getattr(item, cfield)
        if want is None or have is None:
            continue
        allowed = max(tol.abs_in, tol.pct / 100 * want) if kind == "section" else STOCK_SIZE_TOL_IN
        gap = abs(want - have)
        if gap > allowed + 1e-9:
            return None
        if gap > 1e-9:
            note = f"{sfield[:-3].replace('_', ' ')} {_num(want)} in requested, {_num(have)} in stocked"
            diffs.append(note)
            inexact.append(note)
            penalty += PENALTY_INEXACT_DIM

    if check_standard and spec.standard:
        accepted = {_norm(item.standard), *(_norm(c) for c in item.certifications)}
        if _norm(spec.standard) not in accepted:
            diffs.append(f"standard {spec.standard} requested, {item.standard} stocked")
            penalty += PENALTY_STANDARD
    if spec.finish and item.finish and _finish_key(spec.finish, item) != _finish_key(item.finish, item):
        diffs.append(f"finish {spec.finish} requested, {item.finish} stocked")
        penalty += PENALTY_FINISH
    if spec.temper and _norm(spec.temper) not in _norm(item.grade):
        diffs.append(f"temper {spec.temper} requested, {item.grade} stocked")
        penalty += PENALTY_TEMPER

    cand = Candidate(sku=item.sku, description=item.description,
                     strength=round(max(0.0, 1.0 - penalty), 3), differences=diffs)
    return _Hit(candidate=cand, item=item, dual=dual, inexact=inexact)


def _rank(spec: Spec, grade: str, straight: bool, ctx: Context,
          check_standard: bool = True) -> list[_Hit]:
    hits = [h for i in ctx.ref.catalog
            if (h := _score(i, spec, grade, straight, ctx, check_standard))]
    return sorted(hits, key=lambda h: (-h.candidate.strength, h.item.sku))


def _top(hits: list[_Hit]) -> list[_Hit]:
    if not hits:
        return []
    best = hits[0].candidate.strength
    return [h for h in hits if best - h.candidate.strength <= TIE_WINDOW + 1e-9]


# --- offers ----------------------------------------------------------------------------

def _offer_spec(spec: Spec, grade: str, item: CatalogItem, ctx: Context) -> Spec:
    return spec.model_copy(update={
        "grade": grade,
        "material": spec.material or item.material,
        "standard": spec.standard or ctx.ref.default_standard(grade, item.form),
    })


def _distinguish(hits: list[_Hit]) -> list[str]:
    """Buyer-readable words that tell tied items apart."""
    items = [h.item for h in hits]
    words = [[] for _ in items]
    for attr, fmt in (("grade", "{}"), ("finish", "{} finish"), ("standard", "{}")):
        values = [getattr(i, attr) for i in items]
        if len(set(values)) > 1:
            for w, v in zip(words, values):
                if v:
                    w.append(fmt.format(v))
    return [", ".join(w) or i.description for w, i in zip(words, items)]


def _assumptions(line: Line, flat: list[tuple[str, _Hit]], plain: bool, grades: list[str],
                 ctx: Context) -> None:
    hits = [h for _, h in flat]
    if plain and all(h.dual for h in hits):
        h = hits[0]
        line.issues.append(issue(
            "assumption",
            f"{grades[0]} requested; quoting {h.item.grade} dual-certified stock, which meets "
            f"both {h.item.grade.replace('/', ' and ')}.", field="grade"))
    if all(h.inexact for h in hits):
        line.issues.append(issue(
            "assumption",
            "Size matched within standard tolerance: " + "; ".join(hits[0].inexact) + ".",
            field="size"))


# --- nothing fits ----------------------------------------------------------------------

_COLD_BAR_FINISHES = {"COLDROLLED", "COLDDRAWN", "COLDFINISHED"}


def _finish_key(finish: str, item) -> str:
    """Buyers write "CRS" for any cold-finished bar; on bar those finishes are one product."""
    key = _norm(finish)
    return "COLDFINISHED" if item.form.endswith("_bar") and key in _COLD_BAR_FINISHES else key


def _substitute(line: Line, ctx: Context, grades: list[str], straight: bool) -> None:
    spec = line.spec
    families = {f for g in grades if (f := ctx.ref.grade_family(g))}
    # A grade dual-certified stock cannot fill (304H, straight 304) was asked for on purpose;
    # a different low-carbon grade is not a substitute for it.
    excluded = {_norm(x) for d in ctx.ref.tables.dual_certified.values() for x in d.does_not_fill}
    deliberate = straight or any(_norm(g) in excluded for g in grades)
    for sub in ([] if deliberate else ctx.ref.tables.substitutions):
        if sub.from_ not in families:
            continue
        hits = _top(_rank(spec, sub.to, False, ctx, check_standard=False))
        for hit in hits:
            sub_spec = spec.model_copy(update={
                "grade": sub.to, "material": spec.material or hit.item.material,
                "standard": ctx.ref.default_standard(sub.to, hit.item.form)})
            cand = hit.candidate.model_copy(update={
                "differences": [f"substitute for {sub.from_}", *hit.candidate.differences]})
            line.offers.append(Offer(label=f"Substitute: {hit.item.grade}", spec=sub_spec,
                                     candidate=cand))
        if hits:
            line.issues.append(issue(
                "substitution",
                f"We cannot supply {sub.from_} in this size. As a substitute we can offer "
                f"{hits[0].item.grade}. {sub.note} Please confirm before we quote it.",
                field="grade"))
    if not line.offers:
        line.issues.append(_no_match(line, grades[0], grades, ctx))


def _no_match(line: Line, grade: str, grades: list[str] | None, ctx: Context,
              unknown: bool = False) -> Issue:
    spec = line.spec
    form = (spec.form or "product").replace("_", " ")
    if unknown:
        reason = (f"We do not carry {grade} {form}. Our catalog covers stainless, carbon steel "
                  "and aluminum grades.")
        return issue("no_match", reason, field="grade")
    size = _size_words(spec)
    family = ctx.ref.grade_family(grade)
    stocked = [i for i in ctx.ref.catalog
               if ctx.ref.grade_family(i.grade) == family
               and ctx.ref.form_family(i.form) == ctx.ref.form_family(spec.form)]
    if not stocked:
        reason = f"We do not stock {grade} {form}."
    elif not any(_grade_fit(i, grade, _straight_only(line), ctx)[0] for i in stocked):
        have = ", ".join(sorted({i.grade for i in stocked}))
        reason = (f"We stock {form} only as {have}, which does not meet a {grade} "
                  "request as written.")
    else:
        reason = f"We stock {grade} {form}, but not in the requested size{size}."
    return issue("no_match", reason, field="match")


def _size_words(spec: Spec) -> str:
    parts = [f"{_num(v)} in {n}" for n, v in (
        ("thick", spec.thickness_in), ("wide", spec.width_in), ("long", spec.length_in),
        ("diameter", spec.diameter_in), ("wall", spec.wall_in)) if v is not None]
    return f" ({', '.join(parts)})" if parts else ""
