"""Question wording (plans/12-decide-and-verify.md).

`reword` asks the fast model to put a template question into natural language, then checks
the result. If the check fails or the model call fails, the template is returned unchanged.
Options are never reworded.
"""

import re

from pydantic import BaseModel

from rfq.llm import MODEL_FAST, ModelCallError, call_json
from rfq.models import Question
from rfq.reference import load_reference

COMMITMENT_WORDS = ("we will", "we'll", "we shall", "guarantee", "promise", "commit", "assure")
INTERNAL_TERMS = ("cost", "costs", "margin", "margins", "floor", "markup", "supplier",
                  "suppliers", "vendor", "vendors")
MONTHS = ("january", "february", "march", "april", "june", "july", "august", "september",
          "october", "november", "december")  # "may" is left out: it is also a verb
CURRENCY = re.compile(r"[$€£]|\b(?:usd|dollars?|cents?)\b", re.I)
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?|\.\d+")

SYSTEM = (
    "You reword a short question that a metals distributor sends to a buyer about one line of "
    "their request for quote. Make it read naturally, in one to three polite sentences. Keep "
    "the meaning, the line reference and every option exactly as given. Do not add any number, "
    "date, price or amount. Do not promise or commit to anything. Do not mention costs, "
    "margins, floors, suppliers or anything about our internal pricing."
)


class Reworded(BaseModel):
    text: str


def _numbers(text: str) -> set[float]:
    return {float(n.replace(",", "")) for n in NUMBER.findall(text)}


def _words(text: str, words: tuple[str, ...]) -> list[str]:
    low = text.lower()
    return [w for w in words if re.search(rf"(?<![a-z']){re.escape(w)}(?![a-z])", low)]


def supplier_names() -> tuple[str, ...]:
    return tuple(sorted({i.supplier for i in load_reference().catalog if i.supplier}))


def check_rewording(template: str, reworded: str) -> list[str]:
    """Reasons the rewording is not acceptable; empty when it is."""
    problems = []
    if not reworded.strip():
        problems.append("empty")
    extra = _numbers(reworded) - _numbers(template)
    if extra:
        problems.append("new numbers: " + ", ".join(f"{n:g}" for n in sorted(extra)))
    if CURRENCY.search(reworded) and not CURRENCY.search(template):
        problems.append("currency amount")
    new_months = set(_words(reworded, MONTHS)) - set(_words(template, MONTHS))
    if new_months:
        problems.append("date: " + ", ".join(sorted(new_months)))
    if found := _words(reworded, COMMITMENT_WORDS):
        problems.append("commitment: " + ", ".join(found))
    low = reworded.lower()
    found = _words(reworded, INTERNAL_TERMS) + [s for s in supplier_names() if s.lower() in low]
    if found:
        problems.append("internal term: " + ", ".join(found))
    return problems


def reword(question: Question) -> Question:
    """The question with its text reworded by the model, or unchanged when the model fails
    or its wording does not pass `check_rewording`."""
    user = f"Question:\n{question.text}"
    if question.options:
        user += "\nOptions (keep them in the wording): " + "; ".join(question.options)
    try:
        text = call_json(SYSTEM, user, Reworded, model=MODEL_FAST).value.text.strip()
    except ModelCallError:
        return question
    if check_rewording(question.text, text):
        return question
    return question.model_copy(update={"text": text})
