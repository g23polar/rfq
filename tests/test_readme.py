"""The README states rules a reader may check against the product; keep it in step with the code."""
from pathlib import Path

from rfq.decide import STATUS_RULES
from rfq.reference import load_reference

README = (Path(__file__).parent.parent / "README.md").read_text()


def test_status_table_matches_the_rules_in_order():
    for rule in STATUS_RULES:
        label = rule.status.replace("_", " ").capitalize()
        assert f"| {rule.order} | **{label}** |" in README, rule
    numbered = [l for l in README.splitlines() if l.startswith("| ") and l.split("|")[1].strip().isdigit()]
    assert len(numbered) == len(STATUS_RULES)


def test_pricing_values_match_the_rules_file():
    pricing = load_reference().rules.pricing
    below = round((1 - pricing.target_multiplier_of_benchmark_mid) * 100)
    assert f"less {below}%" in README
    assert f"margin floor is {pricing.margin_floor_pct:g}%" in README
    assert f"valid for {pricing.validity_days} days" in README


def test_gauge_examples_match_the_reference_table():
    gauges = load_reference().tables.gauge_sheet_in
    for material in ("stainless", "carbon", "aluminum"):
        assert f"{gauges[material]['16']:.4f} in" in README


def test_bundled_files_the_readme_points_to_exist():
    root = Path(__file__).parent.parent
    for path in ("docs/quote-sample.png", "fixtures/rfq_email.txt", "fixtures/golden.jsonl", "spec.md"):
        assert f"({path})" in README and (root / path).exists(), path
