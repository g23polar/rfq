"""Reference data: catalog, cross-references, benchmarks, reference tables and rules
(plans/02-reference-data-and-catalog.md).

All of it is synthetic demo data. Load everything once with `load_reference()`; stages
read it from their context. Row shapes for the catalog, cross-references and rules live
here; benchmarks load into the `Benchmark` shape from `models`.

Keys used throughout:
- grade family: the grade a benchmark and a default standard are keyed by. Dual-certified
  "304/304L" and a request for "304L" are both family "304"; "6061" is family "6061-T6".
- form family: sheet, plate, bar, tube or pipe. `round_bar` and `flat_bar` are both "bar".
"""

import csv
import json
import re
from functools import cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from rfq.models import Benchmark

DATA_DIR = Path(__file__).parent / "data"
SYNTHETIC_LABEL = "SYNTHETIC DEMO DATA"

Material = Literal["stainless", "carbon", "aluminum"]
Form = Literal["sheet", "plate", "round_bar", "flat_bar", "round_tube", "square_tube", "pipe"]
FormFamily = Literal["sheet", "plate", "bar", "tube", "pipe"]


class _CsvRow(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _blank_is_none(cls, data):
        if isinstance(data, dict):
            return {k: (None if v == "" else v) for k, v in data.items()}
        return data


class CatalogItem(_CsvRow):
    sku: str
    description: str
    material: Material
    grade: str  # dual-certified stock is written "304/304L"
    form: Form
    thickness_in: float | None = None  # sheet, plate, flat bar
    width_in: float | None = None  # sheet, plate, flat bar; outside size for square tube
    length_in: float
    diameter_in: float | None = None  # bar diameter; tube and pipe outside diameter
    wall_in: float | None = None
    nps: str | None = None  # pipe nominal size, e.g. "2"
    schedule: str | None = None  # pipe schedule, e.g. "40S"
    standard: str
    certifications: list[str] = Field(default_factory=list)
    finish: str | None = None
    cost_per_lb: float  # internal
    stock_qty: int  # pieces
    lead_time_days: int
    country_of_melt: str  # ISO 3166 alpha-2
    mtr_available: Literal["yes", "no", "unknown"]
    supplier: str  # internal

    @field_validator("certifications", mode="before")
    @classmethod
    def _split(cls, v):
        return [c.strip() for c in v.split(";") if c.strip()] if isinstance(v, str) else v or []

    @property
    def dual_certified(self) -> bool:
        return "/" in self.grade


class CrossReference(_CsvRow):
    customer: str
    customer_part_no: str
    sku: str


class BenchmarkRow(_CsvRow):
    grade: str  # grade family
    form_family: FormFamily
    low: float
    mid: float
    high: float
    source: str
    as_of: str

    def benchmark(self) -> Benchmark:
        return Benchmark(low=self.low, mid=self.mid, high=self.high, source=self.source,
                         as_of=self.as_of)


class Surcharge(_CsvRow):
    grade: str  # grade family
    month: str  # YYYY-MM
    surcharge_per_lb: float
    source: str


class QuantityBreak(BaseModel):
    min_qty: float
    discount_pct: float


class PricingRules(BaseModel):
    target_multiplier_of_benchmark_mid: float
    margin_floor_pct: float
    validity_days: int
    stale_benchmark_days: int
    minimum_order_charge: float  # stretch
    cutting_charge_per_cut: float  # stretch
    quantity_breaks: list[QuantityBreak]  # stretch


class DfarsRules(BaseModel):
    basis: Literal["country_of_melt"]
    qualifying_countries: list[str]


class Rules(BaseModel):
    label: str = Field(alias="_label")
    pricing: PricingRules
    dfars: DfarsRules


class Abbreviation(BaseModel):
    field: str
    value: str
    means: str
    finish: str | None = None


class GradeInfo(BaseModel):
    material: Material
    variants: list[str]


class DualCertification(BaseModel):
    fills: list[str]
    does_not_fill: list[str]


class Substitution(BaseModel):
    from_: str = Field(alias="from")
    to: str
    note: str


class PipeSize(BaseModel):
    od_in: float
    wall_in: dict[str, float]  # by schedule


class ThicknessTolerance(BaseModel):
    abs_in: float
    pct: float


class ReferenceTables(BaseModel):
    label: str = Field(alias="_label")
    materials: list[Material]
    density_lb_per_in3: dict[Material, float]
    gauge_sheet_in: dict[Material, dict[str, float]]
    gauge_tube_wall_in: dict[str, float]
    standard_thickness_in: dict[Material, list[float]]
    thickness_tolerance: ThicknessTolerance
    plate_min_thickness_in: dict[Material, float]
    forms: dict[Form, FormFamily]
    abbreviations: dict[str, Abbreviation]
    grades: dict[str, GradeInfo]  # keyed by grade family
    dual_certified: dict[str, DualCertification]
    common_grades: dict[Material, dict[FormFamily, list[str]]]
    default_standard: dict[str, dict[FormFamily, str]]  # grade family -> form family -> standard
    substitutions: list[Substitution]
    standard_sheet_sizes_in: list[tuple[float, float]]
    standard_plate_sizes_in: list[tuple[float, float]]
    pipe_sizes: dict[str, PipeSize]


def _norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _norm_customer(name: str) -> str:
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()
    return " ".join(w for w in words if w not in {"inc", "llc", "co", "corp", "corporation",
                                                  "company", "ltd"})


class ReferenceData(BaseModel):
    catalog: list[CatalogItem]
    cross_references: list[CrossReference]
    benchmarks: dict[tuple[str, str], Benchmark]  # (grade family, form family)
    surcharges: list[Surcharge]
    tables: ReferenceTables
    rules: Rules

    def item(self, sku: str) -> CatalogItem | None:
        return next((i for i in self.catalog if i.sku == sku), None)

    def grade_family(self, grade: str) -> str | None:
        """'304/304L', '304L' and '304' are all '304'. None for a grade we don't know."""
        wanted = _norm(grade)
        for family, info in self.tables.grades.items():
            if any(_norm(v) == wanted for v in [family, *info.variants]):
                return family
        if "/" in grade:
            return self.grade_family(grade.split("/")[0])
        return None

    def form_family(self, form: str) -> FormFamily | None:
        return self.tables.forms.get(form)  # type: ignore[call-overload]

    def benchmark_for(self, grade: str, form: str) -> Benchmark | None:
        family, ff = self.grade_family(grade), self.form_family(form)
        return self.benchmarks.get((family, ff)) if family and ff else None

    def default_standard(self, grade: str, form: str) -> str | None:
        family, ff = self.grade_family(grade), self.form_family(form)
        return self.tables.default_standard.get(family, {}).get(ff) if family and ff else None

    def lookup_part(self, customer: str, part_no: str) -> CrossReference | None:
        """Resolve a customer part number for that customer only (NF-5).

        Matching ignores case and punctuation, and accepts a customer prefix in front of
        the stored number ("ACME-PN 88213" finds "88213")."""
        cust, wanted = _norm_customer(customer), _norm(part_no)
        for ref in self.cross_references:
            if _norm_customer(ref.customer) != cust:
                continue
            stored = _norm(ref.customer_part_no)
            if wanted == stored or (wanted.endswith(stored) and len(wanted) > len(stored)
                                    and wanted[-len(stored) - 1].isalpha()):
                return ref
        return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    lines = [l for l in path.read_text().splitlines() if l.strip() and not l.startswith("#")]
    return list(csv.DictReader(lines))


@cache
def load_reference(data_dir: Path = DATA_DIR) -> ReferenceData:
    benchmarks = {}
    for row in _read_csv(data_dir / "benchmarks.csv"):
        b = BenchmarkRow.model_validate(row)
        benchmarks[(b.grade, b.form_family)] = b.benchmark()
    return ReferenceData(
        catalog=[CatalogItem.model_validate(r) for r in _read_csv(data_dir / "catalog.csv")],
        cross_references=[CrossReference.model_validate(r)
                          for r in _read_csv(data_dir / "cross_reference.csv")],
        benchmarks=benchmarks,
        surcharges=[Surcharge.model_validate(r) for r in _read_csv(data_dir / "surcharges.csv")],
        tables=ReferenceTables.model_validate(json.loads((data_dir / "reference.json").read_text())),
        rules=Rules.model_validate(json.loads((data_dir / "rules.json").read_text())),
    )
