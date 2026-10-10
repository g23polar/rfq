import importlib.util
from pathlib import Path

import pytest

from rfq.reference import DATA_DIR, SYNTHETIC_LABEL, ReferenceData, load_reference

ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="module")
def ref() -> ReferenceData:
    return load_reference()


@pytest.fixture(scope="module")
def kb(ref) -> str:
    spec = importlib.util.spec_from_file_location("export_kb", ROOT / "scripts" / "export_kb.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build(ref)


def target_margin_pct(ref, item):
    target = ref.benchmark_for(item.grade, item.form).mid * \
        ref.rules.pricing.target_multiplier_of_benchmark_mid
    return (target - item.cost_per_lb) / target * 100


def test_tables_load_and_are_consistent(ref):
    assert 55 <= len(ref.catalog) <= 70
    assert len({i.sku for i in ref.catalog}) == len(ref.catalog)
    assert all(ref.item(x.sku) for x in ref.cross_references)
    assert all(b.source == "synthetic" for b in ref.benchmarks.values())


def test_every_catalog_grade_and_form_has_a_benchmark_and_default_standard(ref):
    for item in ref.catalog:
        assert ref.benchmark_for(item.grade, item.form), item.sku
        assert ref.default_standard(item.grade, item.form), item.sku


def test_grade_family(ref):
    assert ref.grade_family("304/304L") == ref.grade_family("304l") == "304"
    assert ref.grade_family("6061") == "6061-T6"
    assert ref.grade_family("C276") is None


def test_cross_reference_is_scoped_by_customer(ref):
    assert ref.lookup_part("Acme Fabrication", "88213").sku == "SS-304L-RB-1000-144"
    assert ref.lookup_part("Acme Fabrication Inc.", "ACME-PN 88213").sku == "SS-304L-RB-1000-144"
    assert ref.lookup_part("Brightline Manufacturing", "88213").sku == "CS-1018-RB-1000-144"
    assert ref.lookup_part("Brightline Manufacturing", "AF-7720") is None
    assert ref.lookup_part("Acme Fabrication", "188213") is None


def test_seeded_cases_exist(ref):
    sheets = {i.grade for i in ref.catalog
              if i.form == "sheet" and i.thickness_in == 0.0625 and (i.width_in, i.length_in) == (48, 96)}
    assert sheets == {"304/304L", "316/316L"}  # M1 alternates, L1 target

    tie = [i for i in ref.catalog if i.grade == "304/304L" and i.form == "sheet"
           and i.thickness_in == 0.125 and (i.width_in, i.length_in) == (48, 120)]
    assert len(tie) == 2 and tie[0].finish != tie[1].finish  # X3

    qualifying = ref.rules.dfars.qualifying_countries
    p2 = [i for i in ref.catalog if i.country_of_melt not in qualifying and i.grade == "316/316L"
          and i.form == "round_bar"]
    assert len(p2) == 1
    twins = [i for i in ref.catalog if i.grade == p2[0].grade and i.form == p2[0].form
             and i.diameter_in == p2[0].diameter_in]
    assert twins == p2  # no compliant equivalent

    assert any(i.mtr_available == "unknown" for i in ref.catalog)  # P5
    assert ref.item("SS-304L-PLT-2500-48X96").stock_qty < 8  # Q4

    floor = ref.rules.pricing.margin_floor_pct
    below = [i.sku for i in ref.catalog if target_margin_pct(ref, i) < floor]
    assert below == ["SS-316L-PLT-2500-48X96"]  # PR-2, and nothing else by accident


def test_every_file_is_labeled_synthetic(kb):
    for path in DATA_DIR.iterdir():
        assert SYNTHETIC_LABEL in path.read_text(), path.name
    assert SYNTHETIC_LABEL in kb


def test_knowledge_base_states_groundable_facts(kb):
    assert "- 16 gauge stainless steel sheet is 0.0625 in thick." in kb
    assert "- The default standard for 304 sheet is ASTM A240." in kb
    assert "cost" not in kb.lower() and "Northbridge" not in kb
