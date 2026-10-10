"""Stage 7, Price (plans/10-price.md): a price for each offer from the documented rules, in
the buyer's unit, with a rationale built from the calculated numbers only.

Price per lb = benchmark midpoint x target multiplier. A price under the margin floor is
kept, not raised, and the line gets an internal `below_floor` issue. No benchmark means no
price and an internal `unconfirmed` issue.
"""

import math
from datetime import timedelta

from rfq.context import Context
from rfq.models import Line, Offer, Price, PriceComponent, Spec, issue
from rfq.reference import CatalogItem

LB_PER_CWT = 100.0


def _dim(spec_value: float | None, item_value: float | None) -> float | None:
    return spec_value if spec_value is not None else item_value


def piece_weight_lb(spec: Spec, item: CatalogItem, ctx: Context) -> float:
    """Weight in pounds of one piece of what was requested.

    Dimensions come from `spec`, falling back to the item's own where the spec has none (a
    bar ordered by the foot has no length). Density is the item's material. Raises
    ValueError when a dimension needed for the form is missing from both."""
    density = ctx.ref.tables.density_lb_per_in3[item.material]
    t = _dim(spec.thickness_in, item.thickness_in)
    w = _dim(spec.width_in, item.width_in)
    length = _dim(spec.length_in, item.length_in)
    d = _dim(spec.diameter_in, item.diameter_in)
    wall = _dim(spec.wall_in, item.wall_in)
    form = item.form
    if form in ("sheet", "plate", "flat_bar"):
        dims = (t, w, length)
        volume = None if None in dims else t * w * length
    elif form == "round_bar":
        volume = None if None in (d, length) else math.pi / 4 * d**2 * length
    elif form in ("round_tube", "pipe"):
        volume = (None if None in (d, wall, length)
                  else math.pi / 4 * (d**2 - (d - 2 * wall) ** 2) * length)
    elif form == "square_tube":
        size = w if w is not None else d
        volume = (None if None in (size, wall, length)
                  else (size**2 - (size - 2 * wall) ** 2) * length)
    else:
        volume = None
    if volume is None:
        raise ValueError(f"cannot weigh {item.sku}: missing dimension for {form}")
    return volume * density


def _weight_and_unit_price(spec: Spec, item: CatalogItem, ctx: Context, per_lb: float
                           ) -> tuple[float, float]:
    """(total weight in lb, unit price) in the buyer's unit."""
    qty, unit = spec.quantity, spec.quantity_unit
    if unit == "lb":
        return qty, per_lb
    if unit == "cwt":
        return qty * LB_PER_CWT, round(per_lb * LB_PER_CWT, 2)
    piece = piece_weight_lb(spec, item, ctx)
    if unit == "ft":
        length = _dim(spec.length_in, item.length_in)
        per_ft = piece / (length / 12)
        return qty * per_ft, round(per_lb * per_ft, 2)
    return qty * piece, round(per_lb * piece, 2)


def _rationale(position: str, numbers: dict[str, float]) -> str:
    n = numbers
    head = f"Priced at ${n['price_per_lb']:.4f}/lb, "
    if position == "below_mid":
        where = f"{n['pct_below_mid']:.1f}% below the ${n['benchmark_mid']:.2f}/lb midpoint of the"
    elif position == "within_range":
        where = f"{n['pct_above_mid']:.1f}% above the ${n['benchmark_mid']:.2f}/lb midpoint of the"
    else:
        where = f"above the ${n['benchmark_high']:.2f}/lb top of the"
    return (f"{head}{where} benchmark range ${n['benchmark_low']:.2f}-"
            f"${n['benchmark_high']:.2f}/lb")


def _price_offer(offer: Offer, ctx: Context) -> tuple[Price | None, str | None, str | None]:
    """(price, unconfirmed reason, below-floor message)."""
    item = ctx.ref.item(offer.candidate.sku)
    if item is None:
        return None, f"{offer.candidate.sku} is not in the catalog.", None
    benchmark = ctx.ref.benchmark_for(item.grade, item.form)
    if benchmark is None:
        return None, f"No benchmark for {item.grade} {item.form}; not priced.", None
    rules = ctx.ref.rules.pricing
    spec = offer.spec
    per_lb = round(benchmark.mid * rules.target_multiplier_of_benchmark_mid, 4)
    try:
        weight, unit_price = _weight_and_unit_price(spec, item, ctx, per_lb)
    except ValueError as e:
        return None, f"{e}; not priced.", None
    extended = round(unit_price * spec.quantity, 2)

    numbers = {"price_per_lb": per_lb, "benchmark_mid": benchmark.mid,
               "benchmark_low": benchmark.low, "benchmark_high": benchmark.high}
    if per_lb < benchmark.mid:
        position = "below_mid"
        numbers["pct_below_mid"] = round((1 - per_lb / benchmark.mid) * 100, 1)
    elif per_lb <= benchmark.high:
        position = "within_range"
        numbers["pct_above_mid"] = round((per_lb / benchmark.mid - 1) * 100, 1)
    else:
        position = "above_range"
    rationale = (f"{_rationale(position, numbers)} "
                 f"({benchmark.source} data, as of {benchmark.as_of}).")

    margin = (per_lb - item.cost_per_lb) / per_lb * 100
    price = Price(
        unit=spec.quantity_unit, unit_price=unit_price, extended=extended,
        components=[PriceComponent(name="base", amount=extended)],
        weight_lb=round(weight, 2), benchmark=benchmark, position=position,
        rationale=rationale, numbers=numbers,
        valid_until=(ctx.today + timedelta(days=rules.validity_days)).isoformat(),
        cost_per_lb=item.cost_per_lb, margin_pct=round(margin, 1),
        floor_margin_pct=rules.margin_floor_pct)
    below = None
    if margin < rules.margin_floor_pct:
        below = (f"Margin {margin:.1f}% is under the {rules.margin_floor_pct:.1f}% floor "
                 f"at ${per_lb:.4f}/lb (cost ${item.cost_per_lb:.4f}/lb).")
    return price, None, below


def price(line: Line, ctx: Context) -> Line:
    if not line.offers:
        return line
    several = len(line.offers) > 1
    for offer in line.offers:
        spec = offer.spec
        if offer.candidate is None or not spec.quantity or not spec.quantity_unit:
            continue
        result, unconfirmed, below = _price_offer(offer, ctx)
        offer.price = result
        prefix = f"{offer.label}: " if several else ""
        if unconfirmed:
            line.issues.append(issue("unconfirmed", prefix + unconfirmed, "price"))
        if below:
            line.issues.append(issue("below_floor", prefix + below, "price"))
    return line
