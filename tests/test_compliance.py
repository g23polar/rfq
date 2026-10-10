from datetime import date

import pytest

from rfq.compliance import check
from rfq.context import Context
from rfq.models import Candidate, Line, Offer, Reading, Segment, Sourced, Spec, Terms
from rfq.reference import load_reference

SHEET_US = "SS-304L-SHT-0625-48X96"  # melt US, MTR yes, ASTM A240, dual 304/304L
SHEET_CA = "SS-304L-SHT-1094-48X96"  # melt CA
BAR_IN = "SS-316L-RB-1500-144"  # melt IN, ASTM A276
BAR_US = "SS-304L-RB-1500-144"
A36_UNKNOWN_MTR = "CS-A36-PLT-3750-48X96"  # mtr unknown, melt US
TUBE_NO_MTR = "SS-304L-ST-1000X065-240"  # mtr no, melt KR


def req(text, label=None):
    return Sourced(value=label or text, source_text=text)


def make_line(skus, line_reqs=()):
    offers = [Offer(label=f"Option {i}", spec=Spec(),
                    candidate=Candidate(sku=s, description=s, strength=1.0))
              for i, s in enumerate(skus)]
    return Line(buyer_line_no="1", segment=Segment(buyer_line_no="1", text="x"),
                reading=Reading(requirements=list(line_reqs)), offers=offers)


def make_ctx(*rfq_reqs, ref=None):
    return Context(terms=Terms(requirements=list(rfq_reqs)), ref=ref or load_reference(),
                   today=date(2026, 10, 10))


def results(line, i=0):
    return {r.requirement: r for r in line.offers[i].compliance}


def kinds(line):
    return [i.kind for i in line.issues]


def test_no_offers_returns_line_untouched():
    line = make_line([])
    assert check(line, make_ctx(req("DFARS"))) is line
    assert line.issues == []


def test_offer_without_candidate_is_skipped():
    line = make_line([])
    line.offers.append(Offer(label="x", spec=Spec()))
    check(line, make_ctx(req("DFARS")))
    assert line.offers[0].compliance == [] and line.issues == []


def test_dfars_met_on_qualifying_melt():
    line = check(make_line([SHEET_CA]), make_ctx(req("All material DFARS compliant")))
    r = results(line)["DFARS"]
    assert r.result == "met" and r.scope == "rfq"
    assert r.evidence == "Country of melt: CA."
    assert r.source_text == "All material DFARS compliant"
    assert line.issues == []


def test_dfars_not_met_item_melted_in_india_is_no_bid_material():
    line = check(make_line([BAR_IN]), make_ctx(req("All material DFARS compliant")))
    r = results(line)["DFARS"]
    assert r.result == "not_met" and "IN" in r.evidence
    assert kinds(line) == ["unmet_requirement"]
    assert line.issues[0].audience == "buyer"


def test_unmet_not_raised_when_another_offer_is_compliant():
    line = check(make_line([BAR_IN, BAR_US]), make_ctx(req("DFARS compliant")))
    assert results(line, 0)["DFARS"].result == "not_met"
    assert results(line, 1)["DFARS"].result == "met"
    assert line.issues == []


def test_unmet_raised_when_every_offer_fails():
    line = check(make_line([BAR_IN, TUBE_NO_MTR]), make_ctx(req("DFARS compliant")))
    assert kinds(line) == ["unmet_requirement"]


def test_domestic_melt_and_manufacture_means_melt_country_us():
    text = "Melted and manufactured in USA"
    line = check(make_line([SHEET_US, SHEET_CA]), make_ctx(req(text)))
    assert results(line, 0)["Domestic melt"].result == "met"
    assert results(line, 1)["Domestic melt"].result == "not_met"
    assert line.issues == []


def test_domestic_melt_phrase():
    line = check(make_line([SHEET_US]), make_ctx(req("domestic melt required")))
    assert results(line)["Domestic melt"].result == "met"


def test_unqualified_domestic_is_unknown_with_question_and_stays_priced():
    line = check(make_line([SHEET_US]), make_ctx(req("Domestic material only")))
    r = results(line)["Domestic"]
    assert r.result == "unknown"
    assert kinds(line) == ["open_question"]
    assert line.issues[0].audience == "buyer"
    assert "melted" in line.issues[0].message and "manufactured" in line.issues[0].message
    assert "missing" not in kinds(line)


def test_unqualified_domestic_question_asked_once_for_several_offers():
    line = check(make_line([SHEET_US, SHEET_CA]), make_ctx(req("Domestic only")))
    assert kinds(line).count("open_question") == 1


def test_manufacture_only_is_unknown_and_unconfirmed():
    line = check(make_line([SHEET_US]), make_ctx(req("Manufactured in USA")))
    assert results(line)["Domestic manufacture"].result == "unknown"
    assert kinds(line) == ["unconfirmed"]


@pytest.mark.parametrize("text", ["MTRs required", "Mill certs please", "CMTR", "3.1 certs required",
                                  "EN 10204 3.1", "Mill test reports (MTRs) required for all items."])
def test_mtr_wording(text):
    line = check(make_line([SHEET_US]), make_ctx(req(text)))
    r = results(line)["Mill test report"]
    assert r.result == "met" and r.evidence == "Mill test report available."


def test_mtr_not_available_is_not_met():
    line = check(make_line([TUBE_NO_MTR]), make_ctx(req("3.1 certs required")))
    assert results(line)["Mill test report"].result == "not_met"
    assert kinds(line) == ["unmet_requirement"]


def test_mtr_unknown_is_never_met_and_goes_to_review():
    line = check(make_line([A36_UNKNOWN_MTR]), make_ctx(req("Mill test reports required")))
    r = results(line)["Mill test report"]
    assert r.result == "unknown"
    assert kinds(line) == ["unconfirmed"]
    assert line.issues[0].audience == "internal"


def test_unconfirmed_deduplicated_across_requirements_and_reruns():
    ctx = make_ctx(req("MTRs required"), req("Mill certs"))
    line = check(make_line([A36_UNKNOWN_MTR]), ctx)
    check(line, ctx)
    assert kinds(line) == ["unconfirmed"]
    assert len(line.offers[0].compliance) == 2  # one per source text; reruns replace


def test_specification_met_and_not_met():
    met = check(make_line([SHEET_US]), make_ctx(req("ASTM A240")))
    assert results(met)["Specification: ASTM A240"].result == "met"
    miss = check(make_line([A36_UNKNOWN_MTR]), make_ctx(req("304 sheet per ASTM A240")))
    assert results(miss)["Specification: ASTM A240"].result == "not_met"
    assert kinds(miss) == ["unmet_requirement"]


def test_specification_compare_ignores_case_space_and_hyphen():
    for text in ("per a240", "ASTM A-240", "ASME SA 240", "sa-240"):
        line = check(make_line([SHEET_US]), make_ctx(req(text)))
        (r,) = line.offers[0].compliance
        assert r.result == "met", text
    # SA-240 is a different requirement from A240: an item certified only to A36 does not meet it
    line = check(make_line([A36_UNKNOWN_MTR]), make_ctx(req("per A36")))
    assert line.offers[0].compliance[0].result == "met"


def test_specification_from_certifications_list():
    line = check(make_line([BAR_US]), make_ctx(req("ASTM A479")))
    assert line.offers[0].compliance[0].result == "met"


def test_specification_any_of():
    line = check(make_line([SHEET_US]), make_ctx(req("ASTM A240 or A276")))
    (r,) = line.offers[0].compliance
    assert r.result == "met" and r.requirement == "Specification: ASTM A240 or A276"


def test_dual_certification():
    ok = check(make_line([SHEET_US]), make_ctx(req("dual certified 304/304L")))
    assert results(ok)["Dual certification: 304/304L"].result == "met"
    bad = check(make_line([A36_UNKNOWN_MTR]), make_ctx(req("dual certification")))
    assert results(bad)["Dual certification"].result == "not_met"
    wrong = check(make_line([SHEET_US]), make_ctx(req("dual certified 316/316L")))
    assert results(wrong)["Dual certification: 316/316L"].result == "not_met"


def test_unrecognized_requirement_is_unknown_without_issue():
    line = check(make_line([SHEET_US]), make_ctx(req("Sour service per NACE MR0175", "NACE")))
    (r,) = line.offers[0].compliance
    assert r.requirement == "NACE" and r.result == "unknown"
    assert line.issues == []


def test_line_requirement_overrides_rfq_requirement():
    rfq = req("All material DFARS compliant")
    line_req = req("DFARS not required on this line.")
    line = check(make_line([BAR_IN], [line_req]), make_ctx(rfq))
    assert line.offers[0].compliance == []
    assert line.issues == []


def test_import_ok_waives_rfq_dfars():
    line = check(make_line([BAR_IN], [req("import OK for this line")]),
                 make_ctx(req("All material DFARS compliant")))
    assert line.offers[0].compliance == [] and line.issues == []


def test_override_scope_and_other_subjects_kept():
    ctx = make_ctx(req("DFARS compliant"), req("MTRs required"))
    line = check(make_line([BAR_IN], [req("Melted and manufactured in USA")]), ctx)
    r = results(line)
    assert "DFARS" not in r
    assert r["Domestic melt"].scope == "line" and r["Domestic melt"].result == "not_met"
    assert r["Mill test report"].scope == "rfq" and r["Mill test report"].result == "met"


def test_line_dfars_replaces_rfq_unqualified_domestic():
    line = check(make_line([SHEET_US], [req("DFARS required")]), make_ctx(req("Domestic only")))
    assert list(results(line)) == ["DFARS"]
    assert line.issues == []


def test_label_used_when_wording_says_nothing_but_wording_wins_otherwise():
    line = check(make_line([BAR_IN]), make_ctx(
        Sourced(value="DFARS", source_text="Foreign melt is acceptable, DFARS not required")))
    assert line.offers[0].compliance == []
    line = check(make_line([SHEET_US]), make_ctx(Sourced(value="MTR", source_text="send paperwork")))
    assert results(line)["Mill test report"].result == "met"


def test_missing_or_blank_country_is_unknown_and_unconfirmed():
    ref = load_reference()
    item = ref.item(SHEET_US).model_copy(update={"country_of_melt": ""})
    patched = ref.model_copy(update={"catalog": [item]})
    line = check(make_line([SHEET_US]), make_ctx(req("DFARS"), ref=patched))
    assert results(line)["DFARS"].result == "unknown"
    assert kinds(line) == ["unconfirmed"]


def test_unknown_sku_is_unknown_never_met():
    line = check(make_line(["NOPE"]), make_ctx(req("MTRs required")))
    assert line.offers[0].compliance[0].result == "unknown"
    assert kinds(line) == ["unconfirmed"]


def test_each_offer_judged_independently_and_evidence_has_no_internals():
    line = check(make_line([SHEET_US, BAR_IN]), make_ctx(req("DFARS"), req("MTR")))
    assert [r.result for r in line.offers[0].compliance] == ["met", "met"]
    assert [r.result for r in line.offers[1].compliance] == ["not_met", "met"]
    ref = load_reference()
    for offer in line.offers:
        suppliers = {ref.item(offer.candidate.sku).supplier}
        for r in offer.compliance:
            assert r.source_text and not any(s in r.evidence for s in suppliers)
    for i in line.issues:
        assert i.audience == "buyer"
