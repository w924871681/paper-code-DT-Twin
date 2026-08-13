from __future__ import annotations

import pytest

from experiments.main.pipeline import _select_anchor_safe
from shared.evaluation.common import UnsupportedLimitError


def _candidate(token: str, *, feasible: bool, validation_mse: float) -> dict:
    return {
        "token": token,
        "arch_idx": 57 if token == "PT_A57" else 55,
        "params": 1.0,
        "flops": 1.0,
        "hard_feasible": feasible,
        "validation": {"weighted_mse": validation_mse},
    }


def test_anchor_safe_reports_unsupported_when_reference_only_is_infeasible() -> None:
    with pytest.raises(UnsupportedLimitError, match="UNSUPPORTED_LIMIT"):
        _select_anchor_safe(
            [_candidate("PT_A57", feasible=False, validation_mse=1.0)],
            allowed_tokens=["PT_A57"],
            margin_rel=0.10,
            enforce_feasible=True,
        )


def test_anchor_safe_does_not_replace_an_infeasible_reference_with_alternative() -> None:
    rows = [
        _candidate("PT_A57", feasible=False, validation_mse=1.0),
        _candidate("A55", feasible=True, validation_mse=0.5),
    ]
    with pytest.raises(UnsupportedLimitError, match="UNSUPPORTED_LIMIT"):
        _select_anchor_safe(
            rows,
            allowed_tokens=["PT_A57", "A55"],
            margin_rel=0.10,
            enforce_feasible=True,
        )


def test_anchor_safe_ablation_can_still_disable_feasibility_filtering() -> None:
    selection = _select_anchor_safe(
        [_candidate("PT_A57", feasible=False, validation_mse=1.0)],
        allowed_tokens=["PT_A57"],
        margin_rel=0.10,
        enforce_feasible=False,
    )
    assert selection["selected_token"] == "PT_A57"
    assert selection["selected_hard_feasible"] is False
