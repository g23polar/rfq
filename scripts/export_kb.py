"""Write out/knowledge_base.md: the reference data as plain sentences and tables, for upload
to the PRISM Knowledge Base (plans/17-prism-dashboard-setup.md).

Run: uv run python scripts/export_kb.py
Costs and suppliers are internal and left out.
"""
from pathlib import Path

from rfq.reference import SYNTHETIC_LABEL, ReferenceData, load_reference

OUT = Path(__file__).parent.parent / "out" / "knowledge_base.md"

MATERIAL_NAME = {"stainless": "stainless steel", "carbon": "carbon steel", "aluminum": "aluminum"}
FORM_NAME = {"sheet": "sheet", "plate": "plate", "bar": "bar", "tube": "tube", "pipe": "pipe"}


def _num(x: float) -> str:
    return f"{x:g}"


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers),
            *("| " + " | ".join(r) + " |" for r in rows), ""]


def build(ref: ReferenceData) -> str:
    t = ref.tables
    out = [
        "# RudCo RFQ-to-Quote reference data",
        "",
        f"**{SYNTHETIC_LABEL}.** Every item, price range, stock level and customer part number "
        "in this document is invented for a hackathon demo. None of it is a real price, real "
        "inventory or a real customer.",
        "",
        "## Sheet gauge thickness",
        "",
        "Gauge thickness depends on the material. The same gauge number is a different "
        "thickness for stainless steel, carbon steel and aluminum.",
        "",
    ]
    for material, gauges in t.gauge_sheet_in.items():
        for gauge, inches in gauges.items():
            out.append(f"- {gauge} gauge {MATERIAL_NAME[material]} sheet is {_num(inches)} in thick.")
        out.append("")
    out += ["Tube wall gauge is different from sheet gauge:", ""]
    out += [f"- {g} gauge tube wall is {_num(w)} in." for g, w in t.gauge_tube_wall_in.items()]
    tol = t.thickness_tolerance
    out += ["", f"A stated decimal thickness within {_num(tol.abs_in)} in or {_num(tol.pct)}% of "
            "a standard thickness is treated as that standard thickness.", ""]
    out += [f"- {MATERIAL_NAME[m].capitalize()} {_num(v)} in and thicker is plate; thinner is sheet."
            for m, v in t.plate_min_thickness_in.items()]

    out += ["", "## Default standards", "",
            "When an RFQ line names no standard, the default standard for its grade and form "
            "applies.", ""]
    for grade, by_form in t.default_standard.items():
        for form, standard in by_form.items():
            out.append(f"- The default standard for {grade} {FORM_NAME[form]} is {standard}.")

    out += ["", "## Grades", ""]
    for cert, d in t.dual_certified.items():
        out.append(f"- Dual-certified {cert} stock meets both {' and '.join(d.fills)}. It is "
                   f"supplied against a plain {' or '.join(d.fills)} request as a stated "
                   f"assumption. It does not fill a request for {' or '.join(d.does_not_fill)}.")
    for material, by_form in t.common_grades.items():
        for form, grades in by_form.items():
            out.append(f"- Common {MATERIAL_NAME[material]} {form} grades: {', '.join(grades)}.")
    for grade, info in t.grades.items():
        out.append(f"- Grade {grade} is {MATERIAL_NAME[info.material]}; also written "
                   f"{', '.join(v for v in info.variants if v != grade)}.")
    out += ["", "Substitutions are offered as labeled alternates, never made silently:", ""]
    out += [f"- {s.from_} → {s.to}: {s.note}" for s in t.substitutions]

    out += ["", "## Densities", ""]
    out += [f"- {MATERIAL_NAME[m].capitalize()} weighs {_num(d)} lb per cubic inch."
            for m, d in t.density_lb_per_in3.items()]

    out += ["", "## Abbreviations", ""]
    out += _table(["Written", "Means"], [[k, a.means] for k, a in t.abbreviations.items()])

    out += ["## Standard sizes", "",
            "- Standard sheet sizes (in): "
            + ", ".join(f"{_num(w)} x {_num(l)}" for w, l in t.standard_sheet_sizes_in) + ".",
            "- Standard plate sizes (in): "
            + ", ".join(f"{_num(w)} x {_num(l)}" for w, l in t.standard_plate_sizes_in) + ".",
            "- A sheet size written as two bare numbers is read in whichever unit makes it a "
            "standard size: \"4x8\" is 4 ft x 8 ft (48 x 96 in).", ""]
    out += _table(["NPS", "OD (in)", "Wall by schedule (in)"],
                  [[nps, _num(p.od_in), ", ".join(f"sch {s}: {_num(w)}" for s, w in p.wall_in.items())]
                   for nps, p in t.pipe_sizes.items()])

    p = ref.rules.pricing
    out += ["## Pricing and compliance rules", "",
            f"- The target price is the benchmark midpoint x {_num(p.target_multiplier_of_benchmark_mid)}.",
            f"- Quotes are valid for {p.validity_days} days from the quote date.",
            f"- A benchmark older than {p.stale_benchmark_days} days is stale.",
            "- DFARS specialty-metals compliance is judged by country of melt. Qualifying "
            "countries (ISO codes, illustrative): " + ", ".join(ref.rules.dfars.qualifying_countries) + ".",
            "- An unqualified \"domestic\" requirement is ambiguous between country of melt and "
            "country of manufacture; the buyer is asked which applies.", ""]

    out += [f"## Price benchmarks ($/lb, {SYNTHETIC_LABEL.lower()})", ""]
    out += _table(["Grade", "Form", "Low", "Mid", "High", "Source", "As of"],
                  [[g, f, f"{b.low:.2f}", f"{b.mid:.2f}", f"{b.high:.2f}", b.source, b.as_of]
                   for (g, f), b in ref.benchmarks.items()])
    out += ["Stainless alloy surcharges ($/lb):", ""]
    out += _table(["Grade", "Month", "Surcharge", "Source"],
                  [[s.grade, s.month, f"{s.surcharge_per_lb:.2f}", s.source] for s in ref.surcharges])

    out += [f"## Catalog ({SYNTHETIC_LABEL.lower()})", ""]
    out += _table(
        ["SKU", "Description", "Grade", "Form", "Standard", "Certifications", "Finish", "Stock",
         "Lead time (days)", "Country of melt", "MTR available"],
        [[i.sku, i.description, i.grade, i.form, i.standard, "; ".join(i.certifications),
          i.finish or "", str(i.stock_qty), str(i.lead_time_days), i.country_of_melt,
          i.mtr_available] for i in ref.catalog])

    out += [f"## Customer part numbers ({SYNTHETIC_LABEL.lower()})", "",
            "A customer part number resolves only for the customer it belongs to.", ""]
    for x in ref.cross_references:
        item = ref.item(x.sku)
        out.append(f"- {x.customer} part number {x.customer_part_no} is {x.sku}"
                   f" ({item.description if item else 'unknown item'}).")
    return "\n".join(out).rstrip() + "\n"


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(build(load_reference()))
    print(f"wrote {OUT}")
