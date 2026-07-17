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


def test_reproducible_figures_have_public_data() -> None:
    import csv

    with (ROOT / "results/figure_data/fig6_paired_instantiation_data.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 80
    assert sum(row["selection_category"] == "beneficial alternative" for row in rows) == 44
    assert (ROOT / "results/figure_data/fig8_architecture_selection_data.csv").is_file()
    assert (ROOT / "results/figure_data/fig9_margin_data.csv").is_file()


def test_level_c_bootstrap_manifest_is_portable() -> None:
    from scripts.level_c_bootstrap import load_manifest

    rows = load_manifest()
    assert len(rows) == 32
    assert len({row["artifact"] for row in rows}) == 32
    assert all(len(row["sha256"]) == 64 for row in rows)
