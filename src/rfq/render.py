"""Stage 12: the deliverables (plans/14-pipeline-and-api.md).

Buyer-facing documents are built from `buyer_view(run)` only, so internal data has no way in.
The internal summary reads the full run and is never sent.
"""

import re
from html import escape

from rfq.decide import email_questions
from rfq.models import (PRICED_STATUSES, Availability, BuyerLine, BuyerOffer, BuyerQuote, Run,
                        buyer_view)

SYNTHETIC = ("Demonstration quote. The catalog, stock, prices and market benchmarks behind it "
             "are synthetic data, not real offers.")
STATUS_LABEL = {
    "quoted": "Quoted", "quoted_with_assumptions": "Quoted with assumptions",
    "quoted_with_alternates": "Quoted with alternates", "needs_buyer_input": "Awaiting your answer",
    "needs_specialist_review": "Needs specialist review", "no_bid": "No bid",
    "not_an_item": "Note",
}
UNIT = {"ea": "ea", "lb": "lb", "cwt": "cwt", "ft": "ft"}


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _qty(value: float | None) -> str:
    return "" if value is None else f"{value:,.2f}".rstrip("0").rstrip(".")


def availability_text(a: Availability | None, unit: str | None) -> str:
    if a is None:
        return "Availability to be confirmed"
    u = UNIT.get(unit or "", "")
    lead = f" in about {a.lead_time_days} days" if a.lead_time_days else ""
    if a.status == "in_stock":
        return "In stock"
    if a.status == "partial":
        return (f"{_qty(a.available_qty)} {u} in stock now; the remaining "
                f"{_qty(a.shortfall_qty)} {u}{lead or ' to follow'}")
    return f"Not stocked; available{lead}" if lead else "Not stocked"


def valid_until(quote: BuyerQuote) -> str | None:
    dates = [o.price.valid_until for l in quote.lines for o in l.offers if o.price]
    return min(dates) if dates else None


# The buyer quote is styled as a mill document: paper stock, ink rules, one oxide accent,
# figures in a fixed-width face. Fonts load from Google Fonts when online and fall back to
# local faces; nothing else is fetched, and the print rules drop colour fills and motion.
QUOTE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@600;800&family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:ital,wght@0,400;0,600;1,400&display=swap');
:root{--ink:#14181c;--steel:#5b6770;--rule:#b9b3a6;--paper:#f6f3ec;--sheet:#fffdf8;--oxide:#c2410c;
--display:'Big Shoulders Display','Oswald','Arial Narrow',sans-serif;
--body:'IBM Plex Sans','Segoe UI','Helvetica Neue',sans-serif;
--mono:'IBM Plex Mono','SFMono-Regular',Menlo,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;padding:40px 20px 64px;background:var(--paper);color:var(--ink);font:15px/1.5 var(--body);
background-image:repeating-linear-gradient(0deg,transparent 0 27px,rgba(20,24,28,.035) 27px 28px)}
.sheet{max-width:980px;margin:0 auto;background:var(--sheet);border:1px solid var(--rule);
box-shadow:0 1px 0 #fff inset,0 18px 40px -24px rgba(20,24,28,.45);position:relative}
.band{height:14px;background:var(--ink)}
.draft .band{background:repeating-linear-gradient(135deg,var(--ink) 0 14px,var(--oxide) 14px 28px)}
header{display:grid;grid-template-columns:1fr auto;gap:24px 40px;padding:32px 40px 28px;
border-bottom:3px solid var(--ink);position:relative}
.kicker{font:600 12px/1 var(--mono);letter-spacing:.22em;text-transform:uppercase;color:var(--steel)}
h1{font:800 64px/.95 var(--display);letter-spacing:.01em;text-transform:uppercase;margin:10px 0 8px}
h1 .id{display:block;font:600 22px/1.3 var(--mono);letter-spacing:.04em;text-transform:none;color:var(--oxide)}
.rev{margin:0;color:var(--steel);font-size:14px}
.meta{margin:0;display:grid;grid-template-columns:auto auto;align-self:start;border:1px solid var(--ink)}
.meta div{display:contents}
.meta dt,.meta dd{margin:0;padding:7px 12px;border-bottom:1px solid var(--rule)}
.meta div:last-child dt,.meta div:last-child dd{border-bottom:0}
.meta dt{font:600 11px/1.6 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--steel);
border-right:1px solid var(--rule)}
.meta dd{font:600 14px/1.4 var(--mono)}
.stamp{display:inline-block;margin:20px 0 0 4px;transform:rotate(-4deg);border:4px double var(--oxide);
color:var(--oxide);padding:6px 16px 8px;font:800 40px/1 var(--display);letter-spacing:.12em;
text-align:center;opacity:.9;animation:thunk .5s cubic-bezier(.2,1.6,.4,1) .35s both}
.stamp small{display:block;font:600 10px/1.4 var(--mono);letter-spacing:.16em;text-transform:uppercase}
main{padding:8px 40px 36px}
h2{font:800 26px/1 var(--display);letter-spacing:.08em;text-transform:uppercase;margin:32px 0 12px;
display:flex;align-items:center;gap:14px}
h2::after{content:"";flex:1;height:1px;background:var(--ink)}
table{border-collapse:collapse;width:100%}
th{font:600 11px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--steel);
text-align:left;padding:0 10px 8px;border-bottom:2px solid var(--ink)}
td{padding:14px 10px;vertical-align:top;border-bottom:1px solid var(--rule)}
th.num,td.num{text-align:right;white-space:nowrap;font-family:var(--mono);font-variant-numeric:tabular-nums}
td.num strong{font-size:16px}
tbody tr{animation:rise .45s ease both}
tbody tr:nth-child(2){animation-delay:.05s}tbody tr:nth-child(3){animation-delay:.1s}
tbody tr:nth-child(4){animation-delay:.15s}tbody tr:nth-child(n+5){animation-delay:.2s}
.no{width:92px;border-right:1px solid var(--rule)}
.no b{display:block;font:800 40px/1 var(--display)}
.tag{display:inline-block;margin-top:8px;padding:2px 6px;border:1px solid currentColor;
font:600 9.5px/1.5 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--steel)}
.tag.alt,.tag.open{color:var(--oxide)}
.asked{margin:0 0 10px;color:var(--steel);font-style:italic}
.asked span,.opt{font:600 10px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;font-style:normal}
.asked span{display:block;margin-bottom:3px}
.opt{display:inline-block;background:var(--ink);color:var(--sheet);padding:4px 8px;margin-bottom:6px}
.item{font-weight:600}
.sku{font:400 12px/1.6 var(--mono);color:var(--steel)}
.facts{list-style:none;margin:8px 0 0;padding:0;font-size:13px;color:#33393f}
.facts li{padding-left:16px;position:relative}
.facts li::before{content:"";position:absolute;left:0;top:.62em;width:8px;height:2px;background:var(--steel)}
.facts .not_met::before,.facts .unknown::before{background:var(--oxide);height:8px;top:.4em;width:2px;left:3px}
.facts .not_met,.facts .unknown{color:var(--oxide)}
tr.extra td{background:#faf6ec;padding:10px 14px 12px 24px;border-left:4px solid var(--oxide);font-size:13.5px}
tr.extra p{margin:2px 0}
tr.extra b{font:600 10px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;margin-right:8px}
.total{display:flex;justify-content:flex-end;align-items:baseline;gap:24px;margin-top:0;padding:16px 10px;
border-bottom:3px solid var(--ink)}
.total span{font:600 11px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--steel);
max-width:420px;text-align:right}
.total strong{font:800 44px/1 var(--display);letter-spacing:.02em}
ol.open{list-style:none;margin:0;padding:0}
ol.open li{display:grid;grid-template-columns:92px 1fr;border-bottom:1px solid var(--rule);padding:14px 0}
ol.open b{font:800 40px/1 var(--display);padding-left:10px}
ol.open p{margin:0 0 4px}
ol.open .asked{margin:0 0 6px}
ul.terms{margin:0;padding-left:18px}
footer{padding:20px 40px 28px;border-top:1px solid var(--rule);color:var(--steel);font-size:13px}
.notice{margin-top:14px;padding:10px 14px;border:1px dashed var(--steel);font:400 12px/1.6 var(--mono)}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@keyframes thunk{from{opacity:0;transform:rotate(-4deg) scale(1.8)}to{opacity:.9;transform:rotate(-4deg) scale(1)}}
@media (max-width:760px){header{grid-template-columns:1fr;padding:24px 20px}main,footer{padding-left:20px;padding-right:20px}
h1{font-size:46px}
table,tbody,tr,td{display:block}thead{display:none}td{border-bottom:0;padding:6px 0}tr{border-bottom:1px solid var(--rule);padding:10px 0}
.no{width:auto;border-right:0}td.num{text-align:left}}
@media print{@page{margin:14mm}body{background:#fff;padding:0;font-size:11.5pt}
.sheet{border:0;box-shadow:none;max-width:none}*{animation:none!important}
header,main,footer{padding-left:0;padding-right:0}tr,ol.open li{break-inside:avoid}h2{break-after:avoid}
.band,.opt{-webkit-print-color-adjust:exact;print-color-adjust:exact}tr.extra td{background:none}}
"""
TAG_CLASS = {"quoted_with_alternates": "alt", "needs_buyer_input": "open"}


def _offer_cells(line: BuyerLine, offer: BuyerOffer, first: bool) -> str:
    """One offer as a table row; the line number and the buyer's wording sit on the first."""
    span = len(line.offers)
    no = (f'<td rowspan="{span}" class="no"><b>{escape(line.buyer_line_no)}</b>'
          f'<span class="tag {TAG_CLASS.get(line.status, "")}">{STATUS_LABEL[line.status]}</span></td>'
          ) if first else ""
    asked = f'<p class="asked"><span>Requested</span>{escape(line.text)}</p>' if first else ""
    option = f'<span class="opt">{escape(offer.label)}</span><br>' if span > 1 else ""
    facts = [f"<li>{escape(availability_text(offer.availability, offer.quantity_unit))}</li>"]
    facts += [f'<li class="{c.result}">{escape(c.requirement)}: {c.result.replace("_", " ")}. '
              f"{escape(c.evidence)}</li>" for c in offer.compliance]
    price = offer.price
    money = (f'<td class="num">{_money(price.unit_price)} / {UNIT[price.unit]}</td>'
             f'<td class="num"><strong>{_money(price.extended)}</strong></td>'
             ) if price else '<td class="num"></td><td class="num"></td>'
    return (f"<tr>{no}<td>{asked}{option}<span class=\"item\">{escape(offer.description or '')}"
            f"</span><br><span class=\"sku\">{escape(offer.sku or '')}</span>"
            f"<ul class=\"facts\">{''.join(facts)}</ul></td>"
            f"<td class=\"num\">{_qty(offer.quantity)} {UNIT.get(offer.quantity_unit or '', '')}</td>"
            f"{money}</tr>")


def quote_html(run: Run) -> str:
    quote = buyer_view(run)
    draft = quote.quote_status not in ("approved", "sent")
    priced = [l for l in quote.lines if l.status in PRICED_STATUSES]
    pending = [l for l in quote.lines if l.status == "needs_buyer_input"]
    declined = [l for l in quote.lines if l.status == "no_bid"]
    until = valid_until(quote)

    rows = []
    for line in priced:
        rows += [_offer_cells(line, offer, n == 0) for n, offer in enumerate(line.offers)]
        extra = [f"<p><b>Assumed</b>{escape(a)}</p>" for a in line.assumptions]
        if line.question:
            extra.append(f"<p><b>Question</b>{escape(line.question.text)}</p>")
        if extra:
            rows.append(f'<tr class="extra"><td colspan="5">{"".join(extra)}</td></tr>')

    meta = [("Prepared for:", quote.customer), ("Date:", quote.created[:10]),
            ("Prices valid until:", until), ("Status:", "Draft" if draft else "Approved")]
    stamp = ('<div class="stamp">DRAFT<small>not approved. Do not send.</small></div>'
             if draft else "")
    partial = " &middot; Partial quote: some lines are still open." \
        if quote.completeness == "partial" else ""
    out = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Quote {escape(quote.rfq_id)}</title><style>{QUOTE_CSS}</style></head>"
        f'<body class="{"draft" if draft else "approved"}"><div class="sheet"><div class="band"></div>'
        '<header><div><span class="kicker">Metals quotation</span>'
        f'<h1>Quote <span class="id">{escape(quote.rfq_id)}</span></h1>'
        f'<p class="rev">revision {quote.revision}{partial}</p>{stamp}</div><dl class="meta">'
        + "".join(f"<div><dt>{k}</dt><dd>{escape(v)}</dd></div>" for k, v in meta if v) + "</dl>",
        "</header><main>",
    ]
    if rows:
        alternates = any(len(l.offers) > 1 for l in priced)
        out.append(
            '<h2>Priced lines</h2><table><thead><tr><th>Line</th><th>Item</th>'
            '<th class="num">Quantity</th><th class="num">Unit price</th>'
            '<th class="num">Extended</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>"
            '<p class="total"><span>Total of single-option lines'
            + (". Lines with alternates are not included." if alternates else "")
            + f"</span><strong>{_money(quote.total)}</strong></p>")
    if pending:
        out.append('<h2>Awaiting your answer</h2><ol class="open">' + "".join(
            f"<li><b>{escape(l.buyer_line_no)}</b><div><p class=\"asked\"><span>Requested</span>"
            f"{escape(l.text)}</p><p>{escape(l.question.text if l.question else '')}</p></div></li>"
            for l in pending) + "</ol>")
    if declined:
        out.append('<h2>Not quoted</h2><ol class="open">' + "".join(
            f"<li><b>{escape(l.buyer_line_no)}</b><div><p class=\"asked\"><span>Requested</span>"
            f"{escape(l.text)}</p><p>{escape(l.reason or '')}</p></div></li>"
            for l in declined) + "</ol>")
    if quote.terms:
        out.append('<h2>Requirements applied to all lines</h2><ul class="terms">'
                   + "".join(f"<li>{escape(t)}</li>" for t in quote.terms) + "</ul>")
    out.append("</main><footer>Prices are in US dollars and exclude freight and taxes. "
               "Availability is as of the quote date and subject to prior sale."
               f'<p class="notice">{SYNTHETIC}</p></footer></div></body></html>')
    return "".join(out)


def visible_text(html: str) -> str:
    """The text a reader sees in an HTML page: no styles, no tags."""
    text = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def email_text(run: Run) -> str:
    quote = buyer_view(run)
    items = [l for l in quote.lines if l.status != "not_an_item"]
    priced = [l for l in items if l.status in PRICED_STATUSES]
    declined = [l for l in items if l.status == "no_bid"]
    held = sum(1 for l in run.lines if l.status == "needs_specialist_review")
    questions = email_questions(run)
    plural = "s" if len(questions) != 1 else ""
    subject = f"Quote {quote.rfq_id}" + (f": {len(questions)} question{plural}" if questions else "")
    out = [f"Subject: {subject}", "", "Hello,", "",
           f"Thank you for your request. Quote {quote.rfq_id} is attached, with "
           f"{len(priced)} of {len(items) + held} lines priced."]
    if questions:
        out += ["", "To complete it we need your answer on the following:", ""]
        for n, (line_no, q) in enumerate(questions, start=1):
            named = f"line {line_no}".lower() in q.text.lower()
            text = q.text if named else f"Line {line_no}: {q.text}"
            out.append(f"{n}. {text}" + ("" if q.blocking else " (This line is already priced.)"))
    if declined:
        out += ["", "We are unable to quote:"]
        out += [f"- Line {l.buyer_line_no}: {l.reason}" for l in declined]
    if held:
        out += ["", f"{held} line{'s' if held != 1 else ''} will follow separately."]
    until = valid_until(quote)
    if until:
        out += ["", f"Prices are valid until {until}."]
    out += ["", "Regards,"]
    return "\n".join(out)


def internal_summary(run: Run) -> str:
    """For the specialist only: what needs their judgment. Never sent to the buyer."""
    out = [f"Internal summary for {run.rfq_id} (not for the buyer)", "",
           "Lines by status: " + ", ".join(f"{STATUS_LABEL[s]} {n}" for s, n in run.counts.items())]
    review = [l for l in run.lines if l.status == "needs_specialist_review"]
    if review:
        out += ["", "Needs specialist review:"]
        out += [f"- Line {l.buyer_line_no}: {l.segment.text}\n  {l.review_note or ''}" for l in review]
    noted = [l for l in run.lines if l.review_note and l.status != "needs_specialist_review"]
    if noted:
        out += ["", "Notes on other lines:"]
        out += [f"- Line {l.buyer_line_no}: {l.review_note}" for l in noted]
    if run.withheld:
        out += ["", "Withheld from processing:"]
        out += [f"- \"{w.text}\" ({w.reason})" for w in run.withheld]
    if run.leak_check and not run.leak_check.passed:
        out += ["", "LEAK CHECK FAILED. Approval is blocked:"] + [f"- {h}" for h in run.leak_check.hits]
    return "\n".join(out)
