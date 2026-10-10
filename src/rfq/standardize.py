"""Stage 4: turn a Reading into one canonical Spec and record every inference as an issue
(plans/08-standardize.md).

Entry point: `standardize(line, ctx)`. Dimensions end up in inches, shorthand is expanded
from the reference tables, and the fingerprint is the canonical fields joined with "|".
"""

import re
from dataclasses import dataclass

from rfq.context import Context
from rfq.models import Issue, Line, Reading, Sourced, Spec, issue

FLAT = ("sheet", "plate", "flat_bar")
TUBES = ("round_tube", "square_tube", "pipe")
# Unlabeled dimensions are assigned smallest to largest in this order.
SLOTS = {
    "sheet": ("thickness", "width", "length"),
    "plate": ("thickness", "width", "length"),
    "flat_bar": ("thickness", "width", "length"),
    "round_bar": ("diameter", "length"),
    "round_tube": ("wall", "diameter", "length"),
    "pipe": ("wall", "diameter", "length"),
    "square_tube": ("wall", "width", "length"),
}
REQUIRED = {
    "sheet": ("thickness", "width", "length"),
    "plate": ("thickness", "width", "length"),
    "flat_bar": ("thickness", "width", "length"),
    "round_bar": ("diameter", "length"),
    "round_tube": ("diameter", "wall", "length"),
    "pipe": ("diameter", "wall", "length"),
    "square_tube": ("width", "wall", "length"),
}
BARE_INCH_LIMIT = {"thickness": 2.0, "wall": 2.0, "diameter": 24.0, "width": 24.0}
SPEC_FIELD = {"thickness": "thickness_in", "wall": "wall_in", "diameter": "diameter_in",
              "width": "width_in", "length": "length_in"}
FIELD_LABEL = {"thickness": "thickness", "wall": "wall thickness", "diameter": "diameter",
               "width": "width", "length": "length"}

FRACTIONS = {"¼": "1/4", "½": "1/2", "¾": "3/4", "⅛": "1/8", "⅜": "3/8", "⅝": "5/8",
             "⅞": "7/8", "⅓": "1/3", "⅔": "2/3"}
NUM = (r"\d+\s+\d+/\d+|\d+-\d+/\d+|\d+/\d+|\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d*\.\d+|\d+")
MEASURE = re.compile(rf"^\s*#?(?P<num>{NUM})\s*(?P<unit>[^\d\s].*)?$")

INCHES_PER = {
    "in": 1.0, "inch": 1.0, "inches": 1.0, '"': 1.0, "”": 1.0, "″": 1.0, "''": 1.0,
    "ft": 12.0, "foot": 12.0, "feet": 12.0, "'": 12.0, "′": 12.0, "’": 12.0,
    "mm": 1 / 25.4, "millimeter": 1 / 25.4, "millimeters": 1 / 25.4,
    "cm": 1 / 2.54, "centimeter": 1 / 2.54, "centimeters": 1 / 2.54,
    "m": 1 / 0.0254, "meter": 1 / 0.0254, "meters": 1 / 0.0254,
}
GAUGE_UNITS = {"ga", "gauge", "g", "gage"}
QTY_UNITS = {
    "": "ea", "ea": "ea", "each": "ea", "pc": "ea", "pcs": "ea", "piece": "ea",
    "pieces": "ea", "sheets": "ea", "sheet": "ea", "plates": "ea", "bars": "ea",
    "lb": "lb", "lbs": "lb", "#": "lb", "pound": "lb", "pounds": "lb",
    "cwt": "cwt", "ft": "ft", "foot": "ft", "feet": "ft", "'": "ft",
}
MATERIAL_NAMES = {
    "STAINLESS": "stainless", "STAINLESS STEEL": "stainless", "CARBON": "carbon",
    "CARBON STEEL": "carbon", "MILD STEEL": "carbon", "ALUMINUM": "aluminum",
    "ALUMINIUM": "aluminum",
}
MATERIAL_TEXT = {"stainless": "stainless steel", "carbon": "carbon steel", "aluminum": "aluminum"}
FORM_NAMES = {
    "SHEET": "sheet", "SHEETS": "sheet", "PLATE": "plate", "PLATES": "plate",
    "ROUND BAR": "round_bar", "ROUND": "round_bar", "FLAT BAR": "flat_bar",
    "FLAT": "flat_bar", "SQUARE TUBE": "square_tube", "SQUARE TUBING": "square_tube",
    "ROUND TUBE": "round_tube", "ROUND TUBING": "round_tube", "PIPE": "pipe",
    "BAR": "bar", "TUBE": "tube", "TUBING": "tube",
}
FORM_TEXT = {"sheet": "sheet", "plate": "plate", "round_bar": "round bar",
             "flat_bar": "flat bar", "round_tube": "round tube",
             "square_tube": "square tube", "pipe": "pipe"}


@dataclass
class Dim:
    value: float
    factor: float | None  # inches per unit; None when the RFQ gave no unit
    text: str

    @property
    def inches(self) -> float | None:
        return None if self.factor is None else round(self.value * self.factor, 4)

    @property
    def sort_key(self) -> float:
        return self.value * (self.factor or 1.0)


def _fractions(text: str) -> str:
    for ch, frac in FRACTIONS.items():
        text = re.sub(rf"(\d)\s*{ch}", rf"\1 {frac}", text).replace(ch, frac)
    return text


def _number(text: str) -> float:
    text = text.replace(",", "")
    whole = 0.0
    m = re.match(r"^(\d+)[\s-]+(\d+/\d+)$", text)
    if m:
        whole, text = float(m[1]), m[2]
    if "/" in text:
        n, d = text.split("/")
        return whole + float(n) / float(d)
    return whole + float(text)


def _measure(s: Sourced | None) -> tuple[float, str] | None:
    """Number and unit text of a Sourced, from `value` and `unit` in whatever mix they come."""
    if s is None:
        return None
    unit = (s.unit or "").strip()
    if isinstance(s.value, (int, float)):
        return float(s.value), unit
    m = MEASURE.match(_fractions(str(s.value).strip()))
    if not m:
        return None
    return _number(m["num"]), unit or (m["unit"] or "").strip()


def _unit_key(unit: str) -> str:
    return unit.strip().lower().rstrip(".")


def _dim(s: Sourced | None) -> Dim | None:
    """None when absent or unreadable; `factor=None` for a bare number."""
    got = _measure(s)
    if got is None:
        return None
    value, unit = got
    key = _unit_key(unit)
    if key and key not in INCHES_PER:
        return None
    return Dim(value, INCHES_PER.get(key), _written(s))


def _written(s: Sourced) -> str:
    return (s.source_text or f"{s.value} {s.unit or ''}").strip()


def _fmt(x: float | None) -> str:
    return "" if x is None else f"{x:.4f}".rstrip("0").rstrip(".")


def _norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9&#]+", " ", text.upper()).strip()


def _grade_regex(variant: str) -> re.Pattern:
    parts = []
    for ch in variant.upper():
        parts.append(r"[\s-]?" if ch in " -" else r"\s*/\s*" if ch == "/" else re.escape(ch))
    return re.compile(r"(?<![A-Z0-9])" + "".join(parts) + r"(?![A-Z0-9])")


class _Standardizer:
    def __init__(self, line: Line, ctx: Context):
        self.ctx = ctx
        self.ref = ctx.ref
        self.tables = ctx.ref.tables
        self.r: Reading = line.reading  # type: ignore[assignment]
        self.issues: list[Issue] = []
        self.flagged: set[str] = set()  # fields that already carry a buyer issue
        self.spec = Spec()
        self.spec_done: set[str] = set()
        self.form_inferred = False
        self.pool_conventional = False

    def add(self, kind, message, field=None, options=None, flag=False) -> None:
        self.issues.append(issue(kind, message, field, options))
        if flag and field:
            self.flagged.add(field)

    # ---- vocabulary ------------------------------------------------------------

    def _lookup(self, text: str, names: dict[str, str], field: str) -> tuple[str, str | None] | None:
        """(value, finish) for the first word or word pair that is a known name or shorthand."""
        table = dict(names)
        finish: dict[str, str | None] = {}
        for key, ab in self.tables.abbreviations.items():
            if ab.field == field:
                table[_norm(key)] = ab.value
                finish[_norm(key)] = ab.finish
        words = _norm(text).split()
        grams = [" ".join(words[i:i + n]) for n in (2, 1) for i in range(len(words) - n + 1)]
        for g in grams:
            if g in table:
                return table[g], finish.get(g)
        return None

    # ---- quantity --------------------------------------------------------------

    def quantity(self, required: bool = True) -> None:
        q = self.r.quantity
        got = _measure(q)
        if got is None:
            if required:
                self.add("missing", "No quantity was given. How many do you need?", "quantity",
                         flag=True)
            return
        value, unit = got
        key = _unit_key(unit)
        if key not in QTY_UNITS or value <= 0:
            self.add("missing", f"We could not read the quantity \"{_written(q)}\". How many "
                     "do you need, and in what unit (pieces, pounds, cwt or feet)?",
                     "quantity", flag=True)
            return
        self.spec.quantity = value
        self.spec.quantity_unit = QTY_UNITS[key]  # type: ignore[assignment]

    # ---- material, grade, form -------------------------------------------------

    def material(self) -> None:
        self.finish_from_material: str | None = None
        self.material_stated: str | None = None
        if self.r.material:
            got = self._lookup(str(self.r.material.value), MATERIAL_NAMES, "material")
            if got:
                self.material_stated, self.finish_from_material = got

    def grade(self) -> None:
        """Sets spec.grade and spec.material; leaves `self.grade_options` for later."""
        self.grade_options: list[str] = []
        self.grade_stated = bool(self.r.grade and str(self.r.grade.value).strip())
        material = self.material_stated
        if self.grade_stated:
            found = self._find_grades(str(self.r.grade.value))  # type: ignore[union-attr]
            if len(found) == 1:
                family, canon = found[0]
                canon, note = self._temper(family, canon)
                self.spec.grade = canon
                if note:
                    self.add("assumption", note, "grade")
                grade_material = self.tables.grades[family].material
                if material and material != grade_material:
                    self.add("conflict", f"The line says {MATERIAL_TEXT[material]} but grade "
                             f"{canon} is {MATERIAL_TEXT[grade_material]}. Which did you mean?",
                             "grade", flag=True)
                material = grade_material
            elif len(found) > 1:
                options = [c for _, c in found]
                if len({f for f, _ in found}) > 1:
                    options = list(dict.fromkeys(f for f, _ in found))
                self.grade_options = options
                materials = {self.tables.grades[f].material for f, _ in found}
                if len(materials) == 1:
                    material = materials.pop()
                self.add("ambiguous_options",
                         f"The grade \"{_written(self.r.grade)}\" could mean more than one "  # type: ignore[arg-type]
                         f"grade. Which do you want: {self._or(options)}?", "grade", options)
                self.flagged.add("grade")
        self.spec.material = material

    def _or(self, items: list[str]) -> str:
        return " or ".join(items) if len(items) < 3 else ", ".join(items[:-1]) + f" or {items[-1]}"

    def _find_grades(self, text: str) -> list[tuple[str, str]]:
        t = text.upper()
        found: list[tuple[int, str, str]] = []

        def blank(m: re.Match) -> str:
            return " " * len(m[0])

        for m in re.finditer(r"(?<![A-Z0-9])(\d{3})\s*/\s*([LH])(?![A-Z0-9])", t):
            if m[1] in self.tables.grades:
                found += [(m.start(), m[1], m[1]), (m.start() + 1, m[1], m[1] + m[2])]
        t = re.sub(r"(?<![A-Z0-9])(\d{3})\s*/\s*([LH])(?![A-Z0-9])", blank, t)
        patterns = {(v.upper(), fam) for fam, info in self.tables.grades.items()
                    for v in [fam, *info.variants]}
        for variant, fam in sorted(patterns, key=lambda p: -len(p[0])):
            rx = _grade_regex(variant)
            found += [(m.start(), fam, variant) for m in rx.finditer(t)]
            t = rx.sub(blank, t)
        out: list[tuple[str, str]] = []
        for _, fam, variant in sorted(found):
            pair = (fam, self._canonical(fam, variant))
            if pair not in out:
                out.append(pair)
        if len(out) == 1 and "?" in text and "/" in text and out[0][0] in ("304", "316"):
            out = [(out[0][0], out[0][0]), (out[0][0], out[0][0] + "L")]
        return out

    def _canonical(self, family: str, variant: str) -> str:
        v = variant.upper().replace(" ", "")
        if self.tables.grades[family].material == "stainless" and v in (family + "L", family + "H"):
            return v
        return family

    def _temper(self, family: str, canon: str) -> tuple[str, str | None]:
        """Aluminum written without its temper takes the stocked one, as an assumption."""
        if self.tables.grades[family].material != "aluminum":
            return canon, None
        written = _norm(str(self.r.grade.value))  # type: ignore[union-attr]
        if self.r.temper:
            combined = _norm(f"{canon.split('-')[0]}-{self.r.temper.value}")
            if combined == _norm(canon):
                return canon, None
        if written.replace(" ", "") != _norm(canon).replace(" ", ""):
            return canon, f"Grade \"{_written(self.r.grade)}\" was taken as {canon}."  # type: ignore[arg-type]
        return canon, None

    def form(self) -> None:
        self.form_stated = bool(self.r.form and str(self.r.form.value).strip())
        form = None
        if self.form_stated:
            got = self._lookup(str(self.r.form.value), FORM_NAMES, "form")  # type: ignore[union-attr]
            form = got[0] if got else None
        r = self.r
        if form == "bar":
            if r.diameter:
                form = "round_bar"
            elif r.thickness or r.gauge or r.width:
                form = "flat_bar"
            else:
                form = None
        elif form == "tube":
            if r.diameter:
                form = "round_tube"
            elif r.width:
                form = "square_tube"
            else:
                form = None
        if form and form != (str(r.form.value).strip().lower().replace(" ", "_") if r.form else ""):
            generic = _norm(str(r.form.value)) in ("BAR", "TUBE", "TUBING") if r.form else False
            if generic:
                self.add("assumption", f"\"{r.form.value}\" was read as {FORM_TEXT[form]} "  # type: ignore[union-attr]
                         "from the dimensions given.", "form")
        if (form is None and not self.form_stated and (r.thickness or r.gauge)
                and not (r.diameter or r.wall)
                and (len(r.unlabeled_dimensions) >= 2 or (r.width and r.length))):
            # A thickness with a width and a length and no form named is flat product (L1).
            form, self.form_inferred = "sheet", True
        self.spec.form = form

    def flat_form(self) -> None:
        """Settle sheet versus plate for an inferred form, once the thickness is known."""
        if not self.form_inferred:
            return
        limit = self.tables.plate_min_thickness_in.get(self.spec.material)  # type: ignore[arg-type]
        if self.spec.thickness_in and limit and self.spec.thickness_in >= limit:
            self.spec.form = "plate"
        self.add("assumption", "No form was named; a thickness with a width and a length was "
                 f"read as {FORM_TEXT[self.spec.form]}.", "form")

    # ---- dimensions ------------------------------------------------------------

    def _bare_to_inches(self, slot: str, dim: Dim, quiet: bool = False) -> float | None:
        if dim.factor is not None:
            return dim.inches
        limit = BARE_INCH_LIMIT.get(slot)
        if limit is not None and dim.value <= limit:
            if not quiet:
                self.add("assumption", f"The {FIELD_LABEL[slot]} \"{dim.text}\" had no unit; "
                         "it was read as inches.", slot)
            return round(dim.value, 4)
        self.add("missing", f"Please give the unit for the {FIELD_LABEL[slot]} "
                 f"\"{dim.text}\" (inches, feet or mm).", slot, flag=True)
        return None

    def dimensions(self) -> None:
        r, form = self.r, self.spec.form
        labeled: dict[str, Dim] = {}
        bad: list[tuple[str, Sourced]] = []

        def put(slot: str, s: Sourced | None) -> None:
            if s is None:
                return
            d = _dim(s)
            if d is None:
                bad.append((slot, s))
            elif slot not in labeled:
                labeled[slot] = d

        tube = form in TUBES
        thick_slot = "wall" if tube else "thickness"
        thick_src = (r.wall or r.thickness) if tube else r.thickness
        gauge_src = r.gauge
        if thick_src is not None and self._is_gauge(thick_src):
            gauge_src, thick_src = gauge_src or thick_src, None
        put(thick_slot, thick_src)
        put("width", r.width)
        put("length", r.length)
        if form == "square_tube":
            put("width", r.diameter)
        else:
            put("diameter", r.diameter)
        for slot, s in bad:
            self.add("missing", f"We could not read the {FIELD_LABEL[slot]} \"{_written(s)}\". "
                     "Please restate it with its unit.", slot, flag=True)

        gauge_n = self._gauge(gauge_src)
        pool = self._pool(labeled, gauge_n is not None)
        assigned = self._assign(form, labeled, pool, gauge_n is not None)
        self._flat_pair(labeled, form)
        self._thickness(thick_slot, gauge_n, labeled.get(thick_slot), thick_slot in assigned)
        for slot in ("diameter", "length", "width"):
            if slot in labeled and slot not in self.spec_done:
                self._set(slot, self._bare_to_inches(slot, labeled[slot], slot in assigned
                                                     and slot != "length"))
        if (assigned and not self.pool_conventional
                and not (form in FLAT and set(assigned) <= {"width", "length"})):
            parts = [f"{FIELD_LABEL[s]} {_fmt(getattr(self.spec, SPEC_FIELD[s]))} in"
                     for s in assigned if getattr(self.spec, SPEC_FIELD[s]) is not None]
            if parts:
                self.add("assumption", "The dimensions were not labeled "
                         f"(\"{' x '.join(dict.fromkeys(d.text for d in assigned.values()))}\"); read from "
                         f"smallest to largest as {', '.join(parts)}.", assigned and next(iter(assigned)))

    def _set(self, slot: str, value: float | None) -> None:
        if value is not None:
            setattr(self.spec, SPEC_FIELD[slot], value)
        self.spec_done.add(slot)

    def _is_gauge(self, s: Sourced) -> bool:
        got = _measure(s)
        return bool(got) and _unit_key(got[1]) in GAUGE_UNITS

    def _gauge(self, src: Sourced | None) -> int | None:
        got = _measure(src)
        if got is None:
            return None
        return int(round(got[0]))

    def _pool(self, labeled: dict[str, Dim], has_gauge: bool) -> list[Dim]:
        pool = []
        for s in self.r.unlabeled_dimensions:
            d = _dim(s)
            if d is None:
                self.add("missing", f"We could not read the dimension \"{_written(s)}\". "
                         "Please restate it with its unit.", None)
                continue
            pool.append(d)
        # Written smallest first with units on every figure ("1/4 in x 48 in x 96 in") is the
        # trade's usual thickness x width x length, so reading it that way is not an inference.
        self.pool_conventional = (all(d.factor is not None for d in pool)
                                  and pool == sorted(pool, key=lambda d: d.sort_key))
        pool.sort(key=lambda d: d.sort_key)
        if self.spec.form == "square_tube" and len(pool) >= 2:
            for a, b in zip(pool, pool[1:]):
                if abs(a.sort_key - b.sort_key) < 1e-9:
                    pool.remove(b)
                    break
        return pool

    def _assign(self, form: str | None, labeled: dict[str, Dim], pool: list[Dim],
                has_gauge: bool) -> dict[str, Dim]:
        if not pool:
            return {}
        if form is None:
            self.add("open_question", "We could not tell what the dimensions "
                     f"\"{' x '.join(d.text for d in pool)}\" refer to. Please label them "
                     "(thickness, width, length, diameter).", None)
            return {}
        thick_slot = "wall" if form in TUBES else "thickness"
        missing = [s for s in SLOTS[form]
                   if s not in labeled and not (s == thick_slot and has_gauge)]
        n, k = len(pool), len(missing)
        if n == k:
            chosen = missing
        elif 2 <= n < k:
            chosen = missing[-n:]
        elif n == 1 < k and missing[-1] == "length" and pool[0].factor is not None:
            chosen = ["length"]
        else:
            self.add("open_question", "We could not tell what the dimensions "
                     f"\"{' x '.join(d.text for d in pool)}\" refer to. Please say which is the "
                     "thickness, width, length or diameter.", None)
            return {}
        assigned = dict(zip(chosen, pool))
        labeled.update(assigned)
        return assigned

    def _flat_pair(self, labeled: dict[str, Dim], form: str | None) -> None:
        if form not in FLAT or "width" not in labeled or "length" not in labeled:
            return
        w, l = labeled["width"], labeled["length"]
        if w.factor is not None and l.factor is not None:
            return
        if w.factor is None and l.factor is None:
            sizes = {tuple(sorted(s)) for s in
                     (*self.tables.standard_sheet_sizes_in, *self.tables.standard_plate_sizes_in)}
            for factor, name in ((1.0, "inches"), (12.0, "feet")):
                pair = tuple(sorted((round(w.value * factor, 4), round(l.value * factor, 4))))
                if pair in sizes:
                    w.factor = l.factor = factor
                    if factor != 1.0:
                        self.add("assumption", f"\"{w.text} x {l.text}\" had no unit; it was "
                                 f"read as {name} ({_fmt(w.inches)} in x {_fmt(l.inches)} in), "
                                 "which is a standard sheet size.", "width")
                    return
            self.add("missing", f"Please give the unit for the size \"{w.text} x {l.text}\" "
                     "(inches or feet).", "width", flag=True)
            self.flagged.add("length")
            labeled.pop("width"), labeled.pop("length")
            self.spec_done |= {"width", "length"}
            return
        known = w if w.factor is not None else l
        other = l if known is w else w
        other.factor = known.factor
        self.add("assumption", f"\"{other.text}\" had no unit; it was read in the same unit as "
                 f"\"{known.text}\".", "width" if other is w else "length")

    def _thickness(self, slot: str, gauge: int | None, dim: Dim | None, from_pool: bool) -> None:
        form, material = self.spec.form, self.spec.material
        tube = slot == "wall"
        label = FIELD_LABEL[slot]
        table = None
        gauge_value = None
        if gauge is not None:
            table = self.tables.gauge_tube_wall_in if tube else (
                self.tables.gauge_sheet_in.get(material) if material else None)  # type: ignore[arg-type]
            if table is None:
                self.add("missing", f"A {gauge} gauge depends on the material. Please tell us "
                         "the material or grade, or give the thickness in inches.", "grade",
                         flag=True)
                self.flagged.add(slot)
            else:
                gauge_value = table.get(str(gauge))
                if gauge_value is None:
                    self.add("missing", f"We do not have a thickness for {gauge} gauge. Please "
                             f"give the {label} in inches.", slot, flag=True)
        value = self._bare_to_inches(slot, dim, from_pool) if dim else None
        if dim and value is None and slot in self.flagged:
            return
        if gauge_value is not None and value is None:
            self._set(slot, gauge_value)
            return
        if gauge_value is not None and value is not None:
            tol = self._tol(gauge_value)
            if abs(value - gauge_value) <= tol + 1e-9:
                if abs(value - gauge_value) > 1e-4:
                    self.add("assumption", f"{gauge} gauge and {_fmt(value)} in were both given; "
                             f"they agree, so the standard {_fmt(gauge_value)} in was used.", slot)
                self._set(slot, gauge_value)
            else:
                self.add("conflict", f"The line gives {gauge} gauge ({_fmt(gauge_value)} in) "
                         f"and {_fmt(value)} in, which do not match. Which did you mean?", slot,
                         flag=True)
                self.spec_done.add(slot)
            return
        if value is None:
            return
        standards = None if tube or not material else self.tables.standard_thickness_in.get(material)
        if standards:
            nearest = min(standards, key=lambda s: abs(s - value))
            if abs(nearest - value) > 1e-4 and abs(nearest - value) <= self._tol(nearest) + 1e-9:
                self.add("assumption", f"Thickness {_fmt(value)} in was matched to the standard "
                         f"{_fmt(nearest)} in{self._gauge_note(nearest)}.", slot)
                value = nearest
        self._set(slot, value)

    def _gauge_note(self, std: float) -> str:
        table = self.tables.gauge_sheet_in.get(self.spec.material or "", {})  # type: ignore[call-overload]
        for g, v in table.items():
            if abs(v - std) < 1e-9:
                return f" ({g} gauge)"
        return ""

    def _tol(self, std: float) -> float:
        t = self.tables.thickness_tolerance
        return max(t.abs_in, t.pct / 100 * std)

    # ---- standard, finish, temper ----------------------------------------------

    def standard_finish_temper(self) -> None:
        spec, r = self.spec, self.r
        if r.standard and str(r.standard.value).strip():
            text = _norm(str(r.standard.value))
            m = re.match(r"^(?:ASTM )?([A-Z])\s?(\d+.*)$", text)
            spec.standard = f"ASTM {m[1]}{m[2].replace(' ', '')}" if m else str(r.standard.value).strip()
        elif spec.form:
            grades = [spec.grade] if spec.grade else self.grade_options
            families = {self.ref.grade_family(g) for g in grades}
            if grades and len(families) == 1:
                std = self.ref.default_standard(grades[0], spec.form)
                if std:
                    spec.standard = std
                    self.add("assumption", f"No standard was given, so {std} was assumed.",
                             "standard")
        finish = str(r.finish.value).strip() if r.finish and str(r.finish.value).strip() else None
        spec.finish = finish or self.finish_from_material
        if r.temper and str(r.temper.value).strip():
            spec.temper = str(r.temper.value).strip().upper()

    # ---- grade and required-field checks -----------------------------------------

    def checks(self) -> None:
        spec = self.spec
        if spec.grade is None and not self.grade_options and not self.grade_stated:
            ff = self.ref.form_family(spec.form) if spec.form else None
            options = self.tables.common_grades.get(spec.material, {}).get(ff, []) \
                if spec.material and ff else []
            if options:
                self.add("ambiguous_options", "No grade was given. Which grade do you want: "
                         f"{self._or(list(options))}?", "grade", list(options))
            elif "grade" not in self.flagged:
                self.add("missing", "No grade was given, and we need the material and form to "
                         "suggest options. Please tell us the grade.", "grade", flag=True)
        if spec.form is None and not self.form_stated and "form" not in self.flagged:
            self.add("missing", "We could not tell what form this is (sheet, plate, bar, tube "
                     "or pipe). Please tell us.", "form", flag=True)
        for slot in REQUIRED.get(spec.form or "", ()):
            if getattr(spec, SPEC_FIELD[slot]) is None and slot not in self.flagged:
                self.add("missing", f"The {FIELD_LABEL[slot]} is missing. Please give it.",
                         slot, flag=True)

    def fingerprint(self) -> None:
        s = self.spec
        parts = [s.material, s.grade, s.form, _fmt(s.thickness_in), _fmt(s.width_in),
                 _fmt(s.length_in), _fmt(s.diameter_in), _fmt(s.wall_in), s.standard,
                 s.finish, s.temper]
        s.fingerprint = "|".join("" if p is None else str(p) for p in parts)


DESCRIPTION_FIELDS = ("material", "grade", "form", "thickness", "gauge", "wall", "width",
                      "length", "diameter", "standard", "finish", "temper")


def standardize(line: Line, ctx: Context) -> Line:
    if line.segment.kind != "item" or line.reading is None:
        return line
    r = line.reading
    s = _Standardizer(line, ctx)
    has_description = any(getattr(r, f) for f in DESCRIPTION_FIELDS) or r.unlabeled_dimensions
    if r.customer_part_no and not has_description:
        s.quantity(required=False)
        line.spec = s.spec
        line.issues.extend(s.issues)
        return line
    s.quantity()
    s.material()
    s.grade()
    s.form()
    s.dimensions()
    s.flat_form()
    s.standard_finish_temper()
    s.checks()
    s.fingerprint()
    line.spec = s.spec
    line.issues.extend(s.issues)
    return line
