"""Stage 6: can each offer ship from stock (plans/19-availability.md).

Stock is counted in pieces; the answer is given in the buyer's own unit. Availability never
changes a line's status and raises no issues: a short or unstocked line is still quoted, with
the shortfall stated.
"""

from rfq.context import Context
from rfq.models import Availability, Line, Offer
from rfq.price import piece_weight_lb
from rfq.reference import CatalogItem


def _stock_in_buyer_unit(offer: Offer, item: CatalogItem, ctx: Context) -> float | None:
    """Stock on hand, converted to the unit the buyer ordered in. None if it can't be converted."""
    unit = offer.spec.quantity_unit
    if unit == "ea":
        return float(item.stock_qty)
    if unit == "ft":
        return item.stock_qty * (offer.spec.length_in or item.length_in) / 12
    try:
        # The same weight the pricing stage uses, so the two never disagree.
        pounds = item.stock_qty * piece_weight_lb(offer.spec, item, ctx)
    except ValueError:
        return None
    return pounds / 100 if unit == "cwt" else pounds


def check(line: Line, ctx: Context) -> Line:
    for offer in line.offers:
        if offer.candidate is None or offer.spec.quantity is None:
            continue
        item = ctx.ref.item(offer.candidate.sku)
        on_hand = _stock_in_buyer_unit(offer, item, ctx) if item else None
        if on_hand is None:
            continue  # nothing is promised when the data can't support it
        wanted = offer.spec.quantity
        available = min(wanted, on_hand)
        shortfall = max(0.0, wanted - on_hand)
        status = "in_stock" if shortfall == 0 else "partial" if available > 0 else "not_stocked"
        offer.availability = Availability(
            status=status, available_qty=round(available, 2), shortfall_qty=round(shortfall, 2),
            lead_time_days=item.lead_time_days if shortfall > 0 else None)
    return line
