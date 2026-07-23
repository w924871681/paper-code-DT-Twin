from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting.frozen import (
    CANONICAL_SOURCES, DECISION, DYNAMIC_TABLES, EXPECTED_GENERATED_FILES,
    PAPER_TABLE_NAMES, PUBLIC_TABLE_NAMES, VALIDATION_DECISION,
    paper_table_rows, public_table_rows,
)
from scripts.verify_assets import load_asset_manifest
from scripts.level_c_bootstrap import load_manifest as load_bootstrap_manifest

SANITIZED_FILES = {
    "RESTRUCTURE_REPORT.json",
    "results/audited_provenance/anchor_safe_selector_manifest.json",
    "results/audited_provenance/main_experiments_audit.json",
    "results/supplementary/anchor_risk.json",
}
CORRECTED_FILES = {
    "results/main/mechanism_and_cost.csv",
    "results/robustness/architecture_coverage.csv",
    "results/figure_data/tableS6_alibaba_semi_real.csv",
    "results/figure_data/tableS5_oracle_diagnostics.csv",
    "results/figure_data/tableS7_architecture_coverage.csv",
    "results/figure_data/tableS8_safety_across_pools.csv",
    "results/figure_data/table4_component_ablation.csv",
    "results/figure_data/tableS4_bank_size.csv",
    "results/figure_data/table1_experimental_configuration.csv",
    "results/figure_data/table2_baseline_fairness.csv",
}
DERIVED_AUDIT_FILES = {
    "results/audited_provenance/fig12_case_level_gain_manifest.json",
}
REQUIRED_FILES = {
    "README.md", "CITATION.cff", "LICENSE", "pyproject.toml", "environment.yml",
    "CHANGELOG.md", "AUTHOR_METADATA_REQUIRED.md", "RELEASE_NOTES_v1.1.0.md", "RELEASE_NOTES_v1.1.1.md", "RELEASE_NOTES_v1.1.2.md", "RELEASE_NOTES_v1.1.3.md", "RELEASE_NOTES_v1.1.4.md", "RELEASE_NOTES_v1.1.5.md", "RELEASE_NOTES_v1.1.6.md", "CODEX_V1_1_5_PAPER_ALIGNMENT_AUDIT.md", "CODEX_V1_1_6_RELEASE_AUDIT.md", ".github/workflows/ci.yml", ".github/workflows/release.yml",
    "docs/METHOD.md", "docs/DATA_AVAILABILITY.md", "docs/REPRODUCIBILITY.md", "docs/PAPER_RESULT_MAPPING.md", "docs/LEVEL_C_COMPLETION_PLAN.md", "docs/FIGURE_REPRODUCTION.md", "docs/INTERNAL_PROVENANCE_NAMES.md",
    "assets/README.md", "assets/model_assets.csv", "assets/level_c_bootstrap_files.csv", "data/README.md", "data/alibaba2018/README.md",
    "results/README.md", "results/audited_provenance/SANITIZATION_MANIFEST.json",
    "results/audited_provenance/NUMERICAL_CORRECTIONS.json",
    "scripts/generate_paper_outputs.py", "scripts/verify_repository.py", "scripts/verify_assets.py",
    "scripts/run_smoke_test.py", "scripts/run_full_reproduction.py", "scripts/build_alibaba2018_bank.py",
    "scripts/level_c_bootstrap.py", "scripts/build_level_c_bootstrap.py", "scripts/stage_level_c_bootstrap.py",
    "scripts/finalize_cuda_replay.py", "scripts/verify_release_evidence.py",
    "scripts/plot_reproducible_figures.py", "scripts/derive_reproducible_figure_data.py",
    "reporting/final_figures.py", "reporting/reproducible_figures.py",
    "scripts/validate_paper_outputs.py", "reporting/frozen.py", "paper_assets/legacy_figures/manifest.json", "paper_assets/current_figures/manifest.json",
    "paper/manuscript.tex", "paper/manuscript.pdf",
    *{f"paper/figures/fig{i}.pdf" for i in range(1, 13)},
    *CANONICAL_SOURCES,
}
MODULES = ["core.data.sim", "core.space.profile", "source_prior_bank.pipeline", "anchor_safe_selector.pipeline", "main_evaluation.pipeline", "experiments.main.pipeline", "experiments.robustness.pipeline", "experiments.supplementary.pipeline", "reporting.frozen", "reporting.final_figures", "reporting.reproducible_figures"]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_release_text(path: Path) -> str:
    """Hash released text with Git's LF form on every checkout platform."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def check_required_files() -> list[str]:
    return [f"missing required file: {name}" for name in sorted(REQUIRED_FILES) if not (ROOT / name).is_file()]


def check_imports() -> list[str]:
    errors = []
    for module in MODULES:
        try: importlib.import_module(module)
        except Exception as exc: errors.append(f"cannot import {module}: {exc!r}")
    return errors


def check_json() -> list[str]:
    errors = []
    for path in ROOT.rglob("*.json"):
        if "outputs" in path.parts: continue
        try: json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc: errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
    return errors


def check_checksums() -> list[str]:
    errors = []
    index = {row["path"]: row["sha256"] for row in _csv(ROOT / "FILE_INDEX.csv")}
    sanitation = json.loads((ROOT / "results/audited_provenance/SANITIZATION_MANIFEST.json").read_text(encoding="utf-8"))
    if set(sanitation.get("files", {})) != SANITIZED_FILES: errors.append("sanitization file set mismatch")
    for name, info in sanitation.get("files", {}).items():
        if index.get(name) != info.get("original_sha256"): errors.append(f"sanitization original checksum mismatch: {name}")
        if not (ROOT / name).is_file() or _sha256_release_text(ROOT / name) != info.get("sanitized_sha256"): errors.append(f"sanitized checksum mismatch: {name}")
    corrections = json.loads((ROOT / "results/audited_provenance/NUMERICAL_CORRECTIONS.json").read_text(encoding="utf-8"))
    if set(corrections.get("files", {})) != CORRECTED_FILES: errors.append("numerical-correction file set mismatch")
    for name, info in corrections.get("files", {}).items():
        if index.get(name) != info.get("original_sha256"): errors.append(f"correction original checksum mismatch: {name}")
        if not (ROOT / name).is_file() or _sha256_release_text(ROOT / name) != info.get("corrected_sha256"): errors.append(f"corrected checksum mismatch: {name}")
    for path in (ROOT / "results/audited_provenance").glob("*.json"):
        name = path.relative_to(ROOT).as_posix()
        if path.name in {"SANITIZATION_MANIFEST.json", "NUMERICAL_CORRECTIONS.json"} or name in SANITIZED_FILES or name in DERIVED_AUDIT_FILES: continue
        if index.get(name) != _sha256(path): errors.append(f"immutable audit checksum mismatch: {name}")
    return errors


def check_asset_manifest() -> list[str]:
    try: rows = load_asset_manifest(ROOT / "assets/model_assets.csv")
    except Exception as exc: return [f"invalid model asset manifest: {exc}"]
    errors = [] if len(rows) == 13 else [f"expected 13 model assets, found {len(rows)}"]
    try: bootstrap_rows = load_bootstrap_manifest()
    except Exception as exc: return errors + [f"invalid Level-C bootstrap manifest: {exc}"]
    if len(bootstrap_rows) != 32:
        errors.append(f"expected 32 Level-C bootstrap files, found {len(bootstrap_rows)}")
    return errors


def check_frozen_protocol() -> list[str]:
    errors = []
    split = json.loads((ROOT / "data/synthetic/split_manifest.json").read_text(encoding="utf-8"))
    expected = {"data_seed":2904,"source_bank_training_seeds":[2904,2905,2906],"H":[1,4],"K":[10,20],"locked_main_centers":[980,999],"trajectory_centers":[1080,1099],"optimizer_control_centers":[1100,1119]}
    if split != expected: errors.append("synthetic split manifest differs from frozen protocol")
    from configs.methods.main_experiments_cfg import CFG
    expected_cfg = {
        "data_seed": 2904,
        "train_seed": 2904,
        "target_seeds": (2904, 2905, 2906),
        "H_list": (1, 4),
        "K_list": (10, 20),
        "architecture_count": 66,
        "anchor_arch_idx": 57,
        "compact_arch_indices": (1, 6, 13, 55, 56, 57),
        "frozen_margin_rel": 0.10,
        "target_steps": 50,
        "target_lr": 0.01,
        "target_grad_clip": 1.0,
        "bank_sizes": (1, 2, 3, 4, 5, 6),
        "source_scales": (10, 20, 30, 40, 50),
        "bootstrap_repeats": 4000,
    }
    for field, value in expected_cfg.items():
        actual = getattr(CFG, field)
        if actual != value:
            errors.append(f"frozen protocol changed: {field}={actual!r}")
    return errors


def check_numbers() -> list[str]:
    errors = []
    expected = public_table_rows(ROOT)
    for stem in DYNAMIC_TABLES:
        if _csv(ROOT / f"results/figure_data/{stem}.csv") != expected[stem]: errors.append(f"public table differs from frozen sources: {stem}")
    runtime = {row["method"]: row for row in _csv(ROOT / "results/supplementary/repeated_runtime_summary.csv")}
    ours = runtime["ours_c32_locked"]
    if abs(float(ours["mean_seconds"])-5.676108809500022)>1e-12 or abs(float(ours["repeat_mean_std_seconds"])-0.059080506136177456)>1e-12: errors.append("repeated proposed runtime changed")
    mechanism = next(row for row in _csv(ROOT / "results/main/mechanism_and_cost.csv") if row["Method"]=="Ours")
    dist = json.loads(mechanism["SelectedArchitectureDistribution"])
    if abs(float(mechanism["AnchorRetentionRate"])-.4125)>1e-12 or int(dist.get("PT_A57_A57",0))!=33: errors.append("reference retention is inconsistent")
    alibaba = {row["Measure"]:float(row["Value"]) for row in _csv(ROOT / "results/robustness/alibaba_oracle_diagnostics.csv")}
    if alibaba["Mean captured oracle headroom"] != 0.654228491766997 or int(alibaba["Beneficial selected cases"])!=39 or int(alibaba["Harmful selected cases"])!=5: errors.append("Alibaba V2 diagnostics changed")
    retained = next((row for row in _csv(ROOT / "results/robustness/architecture_coverage.csv") if row["Dataset"]=="C33Locked980-999" and row["ArchIdx"]=="57"), None)
    if not retained or int(retained["SelectedCount"])!=33 or int(retained["SelectedBeneficialCount"])!=0 or int(retained["SelectedHarmfulCount"])!=0: errors.append("retained references are not neutral")
    paper = paper_table_rows(ROOT)
    if tuple(paper) != PAPER_TABLE_NAMES or len(paper["table4_matched_control"]) != 6: errors.append("exact revised-paper table set or order is incomplete")
    fig6 = _csv(ROOT / "results/figure_data/fig6_paired_instantiation_data.csv")
    fig6_counts = {name: sum(row["selection_category"] == name for row in fig6) for name in ("beneficial alternative", "reference retained", "harmful alternative")}
    paired_gain = 100 * sum(
        (float(row["pt_ft_wmse"]) - float(row["proposed_wmse"])) / float(row["pt_ft_wmse"])
        for row in fig6
    ) / len(fig6)
    if len(fig6) != 80 or fig6_counts != {"beneficial alternative": 44, "reference retained": 33, "harmful alternative": 3}: errors.append("Fig. 6 public paired data changed")
    if abs(paired_gain - 14.602159705445189) > 1e-12:
        errors.append("main paired MSE reduction changed")
    filtering = _csv(ROOT / "results/figure_data/fig8_candidate_filtering_data.csv")
    if [(row["budget_tier"], row["case_count"], row["initialized_candidates_per_case"], row["feasible_candidates_per_case_mean"]) for row in filtering] != [("tight", "20", "7", "4"), ("medium", "52", "7", "7"), ("loose", "8", "7", "7")]: errors.append("Fig. 8 candidate-filtering data changed")
    selection = _csv(ROOT / "results/figure_data/fig8_architecture_selection_data.csv")
    if len(selection) != 15 or any(sum(int(row["selection_count"]) for row in selection if row["budget_tier"] == tier) != n for tier, n in (("tight", 20), ("medium", 52), ("loose", 8))): errors.append("Fig. 8 architecture-selection data changed")
    margin = {float(row["minimum_improvement"]): row for row in _csv(ROOT / "results/figure_data/fig9_margin_data.csv")}
    if float(margin[0.1]["harmful_selection_rate"]) != 0.05 or margin[0.1]["eligible_under_5pct_criterion"] != "true": errors.append("Fig. 9 margin data changed")
    tradeoff = _csv(ROOT / "results/figure_data/fig10_deployment_tradeoff_data.csv")
    if [row["method"] for row in tradeoff] != ["PT+FT", "Few-shot NAS", "Zero-shot NAS+FT", "RCF-DTI"]:
        errors.append("Fig. 10 representative-method mapping changed")
    architecture = {row["configuration"]: row for row in _csv(ROOT / "results/figure_data/fig11_architecture_complexity_data.csv")}
    if set(architecture) != {"3-layer MLP-32", "4-layer MLP-32", "Alt. GRU-16", "Alt. GRU-32", "Ref. GRU-32"}:
        errors.append("Fig. 11 architecture mapping changed")
    if architecture.get("Alt. GRU-32", {}).get("harmful_selected_cases") != "2" or architecture.get("Alt. GRU-16", {}).get("harmful_selected_cases") != "1":
        errors.append("Fig. 11 harmful-case annotations changed")
    cases = _csv(ROOT / "results/figure_data/fig12_case_level_gains.csv")
    alibaba_gains = [float(row["gain_percent"]) for row in cases if row["group"] == "Alibaba"]
    if len(cases) != 320 or len(alibaba_gains) != 80 or sum(value < -25 for value in alibaba_gains) != 4:
        errors.append("Fig. 12 exact case-level distribution changed")
    return errors


def check_public_terms() -> list[str]:
    files = [
        ROOT / "README.md",
        ROOT / "CITATION.cff",
        *(path for path in (ROOT / "docs").glob("*.md") if path.name != "INTERNAL_PROVENANCE_NAMES.md"),
        ROOT / "assets/README.md",
        ROOT / "data/README.md",
        ROOT / "data/alibaba2018/README.md",
        *(ROOT / "results/figure_data").glob("*.csv"),
    ]
    patterns = [re.compile(p, re.I) for p in [
        r"\bresource[- ]constraints?\b",
        r"\bsource[- ]prior(?: bank)?\b",
        r"\bhard resource feasibility\b",
        r"\bPT-A57\b",
        r"\banchor[- ]safe selector\b",
        r"\bproposed method\b",
    ]]
    errors=[]
    for path in files:
        text=path.read_text(encoding="utf-8-sig", errors="replace")
        if any(p.search(text) for p in patterns): errors.append(f"prohibited public term in {path.relative_to(ROOT)}")
    return errors


def check_privacy() -> list[str]:
    patterns=[
        re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]"),
        re.compile(r"/(?:home|Users|mnt|tmp)/[^\\s\"']*", re.I),
        re.compile(r"\b[A-Z0-9._%+-]+@(?!example\.)[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
        re.compile(r"\b(?:ghp_|github_pat_|sk-[A-Za-z0-9_-]{16})[A-Za-z0-9_-]*\b"),
        re.compile(r"\b(?:password|passwd|api[_-]?key|secret)\s*[:=]\s*[^\s<]+", re.I),
        re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"),
        re.compile(r"\b[0-9a-f]{5}-[0-9a-f]{5}\b",re.I),
    ]
    errors=[]
    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or path.suffix.lower() not in {".json",".csv",".md",".txt",".log",".cff",".py",".tex",".yml",".yaml",".toml"}
            or "outputs" in path.parts
            or ".git" in path.parts
            or "__pycache__" in path.parts
            or path.name in {"verify_repository.py", "verify_release_evidence.py"}
        ):
            continue
        text=path.read_text(encoding="utf-8-sig",errors="replace")
        if any(p.search(text) for p in patterns): errors.append(f"private path or credential pattern in {path.relative_to(ROOT)}")
    return errors


def check_test_leakage() -> list[str]:
    errors: list[str] = []
    selector = json.loads(
        (ROOT / "results/audited_provenance/anchor_safe_selector_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    expected = {
        "decision": "PASS_C32_SELECTOR_FROZEN",
        "selected_margin_rel": 0.1,
        "selection_uses": "development Check only for finite-grid calibration",
        "final_pool_opened": False,
        "test_used": False,
    }
    for field, value in expected.items():
        if selector.get(field) != value:
            errors.append(f"selector leakage invariant changed: {field}")
    fig9_caption = (ROOT / "reporting/frozen.py").read_text(encoding="utf-8")
    if "Held-out target cases are not used" not in fig9_caption:
        errors.append("Fig. 9 held-out isolation disclosure is missing")
    return errors


def check_unique_figure_implementation() -> list[str]:
    errors: list[str] = []
    canonical = ROOT / "reporting/final_figures.py"
    if not canonical.is_file():
        return ["canonical final figure module is missing"]
    for path in (ROOT / "reporting").glob("*.py"):
        if path == canonical:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?m)^def\s+plot_fig(?:6|7|8|9|10|11|12)\b", text):
            errors.append(f"duplicate final figure implementation: {path.relative_to(ROOT)}")
    wrapper = (ROOT / "scripts/plot_reproducible_figures.py").read_text(encoding="utf-8")
    if "from reporting.final_figures import plot_all" not in wrapper:
        errors.append("compatibility plotting wrapper does not delegate to canonical module")
    return errors


def check_version_metadata() -> list[str]:
    errors = []
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    if 'version = "1.1.6"' not in pyproject:
        errors.append("pyproject version is not 1.1.6")
    if not re.search(r"(?m)^version:\s*1\.1\.6\s*$", citation):
        errors.append("CITATION.cff version is not 1.1.6")
    for asset in (
        "level_c_bootstrap_${GITHUB_REF_NAME}.zip",
        "level_c_bootstrap_${GITHUB_REF_NAME}.zip.sha256",
        "cuda_replay_evidence_${GITHUB_REF_NAME}.zip",
        "cuda_replay_evidence_${GITHUB_REF_NAME}.zip.sha256",
        "paper_alignment_${GITHUB_REF_NAME}.zip",
        "paper_alignment_${GITHUB_REF_NAME}.zip.sha256",
        "rcf_dti_${GITHUB_REF_NAME}_complete.zip",
        "rcf_dti_${GITHUB_REF_NAME}_complete.zip.sha256",
        "RCF_DTI_FIGURE_CODE_FINAL_V1_1_6.zip",
        "RCF_DTI_FIGURE_CODE_FINAL_V1_1_6.zip.sha256",
        "SHA256SUMS.txt",
    ):
        if asset not in workflow:
            errors.append(f"release workflow does not handle {asset}")
    return errors


def check_generated(root: Path | None) -> list[str]:
    if root is None: return []
    manifest_path=root/"paper_outputs_manifest.json"
    if not manifest_path.is_file(): return ["missing generated manifest"]
    manifest=json.loads(manifest_path.read_text(encoding="utf-8")); errors=[]
    if manifest.get("decision")!=DECISION or manifest.get("figure_validation")!=VALIDATION_DECISION: errors.append("generated manifest decision mismatch")
    if set(manifest.get("source_sha256",{}))!=set(CANONICAL_SOURCES): errors.append("generated source set mismatch")
    for name,expected in manifest.get("source_sha256",{}).items():
        if not (ROOT/name).is_file() or _sha256(ROOT/name)!=expected: errors.append(f"generated source checksum mismatch: {name}")
    if set(manifest.get("generated_sha256",{}))!=set(EXPECTED_GENERATED_FILES): errors.append("generated file set mismatch")
    for name,expected in manifest.get("generated_sha256",{}).items():
        if not (root/name).is_file() or _sha256(root/name)!=expected: errors.append(f"generated checksum mismatch: {name}")
    for stem,rows in paper_table_rows(ROOT).items():
        if _csv(root/f"tables/paper_csv/{stem}.csv") != rows: errors.append(f"exact paper table mismatch: {stem}")
    return errors


def run_verification(generated_root: Path | None=None) -> dict[str,Any]:
    checks: list[tuple[str,Callable[[],list[str]]]]=[
        ("required_files",check_required_files),
        ("imports",check_imports),
        ("json",check_json),
        ("checksums",check_checksums),
        ("asset_manifest",check_asset_manifest),
        ("frozen_protocol",check_frozen_protocol),
        ("numerical_consistency",check_numbers),
        ("test_leakage",check_test_leakage),
        ("unique_figure_implementation",check_unique_figure_implementation),
        ("public_terminology",check_public_terms),
        ("privacy",check_privacy),
        ("version_metadata",check_version_metadata),
        ("generated_outputs",lambda:check_generated(generated_root)),
    ]
    errors=[]; status={}
    for name,fn in checks:
        found=fn(); status[name]="PASS" if not found else "FAIL"; errors.extend(found)
    return {"decision":"PASS_PUBLIC_REPOSITORY_VERIFICATION" if not errors else "FAIL_PUBLIC_REPOSITORY_VERIFICATION","checks":status,"errors":errors}


def main() -> int:
    parser=argparse.ArgumentParser(description="Verify the public repository and frozen-result consistency."); parser.add_argument("--generated-root",type=Path); args=parser.parse_args()
    result=run_verification(args.generated_root.resolve() if args.generated_root else None)
    for name,status in result["checks"].items(): print(f"{status:<4} {name}")
    if result["errors"]: print(json.dumps(result,ensure_ascii=False,indent=2)); return 2
    print("PASS_PUBLIC_REPOSITORY_VERIFICATION"); return 0


if __name__=="__main__": raise SystemExit(main())
