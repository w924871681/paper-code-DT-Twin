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
REQUIRED_FILES = {
    "README.md", "CITATION.cff", "LICENSE", "pyproject.toml", "environment.yml",
    "CHANGELOG.md", "RELEASE_NOTES_v1.1.0.md", ".github/workflows/ci.yml",
    "docs/METHOD.md", "docs/DATA_AVAILABILITY.md", "docs/REPRODUCIBILITY.md", "docs/PAPER_RESULT_MAPPING.md",
    "assets/README.md", "assets/model_assets.csv", "data/README.md", "data/alibaba2018/README.md",
    "results/README.md", "results/audited_provenance/SANITIZATION_MANIFEST.json",
    "results/audited_provenance/NUMERICAL_CORRECTIONS.json",
    "scripts/generate_paper_outputs.py", "scripts/verify_repository.py", "scripts/verify_assets.py",
    "scripts/run_smoke_test.py", "scripts/run_full_reproduction.py", "scripts/build_alibaba2018_bank.py",
    "scripts/validate_paper_outputs.py", "reporting/frozen.py", "paper_assets/legacy_figures/manifest.json",
    *CANONICAL_SOURCES,
}
MODULES = ["core.data.sim", "core.space.profile", "source_prior_bank.pipeline", "anchor_safe_selector.pipeline", "main_evaluation.pipeline", "experiments.main.pipeline", "experiments.robustness.pipeline", "experiments.supplementary.pipeline", "reporting.frozen"]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
        if not (ROOT / name).is_file() or _sha256(ROOT / name) != info.get("sanitized_sha256"): errors.append(f"sanitized checksum mismatch: {name}")
    corrections = json.loads((ROOT / "results/audited_provenance/NUMERICAL_CORRECTIONS.json").read_text(encoding="utf-8"))
    if set(corrections.get("files", {})) != CORRECTED_FILES: errors.append("numerical-correction file set mismatch")
    for name, info in corrections.get("files", {}).items():
        if index.get(name) != info.get("original_sha256"): errors.append(f"correction original checksum mismatch: {name}")
        if not (ROOT / name).is_file() or _sha256(ROOT / name) != info.get("corrected_sha256"): errors.append(f"corrected checksum mismatch: {name}")
    for path in (ROOT / "results/audited_provenance").glob("*.json"):
        name = path.relative_to(ROOT).as_posix()
        if path.name in {"SANITIZATION_MANIFEST.json", "NUMERICAL_CORRECTIONS.json"} or name in SANITIZED_FILES: continue
        if index.get(name) != _sha256(path): errors.append(f"immutable audit checksum mismatch: {name}")
    return errors


def check_asset_manifest() -> list[str]:
    try: rows = load_asset_manifest(ROOT / "assets/model_assets.csv")
    except Exception as exc: return [f"invalid model asset manifest: {exc}"]
    return [] if len(rows) == 13 else [f"expected 13 model assets, found {len(rows)}"]


def check_frozen_protocol() -> list[str]:
    errors = []
    split = json.loads((ROOT / "data/synthetic/split_manifest.json").read_text(encoding="utf-8"))
    expected = {"data_seed":2904,"source_bank_training_seeds":[2904,2905,2906],"H":[1,4],"K":[10,20],"locked_main_centers":[980,999],"trajectory_centers":[1080,1099],"optimizer_control_centers":[1100,1119]}
    if split != expected: errors.append("synthetic split manifest differs from frozen protocol")
    from configs.methods.main_experiments_cfg import CFG
    if tuple(CFG.H_list)!=(1,4) or tuple(CFG.K_list)!=(10,20) or CFG.target_steps!=50 or abs(CFG.frozen_margin_rel-.10)>1e-12: errors.append("frozen method protocol changed")
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
    if set(paper) != set(PAPER_TABLE_NAMES) or len(paper["table6_matched_control"]) != 6: errors.append("exact revised-paper table set is incomplete")
    return errors


def check_public_terms() -> list[str]:
    files = [ROOT / "README.md", ROOT / "CITATION.cff", *(ROOT / "docs").glob("*.md"), ROOT / "assets/README.md", ROOT / "data/README.md", ROOT / "data/alibaba2018/README.md", *(ROOT / "results/figure_data").glob("*.csv")]
    patterns = [re.compile(p, re.I) for p in [r"\bresource[- ]constraints?\b", r"\bsource[- ]prior(?: bank)?\b", r"\bhard resource feasibility\b", r"\bPT-A57\b", r"\banchor[- ]safe selector\b"]]
    errors=[]
    for path in files:
        text=path.read_text(encoding="utf-8-sig", errors="replace")
        if any(p.search(text) for p in patterns): errors.append(f"prohibited public term in {path.relative_to(ROOT)}")
    return errors


def check_privacy() -> list[str]:
    patterns=[re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]"),re.compile(r"/(?:home|Users)/[^/\s]+/"),re.compile(r"/tmp/"),re.compile(r"924871681@qq\.com",re.I),re.compile(r"\b(?:ghp_|github_pat_)[A-Za-z0-9_]+\b"),re.compile(r"\bpassword\s*[:=]",re.I),re.compile(r"\b[0-9a-f]{5}-[0-9a-f]{5}\b",re.I)]
    errors=[]
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json",".csv",".md",".txt",".log",".cff"} or "outputs" in path.parts: continue
        text=path.read_text(encoding="utf-8-sig",errors="replace")
        if any(p.search(text) for p in patterns): errors.append(f"private path or credential pattern in {path.relative_to(ROOT)}")
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
    checks: list[tuple[str,Callable[[],list[str]]]]=[("required_files",check_required_files),("imports",check_imports),("json",check_json),("checksums",check_checksums),("asset_manifest",check_asset_manifest),("frozen_protocol",check_frozen_protocol),("numerical_consistency",check_numbers),("public_terminology",check_public_terms),("privacy",check_privacy),("generated_outputs",lambda:check_generated(generated_root))]
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
