from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from reporting.frozen import PAPER_TABLE_NAMES, PUBLIC_TABLE_NAMES, paper_table_rows, public_table_rows
from scripts.verify_repository import ROOT, run_verification
from reporting.overall_performance import (
    EXPECTED_H_META_NAS_LABELS,
    H_META_NAS_INDEX,
    PANEL_TEMPLATES,
    load_h_meta_nas_values,
    panel_data,
)


def test_level_a_verification() -> None:
    assert run_verification()["decision"] == "PASS_PUBLIC_REPOSITORY_VERIFICATION"


def test_public_table_set() -> None:
    assert set(public_table_rows(ROOT)) == set(PUBLIC_TABLE_NAMES)


def test_exact_paper_table_set() -> None:
    tables = paper_table_rows(ROOT)
    assert set(tables) == set(PAPER_TABLE_NAMES)
    assert tuple(tables) == PAPER_TABLE_NAMES
    assert tuple(tables) == ("table1_configuration", "table4_target_cost")


def test_runtime_value() -> None:
    rows = public_table_rows(ROOT)["table3_overall_comparison"]
    proposed = next(row for row in rows if row["Method"] == "MSA-DTI")
    assert proposed["Target-side time (s)"] == "5.676 ± 0.059"


def test_current_figure5_uses_canonical_h_meta_nas_values() -> None:
    source = ROOT / "results/main/overall_comparison.csv"
    audited = load_h_meta_nas_values(source)
    assert tuple(f"{value:.3f}" for value in audited) == EXPECTED_H_META_NAS_LABELS
    panels = panel_data(source)
    for template, panel, audited_value in zip(PANEL_TEMPLATES, panels, audited):
        assert panel[1][H_META_NAS_INDEX] == audited_value
        for index, value in enumerate(template[1]):
            if index != H_META_NAS_INDEX:
                assert panel[1][index] == value


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
    assert (ROOT / "results/figure_data/fig9_selection_outcomes_data.csv").is_file()
    assert (ROOT / "results/figure_data/fig10_architecture_complexity_data.csv").is_file()
    assert (ROOT / "results/figure_data/fig11_margin_data.csv").is_file()
    assert (ROOT / "results/figure_data/deployment_tradeoff_radar_data.csv").is_file()
    with (ROOT / "results/figure_data/fig12_case_level_gains.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        fig12 = list(csv.DictReader(handle))
    assert len(fig12) == 400
    assert sum(row["group"] == "Alibaba" for row in fig12) == 160
    assert sum(
        row["group"] == "Alibaba" and float(row["gain_percent"]) < -25
        for row in fig12
    ) == 1


def test_supplement_figure_generator_roles_and_radar_counts(tmp_path: Path) -> None:
    data = ROOT / "results/figure_data"
    script = """
import json
import sys
from pathlib import Path
from reporting.final_figures import (
    plot_deployment_tradeoff_radar,
    plot_fig9,
    plot_fig10,
    plot_fig11,
)
data = Path(sys.argv[1])
output = Path(sys.argv[2])
print(json.dumps({
    "fig9": plot_fig9(data, output),
    "fig10": plot_fig10(data, output),
    "fig11": plot_fig11(data, output),
    "radar": plot_deployment_tradeoff_radar(data, output),
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(data), str(tmp_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    audits = json.loads(completed.stdout)
    expected = (
        ("fig9", "selection_outcomes"),
        ("fig10", "selected_configuration_complexity"),
        ("fig11", "configuration_analysis"),
    )
    for stem, role in expected:
        audit = audits[stem]
        assert audit["figure"] == stem
        assert audit["semantic"]["role"] == role
        assert (tmp_path / f"{stem}.pdf").is_file()

    radar = audits["radar"]
    assert radar["figure"] == "deployment_tradeoff_radar"
    assert radar["semantic"]["data_rows"] == 5
    assert radar["semantic"]["plotted_methods"] == 5
    assert radar["semantic"]["legend_methods"] == 5
    assert radar["semantic"]["methods"][-1] == "MSA-DTI"


def test_level_c_bootstrap_manifest_is_portable() -> None:
    from scripts.level_c_bootstrap import load_manifest

    rows = load_manifest()
    assert len(rows) == 32
    assert len({row["artifact"] for row in rows}) == 32
    assert all(len(row["sha256"]) == 64 for row in rows)


def test_smoke_then_formal_output_isolation(tmp_path: Path) -> None:
    from scripts.run_full_reproduction import _commands, resolve_output_roots

    smoke_orchestration, smoke_methods = resolve_output_roots(
        smoke=True, repo_root=tmp_path
    )
    formal_orchestration, formal_methods = resolve_output_roots(
        smoke=False, repo_root=tmp_path
    )

    assert smoke_orchestration != formal_orchestration
    assert smoke_methods != formal_methods
    assert smoke_methods.name == "main_evaluation_smoke_d2904_t2904"
    assert formal_methods.name == "main_evaluation_eval_d2904_t2904"

    smoke_marker = smoke_methods / "methods" / "ours_c32_locked.json"
    smoke_marker.parent.mkdir(parents=True)
    smoke_marker.write_text('{"run_mode":"smoke"}\n', encoding="utf-8")

    formal_commands = _commands("cuda", "gru-native", False, formal_methods)
    formal_argv = "\n".join(
        " ".join(item["argv"]) for item in formal_commands
    )
    assert str(smoke_methods) not in formal_argv
    assert str(formal_methods) in formal_argv
    assert smoke_marker.read_text(encoding="utf-8") == '{"run_mode":"smoke"}\n'


def test_public_evidence_sanitization_is_recursive(tmp_path: Path) -> None:
    from scripts.finalize_cuda_replay import sanitize_public_value

    roots = {
        "<REPO_ROOT>": tmp_path / "repo",
        "<PYTHON_EXECUTABLE>": tmp_path / "venv" / "python.exe",
    }
    raw = {
        "argv": [str(roots["<PYTHON_EXECUTABLE>"]), str(roots["<REPO_ROOT>"] / "scripts" / "run.py")],
        "decision": "PASS_FROZEN_MAIN_EVALUATION_REPLAY",
        "nested": {"values": [80, 5.676]},
    }
    sanitized = sanitize_public_value(raw, roots)
    assert sanitized["argv"] == [
        "<PYTHON_EXECUTABLE>",
        str(Path("<REPO_ROOT>") / "scripts" / "run.py"),
    ]
    assert sanitized["decision"] == raw["decision"]
    assert sanitized["nested"] == raw["nested"]
