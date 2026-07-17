from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.methods.main_evaluation_cfg import CFG
from scripts.level_c_bootstrap import stage_bundle, verify_bundle


SMOKE_METHOD_ROOT = Path("outputs/main_evaluation_smoke_d2904_t2904")
FORMAL_METHOD_ROOT = Path(CFG.output_root)
DEFAULT_ORCHESTRATION_ROOT = Path("outputs/full_reproduction")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _absolute(path: Path, repo_root: Path = ROOT) -> Path:
    return path.resolve() if path.is_absolute() else (repo_root / path).resolve()


def resolve_output_roots(
    *,
    smoke: bool,
    output_root: Path | None = None,
    method_output_root: Path | None = None,
    repo_root: Path = ROOT,
) -> tuple[Path, Path]:
    """Resolve orchestration and method outputs without changing frozen protocol."""
    run_mode = "smoke" if smoke else "formal"
    orchestration = _absolute(
        output_root or DEFAULT_ORCHESTRATION_ROOT / run_mode, repo_root
    )
    method_default = SMOKE_METHOD_ROOT if smoke else FORMAL_METHOD_ROOT
    method_root = _absolute(method_output_root or method_default, repo_root)
    if smoke and method_root == _absolute(FORMAL_METHOD_ROOT, repo_root):
        raise ValueError("Smoke output root must not equal the frozen formal output root")
    return orchestration, method_root


def _commands(
    device: str,
    safe_mode: str,
    smoke: bool,
    method_output_root: Path,
) -> list[dict[str, Any]]:
    py = sys.executable
    preflight_out = method_output_root / "preflight" / "c33_preflight.json"
    commands: list[dict[str, Any]] = [
        {
            "stage": "locked_preflight",
            "argv": [
                py,
                "scripts/preflight_main_evaluation.py",
                "--out",
                str(preflight_out),
            ],
        }
    ]
    for method in CFG.methods:
        argv = [py, "scripts/run_main_evaluation_method.py", "--method", method,
                "--device", device, "--safe_mode", safe_mode,
                "--output-root", str(method_output_root)]
        if smoke:
            argv.append("--smoke")
        commands.append({"stage": f"method_{method}", "argv": argv})
    if not smoke:
        commands.extend([
            {
                "stage": "analyze_locked_evaluation",
                "argv": [py, "scripts/analyze_main_evaluation.py", "--root", str(method_output_root)],
            },
            {
                "stage": "audit_locked_evaluation",
                "argv": [py, "scripts/audit_main_evaluation.py", "--root", str(method_output_root)],
            },
        ])
    return commands


def _write_ledger(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify, stage, and replay the frozen locked main evaluation without retraining source assets."
    )
    parser.add_argument("--bootstrap-dir", type=Path)
    parser.add_argument("--asset-dir", type=Path, help="Deprecated alias for --bootstrap-dir")
    parser.add_argument("--alibaba-archive", type=Path, help="Optional checksum check; not used by the main-evaluation replay")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--safe-mode", default="gru-native")
    parser.add_argument(
        "--output-root",
        type=Path,
        help="Orchestration ledger/log root (defaults to a mode-specific directory)",
    )
    parser.add_argument(
        "--method-output-root",
        type=Path,
        help="Method/preflight/analysis root; smoke and formal defaults are isolated",
    )
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="Run two locked cases per method; skip formal analysis/audit")
    args = parser.parse_args()

    bundle = args.bootstrap_dir or args.asset_dir
    if bundle is None:
        parser.error("--bootstrap-dir is required")
    output_root, method_output_root = resolve_output_roots(
        smoke=args.smoke,
        output_root=args.output_root,
        method_output_root=args.method_output_root,
    )
    ledger_path = output_root / "frozen_main_evaluation_ledger.json"
    commands = _commands(args.device, args.safe_mode, args.smoke, method_output_root)
    bundle_check = verify_bundle(bundle)
    ledger: dict[str, Any] = {
        "schema": "frozen-main-evaluation-ledger-v1",
        "scope": "frozen locked main-evaluation replay",
        "source_training_repeated": False,
        "started_at": _now(), "ended_at": None,
        "plan_only": args.plan_only, "smoke": args.smoke,
        "run_mode": "smoke" if args.smoke else "formal",
        "orchestration_output_root": str(output_root),
        "method_output_root": str(method_output_root),
        "output_isolation": True,
        "device": args.device, "bootstrap_verification": bundle_check,
        "alibaba": {"provided": False, "required_for_this_scope": False},
        "commands": [{"stage": item["stage"], "argv": item["argv"]} for item in commands],
        "stages": [], "decision": "PENDING",
    }
    if args.alibaba_archive:
        expected = "3e6ee87fd204bb85b9e234c5c75a5096580fdabc8f085b224033080090753a7a"
        archive = args.alibaba_archive.resolve()
        actual = _sha256(archive) if archive.is_file() else None
        ledger["alibaba"] = {
            "provided": True, "required_for_this_scope": False,
            "filename": archive.name, "sha256": actual,
            "expected_sha256": expected, "hash_verified": actual == expected,
        }
        if actual != expected:
            ledger["decision"] = "FAIL_ALIBABA_ARCHIVE_CHECK"
    if bundle_check["failure_count"]:
        ledger["decision"] = "FAIL_LEVEL_C_BOOTSTRAP"
    if ledger["decision"].startswith("FAIL_"):
        ledger["ended_at"] = _now(); _write_ledger(ledger_path, ledger)
        print(json.dumps(ledger, ensure_ascii=False, indent=2)); return 2

    if args.plan_only:
        ledger["decision"] = "PASS_BOOTSTRAP_AND_EXECUTION_PLAN"
        ledger["ended_at"] = _now(); _write_ledger(ledger_path, ledger)
        print(json.dumps(ledger, ensure_ascii=False, indent=2)); return 0

    if not args.device.lower().startswith("cuda") or not torch.cuda.is_available():
        ledger["decision"] = "BLOCKED_CUDA_RUNTIME_UNAVAILABLE"
        ledger["ended_at"] = _now(); _write_ledger(ledger_path, ledger)
        print(json.dumps(ledger, ensure_ascii=False, indent=2)); return 2

    staged = stage_bundle(bundle, ROOT)
    ledger["bootstrap_stage"] = staged
    _write_ledger(ledger_path, ledger)
    logs = output_root / "logs"; logs.mkdir(parents=True, exist_ok=True)
    for item in commands:
        started = _now()
        completed = subprocess.run(item["argv"], cwd=ROOT, text=True, capture_output=True)
        log_path = logs / f"{item['stage']}.log"
        log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
        record = {
            "stage": item["stage"], "argv": item["argv"], "started_at": started,
            "ended_at": _now(), "return_code": completed.returncode,
            "log": str(log_path), "log_sha256": _sha256(log_path),
        }
        ledger["stages"].append(record); _write_ledger(ledger_path, ledger)
        if completed.returncode != 0:
            ledger["decision"] = f"FAIL_STAGE_{item['stage'].upper()}"
            ledger["ended_at"] = _now(); _write_ledger(ledger_path, ledger)
            print(json.dumps(ledger, ensure_ascii=False, indent=2)); return completed.returncode

    ledger["decision"] = "PASS_FROZEN_MAIN_EVALUATION_SMOKE" if args.smoke else "PASS_FROZEN_MAIN_EVALUATION_REPLAY"
    ledger["ended_at"] = _now(); _write_ledger(ledger_path, ledger)
    print(json.dumps(ledger, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
