from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "run_r1_end_to_end_screening_stability.py"
SPEC = importlib.util.spec_from_file_location("r1_screening_stability_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
R1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R1)


def test_screen_candidate_bank_semantics_are_exact() -> None:
    assert [x["token"] for x in R1._candidate_identities("S0")] == [
        "PT_A57_A57",
        "LEGACY_C1_A57_A57",
        "STRONG_COMPACT_A1",
        "STRONG_COMPACT_A6",
        "STRONG_COMPACT_A13",
        "STRONG_COMPACT_A55",
        "STRONG_COMPACT_A56",
    ]
    assert R1._candidate_identities("S1") == [
        {"token": "PT_A57_A57", "arch_idx": 57, "initialization": "protected_pt"}
    ]
    assert [x["token"] for x in R1._candidate_identities("S2")] == [
        "PT_A57_A57",
        "LEGACY_C1_A57_A57",
        "STRONG_COMPACT_A55",
        "STRONG_COMPACT_A56",
        "STRONG_COMPACT_A59",
    ]


def test_frozen_seed_rules() -> None:
    assert R1._source_asset_seed(1, 59) == 3064
    assert R1._source_asset_seed(4, 59) == 3367
    assert R1._target_seed(1180, 1, 10) == 1_194_091
    assert R1._target_seed(1199, 4, 20) == 1_213_903
    assert len({R1._bootstrap_seed(screen) for screen in R1.SCREENS}) == 1


def test_target_center_seed_manifest_is_complete_and_fixed() -> None:
    records = R1._center_seed_records(R1.TARGET_POOL)
    assert [row["center_id"] for row in records] == list(range(1180, 1200))
    assert all(row["pool_master_seed"] == 322_904 for row in records)
    assert all(row["role"] == "r1_heldout_target_only" for row in records)
    assert all(len(row["cases"]) == 4 for row in records)
    assert {row["center_type"] for row in records} == {"A", "B", "C"}


def test_margin_selector_has_strict_reference_fallback() -> None:
    anchor = {
        "token": "PT_A57_A57",
        "arch_idx": 57,
        "params": 10,
        "flops": 20,
        "validation": {"weighted_mse": 1.0},
    }
    selected = R1._select([anchor], 0.10)
    assert selected["selected_token"] == "PT_A57_A57"
    assert selected["switched_from_pt_anchor"] is False
    assert selected["best_alternative_validation_mse"] is None


def test_output_directory_is_strictly_isolated(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "results").mkdir(parents=True)
    valid = R1._ensure_output_root(
        root, Path("results/r1_end_to_end_screening_stability")
    )
    assert valid == (root / "results" / "r1_end_to_end_screening_stability").resolve()
    with pytest.raises(ValueError):
        R1._ensure_output_root(root, Path("outputs/r1_end_to_end_screening_stability"))
    with pytest.raises(ValueError):
        R1._ensure_output_root(root, Path("results/not_r1"))
