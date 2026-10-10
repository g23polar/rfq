"""Stage 9, decide: one status per line from its issue list, plus the buyer question and the
internal review note (plans/12-decide-and-verify.md).

Statuses come from fixed rules, first match wins (`STATUS_RULES`). Questions come from a
fixed template per issue kind; `rfq.questions.reword` may later put them in natural words.
Internal issues never produce a question.
"""

from typing import NamedTuple

from rfq.context import Context
from rfq.models import PRICED_STATUSES, Issue, Line, LineStatus, Question, Run

REVIEW_KINDS = ("below_floor", "weak_match", "paths_disagree", "withheld_text", "unconfirmed",
                "verification_failed", "model_failed")
NOTE_ONLY_KINDS = ("price_out_of_range", "stale_benchmark")  # review note, status unchanged
NO_BID_KINDS = ("no_match", "unmet_requirement")
BLOCKING_KINDS = ("missing", "conflict", "missing_attachment")
ALTERNATE_KINDS = ("ambiguous_options", "tie", "substitution")
ASSUMPTION_KINDS = ("assumption", "open_question")
# Buyer-facing kinds that need an answer, most important first. Their question is built
# from the first; the rest follow in the same text.
QUESTION_KINDS = ("conflict", "missing", "missing_attachment", "ambiguous_options", "tie",
                  "substitution", "open_question")


class StatusRule(NamedTuple):
    order: int
    status: LineStatus
    kinds: tuple[str, ...]
    condition: str


STATUS_RULES: tuple[StatusRule, ...] = (
    StatusRule(1, "not_an_item", (), "Segment kind is not item"),
    StatusRule(2, "needs_specialist_review", REVIEW_KINDS, "Any internal review issue"),
    StatusRule(3, "no_bid", NO_BID_KINDS,
               "no_match or unmet_requirement; or no offers and no buyer-blocking issue"),
    StatusRule(4, "needs_buyer_input", BLOCKING_KINDS + ALTERNATE_KINDS + ("open_question",),
               "missing, conflict or missing_attachment; or an ambiguous_options, tie, "
               "substitution or open_question item with no priced offer"),
    StatusRule(5, "quoted_with_alternates", ALTERNATE_KINDS,
               "ambiguous_options, tie or substitution, with at least one priced offer"),
    StatusRule(6, "quoted_with_assumptions", ASSUMPTION_KINDS,
               "assumption or open_question only, with a priced offer"),
    StatusRule(7, "quoted", (), "No issues (price_out_of_range and stale_benchmark ignored), "
                                "with a priced offer"),
    StatusRule(8, "needs_specialist_review", (),
               "Fallback: offers exist but none is priced"),
)

_KIND_ORDER = {kind: n for n, kind in enumerate(QUESTION_KINDS)}


def _kinds(line: Line) -> set[str]:
    return {i.kind for i in line.issues}


def _priced(line: Line) -> bool:
    return any(o.price for o in line.offers)


def _blocks(line: Line, kinds: set[str]) -> bool:
    """The line cannot be priced until the buyer answers."""
    if kinds & set(BLOCKING_KINDS):
        return True
    return not _priced(line) and bool(kinds & set(ALTERNATE_KINDS + ("open_question",)))


def assign_status(line: Line) -> LineStatus:
    """Apply `STATUS_RULES` to the line's segment, issues and offers."""
    kinds = _kinds(line)
    if line.segment.kind != "item":
        return "not_an_item"
    if kinds & set(REVIEW_KINDS):
        return "needs_specialist_review"
    if kinds & set(NO_BID_KINDS) or (not line.offers and not _blocks(line, kinds)):
        return "no_bid"
    if _blocks(line, kinds):
        return "needs_buyer_input"
    if not _priced(line):
        return "needs_specialist_review"
    if kinds & set(ALTERNATE_KINDS):
        return "quoted_with_alternates"
    if kinds & set(ASSUMPTION_KINDS):
        return "quoted_with_assumptions"
    return "quoted"


def _sentence(text: str) -> str:
    text = " ".join(text.split())
    return text if not text or text[-1] in ".?!" else text + "."


def _ask(issue: Issue, priced: bool) -> str:
    """The fixed template for one issue kind."""
    if issue.kind == "missing":
        return "Please provide the missing detail."
    if issue.kind == "conflict":
        return "Please confirm which is correct."
    if issue.kind == "missing_attachment":
        return "Please send the attachment."
    if issue.kind in ("ambiguous_options", "tie"):
        return ("Which would you like? Each option is priced in the quote." if priced
                else "Which would you like?")
    if issue.kind == "substitution":
        return "Is this substitution acceptable?"
    return "Please confirm."  # open_question


def build_question(line: Line) -> Question | None:
    """One question for the line, from its buyer-facing open items; None when there are none."""
    items = sorted((i for i in line.issues if i.audience == "buyer" and i.kind in QUESTION_KINDS),
                   key=lambda i: _KIND_ORDER[i.kind])
    if not items:
        return None
    priced = line.status in PRICED_STATUSES
    parts = [f"{_sentence(i.message)} {_ask(i, priced)}" for i in items]
    options = items[0].options
    if options:
        parts[0] += " Options: " + ", ".join(options) + "."
    return Question(text=f"Line {line.buyer_line_no}: " + " ".join(parts), options=list(options),
                    blocking=not priced)


def _review_note(line: Line) -> str | None:
    wanted = REVIEW_KINDS + NOTE_ONLY_KINDS
    notes = [_sentence(i.message) for i in line.issues if i.kind in wanted]
    return " ".join(notes) or None


def decide(line: Line, ctx: Context) -> Line:
    """Set status, question and review note from the issue list alone."""
    line.status = assign_status(line)
    line.review_note = _review_note(line) if line.status != "not_an_item" else None
    asks = line.status in ("needs_buyer_input", "quoted_with_alternates",
                           "quoted_with_assumptions")
    line.question = build_question(line) if asks else None
    return line


def email_questions(run: Run) -> list[tuple[str, Question]]:
    """(line number, question) in email order: blocking questions first, then questions on
    lines that are already priced. Run order is kept within each group."""
    found = [(l.buyer_line_no, l.question) for l in run.lines if l.question]
    return ([f for f in found if f[1].blocking] + [f for f in found if not f[1].blocking])
