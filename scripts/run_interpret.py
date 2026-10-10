"""Interpret every line in fixtures/golden.jsonl and print the readings (plans/06-line-reading.md).

Run: uv run python scripts/run_interpret.py
Needs NICRRON_API_KEY in .env unless the responses are already cached. Accuracy here is
rough: only fields comparable as written (grade, quantity value) against expected.spec.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

from rfq.interpret import interpret_all
from rfq.models import Line, Segment, Sourced, Terms

load_dotenv(".env")

rows = [json.loads(l) for l in Path("fixtures/golden.jsonl").read_text().splitlines() if l.strip()]
lines, terms = [], []
for r in rows:
    terms.append(Terms(requirements=[Sourced(value=t, source_text=t, source="rfq_terms")
                                     for t in r.get("rfq_requirements") or []]))
    no = r["buyer_line_no"] or r["id"]
    # Golden PDF rows keep the line number; intake's segment text leaves it out.
    text = r["text"].removeprefix(f"{no} ") if (r.get("fixture") or "").endswith(".pdf") else r["text"]
    lines.append(Line(buyer_line_no=no, segment=Segment(buyer_line_no=no, text=text,
                                                        kind=r["kind"])))

# Golden lines come from several RFQs, so group them by their terms and run each group
# through the concurrent helper at the same time.
started = time.monotonic()
groups: dict[str, list[int]] = {}
for i, t in enumerate(terms):
    groups.setdefault(t.model_dump_json(), []).append(i)
out: list[Line] = [None] * len(lines)  # type: ignore[list-item]
with ThreadPoolExecutor(max_workers=len(groups)) as pool:
    jobs = {pool.submit(interpret_all, [lines[i] for i in idx], terms[idx[0]]): idx
            for idx in groups.values()}
    for job, idx in jobs.items():
        for i, line in zip(idx, job.result()):
            out[i] = line
elapsed = time.monotonic() - started


def short(s: Sourced) -> str:
    return f"{s.value}{s.unit or ''}" + ("" if s.source == "rfq_line" else "[terms]")


score = {"grade": [0, 0], "quantity": [0, 0]}
for row, line in zip(rows, out):
    print(f"== {row['id']}: {row['text']}")
    if line.reading is None:
        print(f"   no reading; issues: {[i.kind for i in line.issues]}")
        continue
    r = line.reading
    fields = {k: v for k, v in r if k not in ("discarded",) and v}
    print("   " + "; ".join(f"{k}=" + (", ".join(short(s) for s in v) if isinstance(v, list)
                                       else short(v)) for k, v in fields.items()))
    for d in r.discarded:
        print(f"   DISCARDED {d.field}={d.value!r} quote={d.source_text!r}: {d.reason}")
    if row["kind"] != "item":
        continue
    spec = row["expected"]["spec"]
    want = {"grade": spec.get("grade"), "quantity": spec.get("quantity")}
    got = {"grade": r.grade and str(r.grade.value),
           "quantity": r.quantity and str(r.quantity.value).replace(",", "")}
    for k in score:
        w = None if want[k] is None else str(want[k]).replace(".0", "")
        ok = (got[k] or None) == w or (w is not None and got[k] is not None
                                       and got[k].upper() == w.upper())
        score[k][0] += ok
        score[k][1] += 1
        if not ok:
            print(f"   MISMATCH {k}: got {got[k]!r}, expected {w!r}")

print(f"\n{len(out)} lines in {elapsed:.1f} s")
for k, (ok, n) in score.items():
    print(f"{k}: {ok}/{n} match as written")
print(f"discarded fields: {sum(len(l.reading.discarded) for l in out if l.reading)}; "
      f"model_failed: {sum(1 for l in out if any(i.kind == 'model_failed' for i in l.issues))}")
