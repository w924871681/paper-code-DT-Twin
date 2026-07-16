from __future__ import annotations
from scripts.run_smoke_test import run_smoke


def test_cpu_smoke_pipeline(tmp_path) -> None:
    result=run_smoke(tmp_path)
    assert result["decision"]=="PASS_CPU_SMOKE_TEST"
    assert result["selected_is_feasible"] is True


def test_smoke_filters_candidate(tmp_path) -> None:
    run_smoke(tmp_path)
    text=(tmp_path/"smoke_candidates.csv").read_text(encoding="utf-8")
    assert "SMOKE_FILTERED" in text and "False" in text
