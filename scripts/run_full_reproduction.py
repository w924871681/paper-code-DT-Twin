from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_assets import verify_asset_directory


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Level-C prerequisites and write a non-retuning execution plan.")
    parser.add_argument("--asset-dir", type=Path, required=True)
    parser.add_argument("--alibaba-archive", type=Path)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs/full_reproduction")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    assets = verify_asset_directory(args.asset_dir)
    if assets["failure_count"]:
        print(json.dumps(assets, ensure_ascii=False, indent=2)); return 2
    expected = "3e6ee87fd204bb85b9e234c5c75a5096580fdabc8f085b224033080090753a7a"
    alibaba: dict[str, object] = {"provided": False, "required_for": "Alibaba semi-real evaluation"}
    if args.alibaba_archive:
        archive = args.alibaba_archive.resolve()
        if not archive.is_file(): raise FileNotFoundError(archive)
        actual = _sha256(archive)
        if actual.lower() != expected:
            print("Full reproduction cannot start: Alibaba archive SHA-256 mismatch."); return 2
        alibaba = {"provided": True, "file": archive.name, "sha256": actual, "expected_sha256": expected, "hash_verified": True}
    errors = []
    if not args.plan_only and not alibaba["provided"]: errors.append("--alibaba-archive is required")
    if not args.plan_only and not args.device.lower().startswith("cuda"): errors.append("Level C requires CUDA")
    if not args.plan_only and not torch.cuda.is_available(): errors.append("PyTorch cannot access a CUDA GPU")
    if args.plan_only: decision = "PASS_LEVEL_C_PREREQUISITES_AND_PLAN_ONLY"
    elif errors: decision = "BLOCKED_LEVEL_C_PREREQUISITES"
    else: decision = "BLOCKED_LEVEL_C_PUBLIC_DRIVER_UNAVAILABLE"
    plan = {
        "decision": decision, "execution_started": False,
        "reason": "The public package validates archived inputs, but the end-to-end orchestration driver is not released.",
        "prerequisite_errors": errors, "device": args.device, "asset_verification": assets, "alibaba": alibaba,
        "frozen_stages": ["source-initialization asset staging", "reference-based selector verification", "locked main evaluation", "component and robustness evaluations", "Alibaba preprocessing, real source-bank build, and semi-real evaluation", "paper-output reconstruction and audits"],
        "available_entry_points": ["scripts/preflight_source_prior_bank.py", "scripts/preflight_anchor_safe_selector.py", "scripts/preflight_main_evaluation.py", "scripts/run_main_evaluation_method.py", "scripts/run_component_ablation.py", "scripts/run_seed_reproducibility.py", "scripts/run_controlled_source_scale.py", "scripts/prepare_alibaba2018_trace.py", "scripts/build_alibaba2018_bank.py", "scripts/run_alibaba2018_evaluation.py", "scripts/generate_paper_outputs.py"],
    }
    out = args.output_root.resolve(); out.mkdir(parents=True, exist_ok=True)
    (out / "full_reproduction_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if args.plan_only: print(decision); return 0
    print(decision); return 2 if errors else 3


if __name__ == "__main__":
    raise SystemExit(main())
