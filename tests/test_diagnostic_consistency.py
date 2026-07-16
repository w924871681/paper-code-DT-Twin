from __future__ import annotations
import csv
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def _rows(path: Path):
    with path.open("r",encoding="utf-8-sig",newline="") as handle: return list(csv.DictReader(handle))


def test_retained_reference_cases_are_neutral() -> None:
    row=next(r for r in _rows(ROOT/"results/robustness/architecture_coverage.csv") if r["Dataset"]=="C33Locked980-999" and r["ArchIdx"]=="57")
    assert (int(row["SelectedCount"]),int(row["SelectedBeneficialCount"]),int(row["SelectedHarmfulCount"]))==(33,0,0)


def test_alibaba_v2_diagnostic_counts() -> None:
    values={r["Measure"]:float(r["Value"]) for r in _rows(ROOT/"results/robustness/alibaba_oracle_diagnostics.csv")}
    assert values["Mean captured oracle headroom"]==0.654228491766997
    assert int(values["Beneficial selected cases"])==39 and int(values["Harmful selected cases"])==5
