from __future__ import annotations
from pathlib import Path
from reporting.frozen import PAPER_TABLE_NAMES, PUBLIC_TABLE_NAMES, paper_table_rows, public_table_rows
from scripts.verify_repository import ROOT, run_verification


def test_level_a_verification() -> None:
    assert run_verification()["decision"] == "PASS_PUBLIC_REPOSITORY_VERIFICATION"


def test_public_table_set() -> None:
    assert set(public_table_rows(ROOT)) == set(PUBLIC_TABLE_NAMES)


def test_exact_paper_table_set() -> None:
    tables = paper_table_rows(ROOT)
    assert set(tables) == set(PAPER_TABLE_NAMES)
    assert len(tables["table6_matched_control"]) == 6


def test_runtime_value() -> None:
    rows = public_table_rows(ROOT)["table3_overall_comparison"]
    proposed = next(row for row in rows if row["Method"] == "Proposed method")
    assert proposed["Target-side time (s)"] == "5.676 ± 0.059"


def test_table4_is_complete() -> None:
    rows = public_table_rows(ROOT)["table4_component_ablation"]
    assert rows[-1]["Complexity-feasible outputs (%)"] == "96.25"
    assert "Harmful alternative selection / all cases (%)" in rows[0]
