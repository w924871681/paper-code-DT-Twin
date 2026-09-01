# -*- coding: utf-8 -*-
"""Run the isolated R1 candidate-discovery end-to-end stability experiment.

This runner deliberately does not modify the frozen C3-1/C3-2/C3-3 configs.
It reuses their data, training, feasibility, adaptation, selection, and
bootstrap semantics while placing every newly generated artifact under one
R1-only result directory.

The command has two explicit gates:

1. ``--prepare-only`` writes the immutable protocol manifest without training.
2. ``--execute --protocol-sha256 HASH`` runs only when HASH matches that file.

Test tensors for centers 1180--1199 are not materialized until every source
bank and every bank-specific calibration result has been frozen.
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

import numpy as np
import torch
import torch.optim as optim

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.methods.anchor_safe_selector_cfg import CFG as SELECTOR_CFG
from configs.methods.main_evaluation_cfg import CFG as EVAL_CFG
from configs.methods.source_prior_bank_cfg import CFG as BANK_CFG
from core.data.sim import _make_type_schedule
from core.methods.ours.paper_engine import _load_prior_model
from core.methods.ours.stage2_runtime import (
    candidate_backend_context,
    candidate_device,
    synchronize_if_cuda,
)
from core.methods.ours.weight_bank import load_weight_bank
from core.space import build_model, is_feasible, profile_arch
from shared.data_access import get_support_validation_check, get_test_only
from shared.evaluation.common import (
    atomic_json,
    build_runtime,
    eval_metrics,
    file_sha256,
    seed_all,
)
from source_prior_bank.pipeline import (
    _atomic_torch_save,
    _frozen_pt_anchor_asset,
    _iter_source_batches,
    _load_external_source_manifest,
)


PROTOCOL_VERSION = "r1_candidate_discovery_e2e_stability_v1_0"
DATA_SEED = 2904
TRAIN_SEED = 2904
SOURCE_CENTERS = tuple(range(20))
CALIBRATION_POOL = (940, 20, 200000)
TARGET_POOL = (1180, 20, 320000)
H_LIST = (1, 4)
K_LIST = (10, 20)
ANCHOR_IDX = 57
SCREENS: Dict[str, Tuple[int, ...]] = {
    "S0": (1, 6, 13, 55, 56, 57),
    "S1": (),
    "S2": (55, 56, 57, 59),
}
SCREENING_POOLS: Dict[str, Dict[str, Any]] = {
    "S0": {
        "center_ids": list(range(900, 920)),
        "seed_offset": None,
        "seed_offset_status": "not recorded in retained R2 artifact; screening is not rerun",
    },
    "S1": {
        "center_ids": list(range(1120, 1140)),
        "seed_offset": None,
        "seed_offset_status": "not recorded in retained R2 artifact; screening is not rerun",
    },
    "S2": {
        "center_ids": list(range(1140, 1160)),
        "seed_offset": None,
        "seed_offset_status": "not recorded in retained R2 artifact; screening is not rerun",
    },
}
MARGIN_GRID = (0.05, 0.075, 0.10, 0.125, 0.15, 0.20)
BOOTSTRAP_REPEATS = 4000
EPS = 1e-12
EXPECTED_OUTPUT_NAME = "r1_end_to_end_screening_stability"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _run_capture(args: Sequence[str], cwd: Path) -> Dict[str, Any]:
    proc = subprocess.run(
        list(args),
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {
        "command": list(args),
        "exit_code": int(proc.returncode),
        "output": proc.stdout,
    }


def _git_info(root: Path) -> Dict[str, Any]:
    head = _run_capture(("git", "rev-parse", "HEAD"), root)
    status = _run_capture(("git", "status", "--short"), root)
    describe = _run_capture(("git", "describe", "--always", "--dirty", "--tags"), root)
    return {
        "commit": head["output"].strip(),
        "describe": describe["output"].strip(),
        "status_short": status["output"].splitlines(),
    }


def _tracked_snapshot(root: Path) -> Dict[str, str]:
    listed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout
    snapshot: Dict[str, str] = {}
    for raw in listed.split(b"\0"):
        if not raw:
            continue
        rel = raw.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        path = root / Path(rel)
        snapshot[rel] = _sha256(path) if path.is_file() else "MISSING"
    return snapshot


def _ensure_output_root(root: Path, requested: Path) -> Path:
    resolved_root = root.resolve()
    output = requested if requested.is_absolute() else resolved_root / requested
    output = output.resolve()
    required_parent = (resolved_root / "results").resolve()
    try:
        output.relative_to(required_parent)
    except ValueError as exc:
        raise ValueError(f"R1 output must stay under {required_parent}: {output}") from exc
    if output.name != EXPECTED_OUTPUT_NAME:
        raise ValueError(
            f"R1 output directory must be named {EXPECTED_OUTPUT_NAME!r}: {output}"
        )
    return output


def _center_seed_records(pool: Tuple[int, int, int]) -> List[Dict[str, Any]]:
    start, count, offset = pool
    master_seed = DATA_SEED + int(offset)
    rng = np.random.RandomState(master_seed)
    schedule = _make_type_schedule(
        n_centers=count,
        type_ratio=(3, 4, 3),
        allowed_types=("A", "B", "C"),
        rng=rng,
    )
    records: List[Dict[str, Any]] = []
    for local_id, center_type in enumerate(schedule):
        records.append(
            {
                "center_id": int(start + local_id),
                "center_type": str(center_type),
                "pool_master_seed": int(master_seed),
                "center_rng_seed": int(rng.randint(0, 2**31 - 1)),
                "role": "r1_heldout_target_only",
                "cases": [
                    {"H": H, "K": K, "target_adaptation_seed": _target_seed(start + local_id, H, K)}
                    for H in H_LIST
                    for K in K_LIST
                ],
            }
        )
    return records


def _source_asset_seed(H: int, arch_idx: int) -> int:
    return TRAIN_SEED + 101 * int(H) + int(arch_idx)


def _target_seed(center_id: int, H: int, K: int) -> int:
    return TRAIN_SEED + 1009 * int(center_id) + 37 * int(H) + 53 * int(K)


def _bootstrap_seed(screen: str, metric: str = "weighted_mse") -> int:
    method = f"{screen.lower()}_derived_msa_dti"
    return TRAIN_SEED + 701 + len(method) + len(metric)


def _architecture_records() -> List[Dict[str, Any]]:
    cfg, _cache, A, _requested, _safe = build_runtime("cpu", "default", ())
    if len(A) != 66 or any(i != int(spec.arch_id) for i, spec in enumerate(A)):
        raise RuntimeError("The frozen 66-configuration architecture space drifted")
    return [spec.to_dict() for spec in A]


def _candidate_identities(screen: str) -> List[Dict[str, Any]]:
    retained = SCREENS[screen]
    identities: List[Dict[str, Any]] = [
        {"token": "PT_A57_A57", "arch_idx": 57, "initialization": "protected_pt"}
    ]
    if ANCHOR_IDX in retained:
        identities.append(
            {
                "token": "LEGACY_C1_A57_A57",
                "arch_idx": 57,
                "initialization": "paired_c1",
            }
        )
    identities.extend(
        {
            "token": f"STRONG_COMPACT_A{idx}",
            "arch_idx": int(idx),
            "initialization": "r1_source_trained",
        }
        for idx in retained
        if idx != ANCHOR_IDX
    )
    return identities


def _protocol_manifest(root: Path, output_root: Path, device: str, safe_mode: str) -> Dict[str, Any]:
    arch = _architecture_records()
    selected_arch = {
        str(idx): arch[idx]
        for idx in sorted({ANCHOR_IDX, *(idx for vals in SCREENS.values() for idx in vals)})
    }
    c1_path = root / BANK_CFG.c1_bank_path
    external_path = root / BANK_CFG.external_source_manifest
    if not c1_path.is_file() or _sha256(c1_path) != BANK_CFG.c1_bank_sha256:
        raise RuntimeError("Frozen paired C1 bank is missing or has the wrong hash")
    external = _load_external_source_manifest(str(root))
    if tuple(SELECTOR_CFG.selector_dev_pool) != CALIBRATION_POOL:
        raise RuntimeError("Frozen calibration pool drifted")
    if tuple(float(x) for x in SELECTOR_CFG.margin_grid) != MARGIN_GRID:
        raise RuntimeError("Frozen margin grid drifted")
    if tuple(EVAL_CFG.locked_pool) == TARGET_POOL:
        raise RuntimeError("R1 target pool unexpectedly aliases the main held-out pool")
    if any(cid in range(1160, 1180) for cid in range(TARGET_POOL[0], TARGET_POOL[0] + TARGET_POOL[1])):
        raise RuntimeError("R1 target pool overlaps the prior robustness pool")

    return {
        "protocol_version": PROTOCOL_VERSION,
        "created_at_unix_s": time.time(),
        "repository": _git_info(root),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "device": device,
            "safe_mode": safe_mode,
            "cuda_available": bool(torch.cuda.is_available()),
        },
        "architecture_space": {
            "count": 66,
            "indexing": "literal zero-based internal IDs A0--A65",
            "family_counts": {"MLP": 18, "TCN": 36, "GRU": 12},
            "reference_arch_idx": ANCHOR_IDX,
            "selected_specs": selected_arch,
            "A56_A57_executable_duplicate": True,
            "duplicate_reason": "single-layer torch GRU disables recurrent dropout",
        },
        "screening": {
            "retention_rule": "check_true_wins>=2 OR validation_positive_wins>=2",
            "check_true_win": "feasible check oracle improves on PT-A57",
            "validation_positive_win": "validation-selected alternative improves on PT-A57 check MSE",
            "outcomes": {
                screen: {
                    "screening_pool": SCREENING_POOLS[screen],
                    "retained_indexed_configurations": list(retained),
                    "candidate_identities": _candidate_identities(screen),
                    "candidate_bank_size": len(_candidate_identities(screen)),
                }
                for screen, retained in SCREENS.items()
            },
        },
        "source_training": {
            "center_ids": list(SOURCE_CENTERS),
            "data_seed": DATA_SEED,
            "seed_offset": 0,
            "data": "support_plus_validation_K20",
            "optimizer": "Adam",
            "loss": "MSE",
            "epochs": 50,
            "learning_rate": 1e-3,
            "batch_size": 64,
            "weight_decay": 0.0,
            "asset_seed_rule": "2904 + 101*H + arch_idx",
            "asset_seeds": {
                screen: {
                    f"h{H}_a{idx}": _source_asset_seed(H, idx)
                    for H in H_LIST
                    for idx in retained
                    if idx != ANCHOR_IDX
                }
                for screen, retained in SCREENS.items()
            },
        },
        "candidate_bank_semantics": {
            "protected_reference": "copy exact frozen PT-A57 source asset for each H",
            "paired_A57": "include frozen legacy C1-A57 only when A57 is retained",
            "retained_non_reference": "independently source-train per screen under the frozen recipe",
            "A56_A57": "keep indexed candidates and initializations separate; do not deduplicate",
            "no_alternative": "S1 contains PT-A57 only",
        },
        "calibration": {
            "pool": list(CALIBRATION_POOL),
            "center_ids": list(range(CALIBRATION_POOL[0], CALIBRATION_POOL[0] + CALIBRATION_POOL[1])),
            "shared_identically_across_banks": True,
            "margin_grid": list(MARGIN_GRID),
            "harmful_selection_rate_max": 0.05,
            "mean_gain_vs_reference_min": 0.03,
            "ci_low_vs_reference_strictly_greater_than": 0.0,
            "mean_gain_vs_paired_min": 0.03,
            "ci_low_vs_paired_strictly_greater_than": 0.0,
            "rule": "smallest eligible margin; otherwise deploy adapted PT-A57 only",
            "bootstrap_repetitions": BOOTSTRAP_REPEATS,
            "test_used": False,
        },
        "target_evaluation": {
            "pool": list(TARGET_POOL),
            "pool_master_seed": DATA_SEED + TARGET_POOL[2],
            "center_ids": list(range(TARGET_POOL[0], TARGET_POOL[0] + TARGET_POOL[1])),
            "center_seed_records": _center_seed_records(TARGET_POOL),
            "H": list(H_LIST),
            "K": list(K_LIST),
            "case_count": 80,
            "split": "chronological support/validation/check/test with disjoint raw segments",
            "test_policy": "materialize Test only after deployment filtering, adaptation, and validation selection",
            "optimizer": "SGD",
            "loss": "MSE",
            "updates": 50,
            "learning_rate": 0.01,
            "gradient_norm_limit": 1.0,
            "batching": "complete support set",
            "target_seed_rule": "2904 + 1009*center_id + 37*H + 53*K",
            "bootstrap_seed_rule": "2904 + 701 + len(method) + len(metric)",
            "bootstrap_seeds": {screen: _bootstrap_seed(screen) for screen in SCREENS},
        },
        "deployment_limits": {
            "tight": {"flops": 1_500_000, "params": 30_000},
            "medium": {"flops": 5_000_000, "params": 100_000},
            "loose": {"flops": 20_000_000, "params": 500_000},
            "filter_before_adaptation": True,
        },
        "frozen_inputs": {
            "paired_c1_bank": {
                "path": c1_path.resolve().relative_to(root.resolve()).as_posix(),
                "sha256": _sha256(c1_path),
            },
            "external_source_manifest": {
                "path": external_path.resolve().relative_to(root.resolve()).as_posix(),
                "sha256": _sha256(external_path),
            },
            "external_source_decision": external.get("decision"),
        },
        "isolation": {
            "output_root": output_root.resolve().relative_to(root.resolve()).as_posix(),
            "manuscript_edits_allowed": False,
            "canonical_result_edits_allowed": False,
            "test_used_upstream": False,
        },
    }


def prepare(root: Path, output_root: Path, device: str, safe_mode: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "protocol_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(
            f"Protocol manifest already exists; do not silently overwrite it: {manifest_path}"
        )
    manifest = _protocol_manifest(root, output_root, device, safe_mode)
    atomic_json(manifest, str(manifest_path))
    sha_path = output_root / "protocol_manifest.sha256"
    _atomic_write_text(sha_path, f"{_sha256(manifest_path)}  protocol_manifest.json\n")
    print(json.dumps({"prepared": str(manifest_path), "sha256": _sha256(manifest_path)}, indent=2))
    return manifest_path


def _load_protocol(output_root: Path, expected_sha256: str) -> Dict[str, Any]:
    path = output_root / "protocol_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"Run --prepare-only first: {path}")
    actual = _sha256(path)
    if actual.lower() != expected_sha256.lower():
        raise RuntimeError(f"Protocol manifest hash mismatch: expected {expected_sha256}, got {actual}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("protocol_version") != PROTOCOL_VERSION:
        raise RuntimeError("R1 protocol version mismatch")
    return obj


def _asset_record(path: Path, root: Path, **extra: Any) -> Dict[str, Any]:
    return {
        "path": path.resolve().relative_to(root.resolve()).as_posix(),
        "sha256": _sha256(path),
        **extra,
    }


def _build_bank(
    *,
    root: Path,
    output_root: Path,
    screen: str,
    cfg: Any,
    cache: Any,
    A: Sequence[Any],
    requested: torch.device,
    safe_mode: str,
    resume: bool,
) -> Dict[str, Any]:
    retained = SCREENS[screen]
    bank_dir = output_root / "banks" / screen
    bank_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = bank_dir / "bank_manifest.json"
    external = _load_external_source_manifest(str(root))
    L = int(cfg.main.task.L)
    X0, *_ = get_support_validation_check(cfg, cache, 0, H_LIST[0], max(K_LIST))
    input_dim = int(X0.shape[-1])
    manifest: Dict[str, Any]
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not resume:
            raise RuntimeError(f"Existing R1 bank requires an explicitly confirmed --resume: {manifest_path}")
        if tuple(manifest.get("retained_indexed_configurations", ())) != retained:
            raise RuntimeError(f"Retained-set mismatch in {manifest_path}")
    else:
        manifest = {
            "study": "R1 candidate-discovery end-to-end stability",
            "screen": screen,
            "decision": "R1_BANK_IN_PROGRESS",
            "retained_indexed_configurations": list(retained),
            "candidate_identities": _candidate_identities(screen),
            "candidate_bank_size": len(_candidate_identities(screen)),
            "source_centers": list(SOURCE_CENTERS),
            "source_recipe": {
                "optimizer": "Adam",
                "loss": "MSE",
                "epochs": BANK_CFG.source_epochs,
                "lr": BANK_CFG.source_lr,
                "batch_size": BANK_CFG.source_batch_size,
                "weight_decay": BANK_CFG.source_weight_decay,
                "source_data": "support_plus_validation_K20",
            },
            "assets": {},
            "paired_c1_input": {
                "included": ANCHOR_IDX in retained,
                "path": BANK_CFG.c1_bank_path,
                "sha256": BANK_CFG.c1_bank_sha256,
            },
            "target_pool_used": False,
            "calibration_pool_used": False,
            "test_used": False,
        }

    jobs = [(H, ANCHOR_IDX) for H in H_LIST]
    jobs += [(H, idx) for H in H_LIST for idx in retained if idx != ANCHOR_IDX]
    started = time.perf_counter()
    for job_no, (H, idx) in enumerate(jobs, 1):
        key = f"h{H}_a{idx}"
        out_file = bank_dir / f"source_h{H}_a{idx}.pt"
        existing = manifest["assets"].get(key)
        if existing and out_file.is_file() and _sha256(out_file) == existing.get("sha256"):
            continue
        spec = A[idx]
        if idx == ANCHOR_IDX:
            source_path, source_hash = _frozen_pt_anchor_asset(str(root), external, H=H)
            shutil.copy2(source_path, out_file)
            if _sha256(out_file) != source_hash:
                raise RuntimeError(f"PT-A57 copy hash mismatch for {screen} H={H}")
            manifest["assets"][key] = _asset_record(
                out_file,
                root,
                H=H,
                arch_idx=idx,
                arch_key=spec.arch_key,
                family=spec.family,
                provenance="exact_frozen_PT_A57_copy",
                source_seed=None,
                epochs_completed=BANK_CFG.source_epochs,
                elapsed_seconds=0.0,
            )
        else:
            actual = candidate_device(spec, requested, safe_mode)
            progress = out_file.with_suffix(out_file.suffix + ".progress.pt")
            with candidate_backend_context(spec, actual, safe_mode):
                asset_seed = _source_asset_seed(H, idx)
                seed_all(asset_seed, actual)
                model = build_model(spec, input_dim=input_dim, H=H, L=L, device=str(actual))
                optimizer = optim.Adam(
                    model.parameters(),
                    lr=BANK_CFG.source_lr,
                    weight_decay=BANK_CFG.source_weight_decay,
                )
                start_epoch = 0
                if progress.is_file():
                    if not resume:
                        raise RuntimeError(f"Progress checkpoint requires --resume: {progress}")
                    state = torch.load(progress, map_location=actual)
                    model.load_state_dict(state["model"], strict=True)
                    optimizer.load_state_dict(state["optimizer"])
                    torch.set_rng_state(state["torch_rng_state"])
                    if actual.type == "cuda" and state.get("cuda_rng_state") is not None:
                        torch.cuda.set_rng_state(state["cuda_rng_state"], actual)
                    start_epoch = int(state["next_epoch"])
                asset_started = time.perf_counter()
                last_loss = None
                for epoch in range(start_epoch, BANK_CFG.source_epochs):
                    losses: List[float] = []
                    for Xb, yb in _iter_source_batches(
                        cfg,
                        cache,
                        H=H,
                        batch_size=BANK_CFG.source_batch_size,
                        epoch=epoch,
                    ):
                        model.train()
                        optimizer.zero_grad(set_to_none=True)
                        pred = model(Xb.to(actual).contiguous())
                        loss = ((pred - yb.to(actual).contiguous()) ** 2).mean()
                        if not torch.isfinite(loss):
                            raise RuntimeError(f"Non-finite source loss: {screen} H={H} A{idx}")
                        loss.backward()
                        optimizer.step()
                        losses.append(float(loss.detach().item()))
                    last_loss = float(np.mean(losses))
                    _atomic_torch_save(
                        {
                            "model": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                            "optimizer": optimizer.state_dict(),
                            "next_epoch": epoch + 1,
                            "torch_rng_state": torch.get_rng_state(),
                            "cuda_rng_state": (
                                torch.cuda.get_rng_state(actual) if actual.type == "cuda" else None
                            ),
                        },
                        str(progress),
                    )
                    elapsed = time.perf_counter() - asset_started
                    print(
                        f"[R1][{screen}][source] job={job_no}/{len(jobs)} H={H} A={idx} "
                        f"epoch={epoch + 1}/{BANK_CFG.source_epochs} loss={last_loss:.8g} "
                        f"elapsed={elapsed / 3600:.2f}h",
                        flush=True,
                    )
                synchronize_if_cuda(actual)
                _atomic_torch_save(
                    {k: v.detach().cpu() for k, v in model.state_dict().items()}, str(out_file)
                )
                progress.unlink(missing_ok=True)
                elapsed_seconds = time.perf_counter() - asset_started
                del model, optimizer
            params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
            manifest["assets"][key] = _asset_record(
                out_file,
                root,
                H=H,
                arch_idx=idx,
                arch_key=spec.arch_key,
                family=spec.family,
                provenance="R1_independent_PT_recipe_source_training",
                source_seed=asset_seed,
                epochs_completed=BANK_CFG.source_epochs,
                final_source_loss=last_loss,
                params=params,
                flops=flops,
                elapsed_seconds=elapsed_seconds,
            )
        manifest["completed_assets"] = len(manifest["assets"])
        manifest["expected_assets"] = len(jobs)
        atomic_json(manifest, str(manifest_path))
        gc.collect()
        if requested.type == "cuda":
            torch.cuda.empty_cache()

    if len(manifest["assets"]) != len(jobs):
        raise RuntimeError(f"Incomplete {screen} bank: {len(manifest['assets'])}/{len(jobs)}")
    for item in manifest["assets"].values():
        path = root / item["path"]
        if not path.is_file() or _sha256(path) != item["sha256"]:
            raise RuntimeError(f"R1 bank asset verification failed: {path}")
    manifest["decision"] = "PASS_R1_BANK_FROZEN"
    manifest["elapsed_seconds"] = float(time.perf_counter() - started)
    manifest["calibration_pool_used"] = False
    manifest["target_pool_used"] = False
    manifest["test_used"] = False
    atomic_json(manifest, str(manifest_path))
    return manifest


def _load_source_model(
    *,
    root: Path,
    bank: Mapping[str, Any],
    c1_bank: Mapping[str, Mapping[str, torch.Tensor]],
    token: str,
    idx: int,
    A: Sequence[Any],
    H: int,
    input_dim: int,
    L: int,
    device: torch.device,
) -> torch.nn.Module:
    spec = A[idx]
    if token == "LEGACY_C1_A57_A57":
        model, _prior = _load_prior_model(
            spec=spec,
            H=H,
            L=L,
            input_dim=input_dim,
            bank=c1_bank,
            device=device,
        )
        return model
    item = bank["assets"][f"h{H}_a{idx}"]
    path = root / item["path"]
    model = build_model(spec, input_dim=input_dim, H=H, L=L, device=str(device))
    model.load_state_dict(torch.load(path, map_location=device), strict=True)
    return model


def _adapt(model: torch.nn.Module, Xs: torch.Tensor, ys: torch.Tensor, seed: int) -> None:
    device = next(model.parameters()).device
    seed_all(seed, device)
    model.train()
    optimizer = optim.SGD(model.parameters(), lr=EVAL_CFG.fixed_target_lr)
    Xd = Xs.to(device).contiguous()
    yd = ys.to(device).contiguous()
    for _ in range(EVAL_CFG.fixed_target_steps):
        optimizer.zero_grad(set_to_none=True)
        loss = ((model(Xd) - yd) ** 2).mean()
        if not torch.isfinite(loss):
            raise RuntimeError("Non-finite R1 target adaptation loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), EVAL_CFG.fixed_target_grad_clip)
        optimizer.step()


def _planned_case_candidates(screen: str, feasible: set[int]) -> List[Dict[str, Any]]:
    out = []
    for item in _candidate_identities(screen):
        if int(item["arch_idx"]) in feasible:
            out.append(dict(item))
    if not any(item["token"] == "PT_A57_A57" for item in out):
        raise RuntimeError("PT-A57 must be deployment-feasible in every R1 case")
    return out


def _candidate_sort_key(row: Mapping[str, Any]) -> Tuple[Any, ...]:
    return (
        float(row["validation"]["weighted_mse"]),
        float(row["params"]),
        float(row["flops"]),
        int(row["arch_idx"]),
        str(row["token"]),
    )


def _select(rows: Sequence[Mapping[str, Any]], margin: float) -> Dict[str, Any]:
    anchors = [r for r in rows if r["token"] == "PT_A57_A57"]
    if len(anchors) != 1:
        raise RuntimeError("Exactly one PT-A57 row is required")
    anchor = anchors[0]
    alternatives = [r for r in rows if r is not anchor]
    best_alt = min(alternatives, key=_candidate_sort_key) if alternatives else None
    threshold = float(anchor["validation"]["weighted_mse"]) * (1.0 - float(margin))
    switched = best_alt is not None and float(best_alt["validation"]["weighted_mse"]) <= threshold
    selected = best_alt if switched else anchor
    return {
        "selected_token": selected["token"],
        "selected_arch_idx": int(selected["arch_idx"]),
        "switched_from_pt_anchor": bool(switched),
        "anchor_validation_mse": float(anchor["validation"]["weighted_mse"]),
        "best_alternative_validation_mse": (
            float(best_alt["validation"]["weighted_mse"]) if best_alt is not None else None
        ),
        "switch_threshold_validation_mse": threshold,
        "margin_rel": float(margin),
    }


def _jobs(pool: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
    start, count, _offset = pool
    return [(cid, H, K) for cid in range(start, start + count) for H in H_LIST for K in K_LIST]


def _candidate_cache(
    *,
    root: Path,
    output_root: Path,
    screen: str,
    bank: Mapping[str, Any],
    cfg: Any,
    cache: Any,
    A: Sequence[Any],
    requested: torch.device,
    safe_mode: str,
    c1_bank: Mapping[str, Mapping[str, torch.Tensor]],
    resume: bool,
) -> Dict[str, Any]:
    out_path = output_root / "calibration" / screen / "calibration_candidates.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.is_file():
        if not resume:
            raise RuntimeError(f"Existing candidate cache requires --resume: {out_path}")
        result = json.loads(out_path.read_text(encoding="utf-8"))
    else:
        result = {
            "study": "R1 bank-specific margin calibration candidates",
            "screen": screen,
            "pool": list(CALIBRATION_POOL),
            "records": {},
            "same_case_seed_for_all_candidates": True,
            "test_used": False,
            "complete": False,
        }
    records: MutableMapping[str, Any] = result["records"]
    L = int(cfg.main.task.L)
    started = time.perf_counter()
    for case_no, (cid, H, K) in enumerate(_jobs(CALIBRATION_POOL), 1):
        Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(
            cfg, cache, cid, H, K
        )
        case_key = f"c{cid}_h{H}_k{K}_b{tier}"
        if case_key in records and records[case_key].get("complete"):
            continue
        input_dim = int(Xs.shape[-1])
        feasible = {
            idx
            for idx, spec in enumerate(A)
            if is_feasible(spec, cfg.main.budget, tier, L, input_dim, H)
        }
        planned = _planned_case_candidates(screen, feasible)
        target_seed = _target_seed(cid, H, K)
        rows: List[Dict[str, Any]] = []
        for item in planned:
            idx = int(item["arch_idx"])
            spec = A[idx]
            actual = candidate_device(spec, requested, safe_mode)
            with candidate_backend_context(spec, actual, safe_mode):
                model = _load_source_model(
                    root=root,
                    bank=bank,
                    c1_bank=c1_bank,
                    token=item["token"],
                    idx=idx,
                    A=A,
                    H=H,
                    input_dim=input_dim,
                    L=L,
                    device=actual,
                )
                _adapt(model, Xs, ys, target_seed)
                validation = eval_metrics(model, Xv, yv)
                check = eval_metrics(model, Xc, yc)
                synchronize_if_cuda(actual)
                del model
            params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
            rows.append(
                {
                    **item,
                    "arch_key": spec.arch_key,
                    "family": spec.family,
                    "params": params,
                    "flops": flops,
                    "target_seed": target_seed,
                    "target_steps": EVAL_CFG.fixed_target_steps,
                    "validation": validation,
                    "check": check,
                }
            )
        if len(rows) != len(planned) or len({r["target_seed"] for r in rows}) != 1:
            raise RuntimeError(f"Calibration candidate completeness failure: {screen} {case_key}")
        records[case_key] = {
            "case_key": case_key,
            "center_id": cid,
            "center_type": ctype,
            "budget_tier": tier,
            "H": H,
            "K": K,
            "candidates": rows,
            "candidate_count": len(rows),
            "complete": True,
            "test_used": False,
        }
        result["completed_records"] = len(records)
        atomic_json(result, str(out_path))
        print(f"[R1][{screen}][calibration] case={case_no}/80 {case_key}", flush=True)
        gc.collect()
        if requested.type == "cuda":
            torch.cuda.empty_cache()
    result["complete"] = len(records) == 80 and all(r.get("complete") for r in records.values())
    result["elapsed_seconds"] = float(time.perf_counter() - started)
    result["test_used"] = False
    atomic_json(result, str(out_path))
    return result


def _relative_gain(new: float, ref: float) -> float:
    return float((float(ref) - float(new)) / (abs(float(ref)) + EPS))


def _center_bootstrap(
    records: Mapping[str, Mapping[str, Any]], values: Mapping[str, float], seed: int
) -> Dict[str, Any]:
    by_center: Dict[int, List[float]] = defaultdict(list)
    for key, value in values.items():
        by_center[int(records[key]["center_id"])].append(float(value))
    centers = sorted(by_center)
    arr = np.asarray([np.mean(by_center[c]) for c in centers], dtype=np.float64)
    rng = np.random.default_rng(int(seed))
    ids = rng.integers(0, len(arr), size=(BOOTSTRAP_REPEATS, len(arr)))
    boot = arr[ids].mean(axis=1)
    return {
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "ci_low": float(np.quantile(boot, 0.025)),
        "ci_high": float(np.quantile(boot, 0.975)),
        "N_centers": len(centers),
        "N_cases": len(values),
        "bootstrap_repetitions": BOOTSTRAP_REPEATS,
        "bootstrap_seed": int(seed),
    }


def _calibrate(screen: str, cache_obj: Mapping[str, Any], output_root: Path) -> Dict[str, Any]:
    records = cache_obj["records"]
    out_path = output_root / "calibration" / screen / "calibration_result.json"
    grid: Dict[str, Any] = {}
    eligible: List[float] = []
    has_pair = ANCHOR_IDX in SCREENS[screen]
    for i, margin in enumerate(MARGIN_GRID):
        selections: Dict[str, Any] = {}
        primary_values: Dict[str, float] = {}
        paired_values: Dict[str, float] = {}
        harmful: List[bool] = []
        switched: List[bool] = []
        for key, rec in records.items():
            rows = rec["candidates"]
            pt = next(r for r in rows if r["token"] == "PT_A57_A57")
            selected_info = _select(rows, margin)
            selected = next(r for r in rows if r["token"] == selected_info["selected_token"])
            primary_values[key] = _relative_gain(
                selected["check"]["weighted_mse"], pt["check"]["weighted_mse"]
            )
            is_switched = bool(selected_info["switched_from_pt_anchor"])
            switched.append(is_switched)
            harmful.append(
                is_switched
                and float(selected["check"]["weighted_mse"])
                > float(pt["check"]["weighted_mse"])
            )
            if has_pair:
                paired = next(r for r in rows if r["token"] == "LEGACY_C1_A57_A57")
                dual_info = _select((pt, paired), margin)
                dual = next(r for r in (pt, paired) if r["token"] == dual_info["selected_token"])
                paired_values[key] = _relative_gain(
                    selected["check"]["weighted_mse"], dual["check"]["weighted_mse"]
                )
            selections[key] = selected_info
        primary = _center_bootstrap(records, primary_values, TRAIN_SEED + 100 * i + 1)
        paired = (
            _center_bootstrap(records, paired_values, TRAIN_SEED + 100 * i + 2)
            if has_pair
            else None
        )
        harmful_rate = float(np.mean(harmful))
        is_eligible = bool(
            has_pair
            and primary["mean"] >= SELECTOR_CFG.primary_gain_mean
            and primary["ci_low"] > SELECTOR_CFG.primary_gain_ci_low
            and harmful_rate <= SELECTOR_CFG.harmful_switch_rate_max
            and paired is not None
            and paired["mean"] >= SELECTOR_CFG.architecture_increment_mean
            and paired["ci_low"] > SELECTOR_CFG.architecture_increment_ci_low
        )
        item = {
            "margin_rel": margin,
            "primary_gain_over_adapted_PT_A57": primary,
            "gain_over_dual_A57_paired_initialization": paired,
            "switch_rate": float(np.mean(switched)),
            "harmful_switch_rate_all_cases": harmful_rate,
            "harmful_switch_count": int(sum(harmful)),
            "paired_control_available": has_pair,
            "eligible": is_eligible,
            "selections": selections,
        }
        grid[f"{margin:.6f}"] = item
        if is_eligible:
            eligible.append(margin)
    selected_margin = min(eligible) if eligible else None
    result = {
        "study": "R1 independent bank-specific margin calibration",
        "screen": screen,
        "pool": list(CALIBRATION_POOL),
        "margin_grid_results": grid,
        "eligible_margins": eligible,
        "selected_margin_rel": selected_margin,
        "deployment_mode": "calibrated_margin" if selected_margin is not None else "adapted_reference_fallback",
        "decision": "PASS_R1_CALIBRATION_FROZEN",
        "candidate_cache_sha256": _sha256(
            output_root / "calibration" / screen / "calibration_candidates.json"
        ),
        "test_used": False,
    }
    atomic_json(result, str(out_path))
    return result


def _evaluate_screen(
    *,
    root: Path,
    output_root: Path,
    screen: str,
    bank: Mapping[str, Any],
    calibration: Mapping[str, Any],
    cfg: Any,
    cache: Any,
    A: Sequence[Any],
    requested: torch.device,
    safe_mode: str,
    c1_bank: Mapping[str, Mapping[str, torch.Tensor]],
    resume: bool,
) -> Dict[str, Any]:
    out_path = output_root / "evaluation" / screen / "r1_cases.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.is_file():
        if not resume:
            raise RuntimeError(f"Existing R1 evaluation requires --resume: {out_path}")
        result = json.loads(out_path.read_text(encoding="utf-8"))
    else:
        result = {
            "study": "R1 held-out target evaluation",
            "screen": screen,
            "pool": list(TARGET_POOL),
            "calibration_sha256": _sha256(
                output_root / "calibration" / screen / "calibration_result.json"
            ),
            "records": {},
            "selection_uses_check": False,
            "selection_uses_test": False,
            "test_opened_only_after_final_model_fixed": True,
            "complete": False,
        }
    records: MutableMapping[str, Any] = result["records"]
    L = int(cfg.main.task.L)
    selected_margin = calibration["selected_margin_rel"]
    fallback = calibration["deployment_mode"] == "adapted_reference_fallback"
    started = time.perf_counter()
    for case_no, (cid, H, K) in enumerate(_jobs(TARGET_POOL), 1):
        Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(
            cfg, cache, cid, H, K
        )
        case_key = f"c{cid}_h{H}_k{K}_b{tier}"
        if case_key in records and records[case_key].get("complete"):
            continue
        input_dim = int(Xs.shape[-1])
        feasible = {
            idx
            for idx, spec in enumerate(A)
            if is_feasible(spec, cfg.main.budget, tier, L, input_dim, H)
        }
        planned = _planned_case_candidates(screen, feasible)
        if fallback:
            planned = [item for item in planned if item["token"] == "PT_A57_A57"]
        target_seed = _target_seed(cid, H, K)
        rows: List[Dict[str, Any]] = []
        models: Dict[str, torch.nn.Module] = {}
        for item in planned:
            idx = int(item["arch_idx"])
            spec = A[idx]
            actual = candidate_device(spec, requested, safe_mode)
            with candidate_backend_context(spec, actual, safe_mode):
                model = _load_source_model(
                    root=root,
                    bank=bank,
                    c1_bank=c1_bank,
                    token=item["token"],
                    idx=idx,
                    A=A,
                    H=H,
                    input_dim=input_dim,
                    L=L,
                    device=actual,
                )
                _adapt(model, Xs, ys, target_seed)
                validation = eval_metrics(model, Xv, yv)
                synchronize_if_cuda(actual)
            params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
            rows.append(
                {
                    **item,
                    "arch_key": spec.arch_key,
                    "family": spec.family,
                    "params": params,
                    "flops": flops,
                    "target_seed": target_seed,
                    "validation": validation,
                }
            )
            models[item["token"]] = model

        if fallback:
            selector = {
                "selected_token": "PT_A57_A57",
                "selected_arch_idx": ANCHOR_IDX,
                "switched_from_pt_anchor": False,
                "margin_rel": None,
                "deployment_mode": "adapted_reference_fallback",
            }
        else:
            selector = _select(rows, float(selected_margin))
            selector["deployment_mode"] = "calibrated_margin"
        selected_token = selector["selected_token"]
        selected_row = next(r for r in rows if r["token"] == selected_token)
        pt_row = next(r for r in rows if r["token"] == "PT_A57_A57")
        selected_model = models[selected_token]
        pt_model = models["PT_A57_A57"]

        # Selection is now frozen. Check is reporting-only, and Test is first
        # materialized at this exact point.
        selected_check = eval_metrics(selected_model, Xc, yc)
        pt_check = eval_metrics(pt_model, Xc, yc)
        Xt, yt = get_test_only(cfg, cache, cid, H, K)
        selected_test = eval_metrics(selected_model, Xt, yt)
        pt_test = eval_metrics(pt_model, Xt, yt)
        tier_cfg = getattr(cfg.main.budget, tier)
        limit_ok = bool(
            float(selected_row["params"]) <= float(tier_cfg.params)
            and float(selected_row["flops"]) <= float(tier_cfg.flops)
        )
        record = {
            "complete": True,
            "case_key": case_key,
            "center_id": cid,
            "center_type": ctype,
            "budget_tier": tier,
            "H": H,
            "K": K,
            "target_seed": target_seed,
            "candidate_count": len(rows),
            "candidate_validations": rows,
            "selector": selector,
            "selected": {
                **{k: selected_row[k] for k in ("token", "arch_idx", "arch_key", "family", "params", "flops")},
                "check": selected_check,
                "test": selected_test,
            },
            "pt_ft": {
                **{k: pt_row[k] for k in ("token", "arch_idx", "arch_key", "family", "params", "flops")},
                "check": pt_check,
                "test": pt_test,
            },
            "deployment_limit_satisfied": limit_ok,
            "selection_uses_check": False,
            "selection_uses_test": False,
            "test_opened_after_selection": True,
        }
        records[case_key] = record
        result["completed_records"] = len(records)
        atomic_json(result, str(out_path))
        print(
            f"[R1][{screen}][heldout] case={case_no}/80 {case_key} "
            f"selected={selected_token} test_mse={selected_test['weighted_mse']:.8g}",
            flush=True,
        )
        for model in models.values():
            del model
        gc.collect()
        if requested.type == "cuda":
            torch.cuda.empty_cache()
    result["complete"] = len(records) == 80 and all(r.get("complete") for r in records.values())
    result["elapsed_seconds"] = float(time.perf_counter() - started)
    atomic_json(result, str(out_path))
    return result


def _summarize_screen(screen: str, evaluation: Mapping[str, Any], calibration: Mapping[str, Any]) -> Dict[str, Any]:
    records = evaluation["records"]
    gains: Dict[str, float] = {}
    wins = 0
    reference_retained = 0
    beneficial = 0
    harmful = 0
    selections: Counter[str] = Counter()
    selected_configurations: Counter[str] = Counter()
    selected_mse: List[float] = []
    pt_mse: List[float] = []
    limit_ok: List[bool] = []
    for key, rec in records.items():
        proposed = float(rec["selected"]["test"]["weighted_mse"])
        reference = float(rec["pt_ft"]["test"]["weighted_mse"])
        gain = _relative_gain(proposed, reference)
        gains[key] = gain
        selected_mse.append(proposed)
        pt_mse.append(reference)
        wins += int(proposed < reference)
        switched = bool(rec["selector"]["switched_from_pt_anchor"])
        reference_retained += int(not switched)
        beneficial += int(switched and gain > 1e-6)
        harmful += int(switched and gain <= 1e-6)
        selections[str(rec["selected"]["token"])] += 1
        selected_configurations[f"A{int(rec['selected']['arch_idx'])}"] += 1
        limit_ok.append(bool(rec["deployment_limit_satisfied"]))
    alternative_selected = len(records) - reference_retained
    ci = _center_bootstrap(records, gains, _bootstrap_seed(screen))
    return {
        "screen": screen,
        "screening_pool_identity": SCREENING_POOLS[screen],
        "retained_indexed_configurations": list(SCREENS[screen]),
        "executable_architecture_count": {"S0": 5, "S1": 1, "S2": 3}[screen],
        "candidate_bank_identities": _candidate_identities(screen),
        "candidate_bank_size": len(_candidate_identities(screen)),
        "calibrated_tau": calibration["selected_margin_rel"],
        "calibration_deployment_mode": calibration["deployment_mode"],
        "pt_ft_mean_test_mse": float(np.mean(pt_mse)),
        "msa_dti_mean_test_mse": float(np.mean(selected_mse)),
        "mean_paired_mse_reduction_vs_pt_ft": ci["mean"],
        "mse_win_rate_vs_pt_ft": float(wins / len(records)),
        "center_cluster_bootstrap_95_ci": [ci["ci_low"], ci["ci_high"]],
        "bootstrap": ci,
        "reference_retained_cases": reference_retained,
        "alternative_selected_cases": alternative_selected,
        "beneficial_alternatives": beneficial,
        "harmful_alternatives": harmful,
        "all_case_harmful_selection_rate": float(harmful / len(records)),
        "conditional_harmful_selection_rate": float(harmful / alternative_selected) if alternative_selected else 0.0,
        "deployment_limit_satisfaction": float(np.mean(limit_ok)),
        "selected_candidate_counts": dict(sorted(selections.items())),
        "selected_configuration_counts": dict(sorted(selected_configurations.items())),
        "N_centers": 20,
        "N_cases": 80,
    }


def _write_summary_outputs(output_root: Path, summaries: Sequence[Mapping[str, Any]]) -> None:
    csv_path = output_root / "r1_end_to_end_screening_stability.csv"
    rows = []
    for item in summaries:
        ci_low, ci_high = item["center_cluster_bootstrap_95_ci"]
        rows.append(
            {
                "Screen": item["screen"],
                "Retained configurations": "; ".join(f"A{x}" for x in item["retained_indexed_configurations"]) or "reference fallback only",
                "Candidate-bank size": item["candidate_bank_size"],
                "Calibrated tau": item["calibrated_tau"] if item["calibrated_tau"] is not None else "no eligible margin / reference fallback",
                "PT+FT mean test MSE": item["pt_ft_mean_test_mse"],
                "MSA-DTI mean test MSE": item["msa_dti_mean_test_mse"],
                "Mean paired MSE reduction vs PT+FT": item["mean_paired_mse_reduction_vs_pt_ft"],
                "95% CI low": ci_low,
                "95% CI high": ci_high,
                "MSE win rate": item["mse_win_rate_vs_pt_ft"],
                "Reference retained": item["reference_retained_cases"],
                "Alternative selected": item["alternative_selected_cases"],
                "Beneficial alternatives": item["beneficial_alternatives"],
                "Harmful / 80": item["harmful_alternatives"],
                "All-case harmful rate": item["all_case_harmful_selection_rate"],
                "Conditional harmful rate": item["conditional_harmful_selection_rate"],
                "Limit satisfaction": item["deployment_limit_satisfaction"],
                "Selected candidate counts": json.dumps(item["selected_candidate_counts"], sort_keys=True),
                "Selected configuration counts": json.dumps(item["selected_configuration_counts"], sort_keys=True),
            }
        )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    md = [
        "| Screen | Retained configurations | Candidate-bank size | Calibrated tau | Mean paired MSE reduction vs PT+FT | 95% CI | MSE win rate | Alternative selected | Harmful / 80 | Conditional harmful rate | Limit satisfaction |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summaries:
        retained = ", ".join(f"A{x}" for x in item["retained_indexed_configurations"]) or "reference fallback only"
        tau = item["calibrated_tau"] if item["calibrated_tau"] is not None else "no eligible / fallback"
        lo, hi = item["center_cluster_bootstrap_95_ci"]
        md.append(
            f"| {item['screen']} | {retained} | {item['candidate_bank_size']} | {tau} | "
            f"{100 * item['mean_paired_mse_reduction_vs_pt_ft']:.3f}% | "
            f"[{100 * lo:.3f}%, {100 * hi:.3f}%] | {100 * item['mse_win_rate_vs_pt_ft']:.2f}% | "
            f"{item['alternative_selected_cases']} | {item['harmful_alternatives']} | "
            f"{100 * item['conditional_harmful_selection_rate']:.2f}% | "
            f"{100 * item['deployment_limit_satisfaction']:.2f}% |"
        )
    _atomic_write_text(output_root / "r1_end_to_end_screening_stability_table.md", "\n".join(md) + "\n")


def _verify(
    *,
    root: Path,
    output_root: Path,
    protocol_sha256: str,
    banks: Mapping[str, Mapping[str, Any]],
    calibrations: Mapping[str, Mapping[str, Any]],
    evaluations: Mapping[str, Mapping[str, Any]],
    summaries: Sequence[Mapping[str, Any]],
    tracked_before: Mapping[str, str],
) -> Dict[str, Any]:
    checks: Dict[str, bool] = {}
    checks["protocol_hash_bound"] = _sha256(output_root / "protocol_manifest.json") == protocol_sha256
    checks["banks_complete"] = all(b.get("decision") == "PASS_R1_BANK_FROZEN" for b in banks.values())
    checks["bank_identities_exact"] = all(
        b.get("candidate_identities") == _candidate_identities(screen) for screen, b in banks.items()
    )
    checks["S1_reference_only"] = banks["S1"]["candidate_identities"] == _candidate_identities("S1")
    checks["S2_A59_source_trained"] = all(
        f"h{H}_a59" in banks["S2"]["assets"]
        and banks["S2"]["assets"][f"h{H}_a59"]["provenance"]
        == "R1_independent_PT_recipe_source_training"
        for H in H_LIST
    )
    checks["calibration_complete_test_unused"] = all(
        c.get("decision") == "PASS_R1_CALIBRATION_FROZEN" and not c.get("test_used")
        for c in calibrations.values()
    )
    checks["smallest_eligible_or_fallback"] = all(
        (
            c["selected_margin_rel"] == min(c["eligible_margins"])
            if c["eligible_margins"]
            else c["selected_margin_rel"] is None
            and c["deployment_mode"] == "adapted_reference_fallback"
        )
        for c in calibrations.values()
    )
    checks["heldout_cases_exact"] = all(
        e.get("complete") and len(e.get("records", {})) == 80 for e in evaluations.values()
    )
    key_sets = [set(e["records"]) for e in evaluations.values()]
    checks["same_heldout_cases_all_screens"] = bool(key_sets) and all(keys == key_sets[0] for keys in key_sets)
    checks["test_isolation"] = all(
        not rec.get("selection_uses_check")
        and not rec.get("selection_uses_test")
        and rec.get("test_opened_after_selection")
        for e in evaluations.values()
        for rec in e["records"].values()
    )
    checks["deployment_limits_satisfied"] = all(
        item["deployment_limit_satisfaction"] == 1.0 for item in summaries
    )
    checks["summary_counts_consistent"] = all(
        item["reference_retained_cases"] + item["alternative_selected_cases"] == 80
        and item["beneficial_alternatives"] + item["harmful_alternatives"]
        == item["alternative_selected_cases"]
        and sum(item["selected_candidate_counts"].values()) == 80
        and sum(item["selected_configuration_counts"].values()) == 80
        for item in summaries
    )
    tracked_after = _tracked_snapshot(root)
    changed = {
        path: {"before": tracked_before.get(path), "after": tracked_after.get(path)}
        for path in sorted(set(tracked_before) | set(tracked_after))
        if tracked_before.get(path) != tracked_after.get(path)
    }
    checks["canonical_tracked_files_unchanged_during_R1"] = not changed
    repo_verification = _run_capture((sys.executable, "scripts/verify_repository.py"), root)
    _atomic_write_text(output_root / "repository_verification.txt", repo_verification["output"])
    checks["repository_verification_exit_zero"] = repo_verification["exit_code"] == 0
    result = {
        "decision": "PASS_R1_COMPLETE_AND_AUDITED" if all(checks.values()) else "FAIL_R1_AUDIT",
        "checks": checks,
        "tracked_file_changes_during_R1": changed,
        "repository_verification": {
            "command": ["python", "scripts/verify_repository.py"],
            "exit_code": repo_verification["exit_code"],
            "output_file": "repository_verification.txt",
        },
        "test_used_for_upstream_decision": False,
        "canonical_results_modified_during_R1": bool(changed),
    }
    atomic_json(result, str(output_root / "verification.json"))
    return result


def _write_report(
    output_root: Path,
    protocol: Mapping[str, Any],
    summaries: Sequence[Mapping[str, Any]],
    verification: Mapping[str, Any],
    runtime: Mapping[str, Any],
) -> None:
    lines = [
        "# R1 End-to-End Screening Stability Report",
        "",
        "## Material Passport",
        "",
        "- Artifact type: controlled diagnostic experiment result",
        f"- Protocol: `{PROTOCOL_VERSION}`",
        f"- Repository commit: `{protocol['repository']['commit']}`",
        f"- Verification status: `{verification['decision']}`",
        "- Test isolation: held-out Test was materialized only after per-case validation selection",
        "",
        "## Pre-run audit",
        "",
        "The frozen space contains 66 indexed configurations, with A57 as the protected reference. "
        "The screening rule retains a configuration when either screening evidence count reaches two. "
        "S0, S1, and S2 are treated as fixed inputs; no screening is rerun and no hyperparameter is retuned.",
        "",
        "## Fixed pools and roles",
        "",
        f"- Source training: centers 0--19, data seed {DATA_SEED}, seed offset 0.",
        f"- Shared bank-specific calibration: centers 940--959, seed offset {CALIBRATION_POOL[2]}.",
        f"- R1 held-out evaluation: centers 1180--1199, seed offset {TARGET_POOL[2]}, master seed {DATA_SEED + TARGET_POOL[2]}.",
        "- Held-out Test was not used in source training, calibration, deployment filtering, adaptation, or selection.",
        "",
        "## Results",
        "",
        (output_root / "r1_end_to_end_screening_stability_table.md").read_text(encoding="utf-8").strip(),
        "",
        "## Candidate banks and calibration",
        "",
    ]
    for item in summaries:
        retained = ", ".join(f"A{x}" for x in item["retained_indexed_configurations"]) or "none"
        lines.extend(
            [
                f"### {item['screen']}",
                "",
                f"- Retained indexed configurations: {retained}.",
                f"- Candidate-bank size: {item['candidate_bank_size']}.",
                f"- Candidate identities: {', '.join(x['token'] for x in item['candidate_bank_identities'])}.",
                f"- Calibration: {item['calibrated_tau'] if item['calibrated_tau'] is not None else 'no eligible margin; adapted-reference fallback'}.",
                f"- Selected candidate counts: `{json.dumps(item['selected_candidate_counts'], sort_keys=True)}`.",
                f"- Selected configuration counts: `{json.dumps(item['selected_configuration_counts'], sort_keys=True)}`.",
                "",
            ]
        )
    lines.extend(
        [
            "## Verification and provenance",
            "",
            f"- Verification decision: `{verification['decision']}`.",
            f"- Repository verification exit code: {verification['repository_verification']['exit_code']}.",
            f"- Total runtime: {runtime['total_elapsed_seconds']:.3f} seconds.",
            f"- Protocol manifest SHA-256: `{runtime['protocol_sha256']}`.",
            "- Generated checkpoints and result hashes are listed in `artifact_hashes.json`.",
            "- No manuscript, Supplement, canonical figure/table, release tag, or pre-existing canonical result was intentionally modified.",
            f"- Tracked files changed during R1: {len(verification['tracked_file_changes_during_R1'])}.",
            "",
            "## Protocol deviations",
            "",
            "None if and only if the verification decision above is PASS. Any failed check is recorded in `verification.json` and must be treated as a deviation.",
        ]
    )
    _atomic_write_text(output_root / "R1_END_TO_END_SCREENING_STABILITY_REPORT.md", "\n".join(lines) + "\n")


def _artifact_hashes(output_root: Path) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path.name not in {"artifact_hashes.json", "artifact_hashes.sha256"}:
            hashes[path.relative_to(output_root).as_posix()] = _sha256(path)
    atomic_json(hashes, str(output_root / "artifact_hashes.json"))
    _atomic_write_text(
        output_root / "artifact_hashes.sha256",
        "".join(f"{digest}  {rel}\n" for rel, digest in hashes.items()),
    )
    return hashes


def execute(
    *,
    root: Path,
    output_root: Path,
    device: str,
    safe_mode: str,
    protocol_sha256: str,
    resume: bool,
) -> Dict[str, Any]:
    protocol = _load_protocol(output_root, protocol_sha256)
    if protocol["environment"]["device"] != device or protocol["environment"]["safe_mode"] != safe_mode:
        raise RuntimeError("Execution device/safe-mode differs from the frozen protocol manifest")
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but this Python environment has no CUDA-enabled PyTorch")
    tracked_before = _tracked_snapshot(root)
    started = time.perf_counter()
    command_record = {
        "argv": sys.argv,
        "working_directory": ".",
        "started_at_unix_s": time.time(),
        "protocol_sha256": protocol_sha256,
        "resume": resume,
    }
    atomic_json(command_record, str(output_root / "execution_command.json"))

    # Upstream stages see source plus calibration only. The held-out R1 target
    # pool is not generated until all three calibration files are frozen.
    cfg_cal, cache_cal, A_cal, requested_cal, resolved_safe = build_runtime(
        device, safe_mode, (CALIBRATION_POOL,)
    )
    if resolved_safe != safe_mode:
        raise RuntimeError("Safe-mode normalization drifted from the frozen manifest")
    c1_path = root / BANK_CFG.c1_bank_path
    _meta, c1_bank = load_weight_bank(str(c1_path), map_location="cpu")
    banks: Dict[str, Any] = {}
    calibrations: Dict[str, Any] = {}
    phase_runtime: Dict[str, float] = {}
    for screen in SCREENS:
        phase_start = time.perf_counter()
        banks[screen] = _build_bank(
            root=root,
            output_root=output_root,
            screen=screen,
            cfg=cfg_cal,
            cache=cache_cal,
            A=A_cal,
            requested=requested_cal,
            safe_mode=safe_mode,
            resume=resume,
        )
        cache_obj = _candidate_cache(
            root=root,
            output_root=output_root,
            screen=screen,
            bank=banks[screen],
            cfg=cfg_cal,
            cache=cache_cal,
            A=A_cal,
            requested=requested_cal,
            safe_mode=safe_mode,
            c1_bank=c1_bank,
            resume=resume,
        )
        calibrations[screen] = _calibrate(screen, cache_obj, output_root)
        banks[screen]["calibration_pool_used"] = True
        atomic_json(banks[screen], str(output_root / "banks" / screen / "bank_manifest.json"))
        phase_runtime[f"{screen}_bank_and_calibration_seconds"] = time.perf_counter() - phase_start

    del cache_cal, cfg_cal, A_cal
    gc.collect()
    if requested_cal.type == "cuda":
        torch.cuda.empty_cache()

    cfg_target, cache_target, A_target, requested_target, resolved_safe = build_runtime(
        device, safe_mode, (TARGET_POOL,)
    )
    expected_types = {
        int(row["center_id"]): row["center_type"]
        for row in protocol["target_evaluation"]["center_seed_records"]
    }
    actual_types = {
        cid: cache_target.centers[cid].center_type
        for cid in range(TARGET_POOL[0], TARGET_POOL[0] + TARGET_POOL[1])
    }
    if actual_types != expected_types:
        raise RuntimeError("Generated R1 center-type schedule differs from the frozen seed manifest")

    evaluations: Dict[str, Any] = {}
    summaries: List[Dict[str, Any]] = []
    for screen in SCREENS:
        phase_start = time.perf_counter()
        evaluations[screen] = _evaluate_screen(
            root=root,
            output_root=output_root,
            screen=screen,
            bank=banks[screen],
            calibration=calibrations[screen],
            cfg=cfg_target,
            cache=cache_target,
            A=A_target,
            requested=requested_target,
            safe_mode=safe_mode,
            c1_bank=c1_bank,
            resume=resume,
        )
        summaries.append(_summarize_screen(screen, evaluations[screen], calibrations[screen]))
        phase_runtime[f"{screen}_heldout_evaluation_seconds"] = time.perf_counter() - phase_start

    atomic_json({"screens": summaries}, str(output_root / "r1_end_to_end_screening_stability.json"))
    _write_summary_outputs(output_root, summaries)
    runtime = {
        "protocol_sha256": protocol_sha256,
        "total_elapsed_seconds": float(time.perf_counter() - started),
        "phase_runtime_seconds": phase_runtime,
        "completed_at_unix_s": time.time(),
    }
    atomic_json(runtime, str(output_root / "runtime.json"))
    verification = _verify(
        root=root,
        output_root=output_root,
        protocol_sha256=protocol_sha256,
        banks=banks,
        calibrations=calibrations,
        evaluations=evaluations,
        summaries=summaries,
        tracked_before=tracked_before,
    )
    _write_report(output_root, protocol, summaries, verification, runtime)
    hashes = _artifact_hashes(output_root)
    final = {
        "decision": verification["decision"],
        "output_root": str(output_root),
        "summary_csv": str(output_root / "r1_end_to_end_screening_stability.csv"),
        "report": str(output_root / "R1_END_TO_END_SCREENING_STABILITY_REPORT.md"),
        "artifact_count": len(hashes),
        "elapsed_seconds": runtime["total_elapsed_seconds"],
    }
    print(json.dumps(final, ensure_ascii=False, indent=2), flush=True)
    return final


def finalize_existing_artifacts(
    *,
    root: Path,
    output_root: Path,
    original_protocol_sha256: str,
) -> Dict[str, Any]:
    """Repair public-path metadata and re-audit an already completed R1 run.

    This operation never constructs a data runtime, trains/adapts a model, or
    recomputes a scientific metric.  It is deliberately limited to path
    sanitization, report regeneration, hashing, and repository verification.
    """
    manifest_path = output_root / "protocol_manifest.json"
    if _sha256(manifest_path) != original_protocol_sha256:
        raise RuntimeError("Existing protocol manifest does not match the executed protocol hash")

    protocol = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed_fields = {
        "frozen_inputs.paired_c1_bank.path": protocol["frozen_inputs"]["paired_c1_bank"]["path"],
        "frozen_inputs.external_source_manifest.path": protocol["frozen_inputs"]["external_source_manifest"]["path"],
        "isolation.output_root": protocol["isolation"]["output_root"],
    }
    protocol["frozen_inputs"]["paired_c1_bank"]["path"] = BANK_CFG.c1_bank_path
    protocol["frozen_inputs"]["external_source_manifest"]["path"] = BANK_CFG.external_source_manifest
    protocol["isolation"]["output_root"] = f"results/{EXPECTED_OUTPUT_NAME}"
    atomic_json(protocol, str(manifest_path))
    public_protocol_sha256 = _sha256(manifest_path)
    _atomic_write_text(
        output_root / "protocol_manifest.sha256",
        f"{public_protocol_sha256}  protocol_manifest.json\n",
    )

    command_path = output_root / "execution_command.json"
    command_record = json.loads(command_path.read_text(encoding="utf-8"))
    original_working_directory = command_record.get("working_directory")
    command_record["working_directory"] = "."
    command_record["executed_protocol_sha256"] = original_protocol_sha256
    command_record["public_protocol_sha256"] = public_protocol_sha256
    atomic_json(command_record, str(command_path))

    sanitization = {
        "decision": "PASS_ARTIFACT_ONLY_PATH_SANITIZATION",
        "scientific_values_changed": False,
        "training_or_evaluation_rerun": False,
        "executed_protocol_sha256": original_protocol_sha256,
        "public_protocol_sha256": public_protocol_sha256,
        "changed_fields": sorted(changed_fields),
        "execution_command_changed_fields": ["working_directory"],
        "reason": "replace machine-local absolute paths with repository-relative public paths",
    }
    if not original_working_directory:
        raise RuntimeError("Execution command lacks the original working-directory record")
    atomic_json(sanitization, str(output_root / "artifact_sanitization.json"))

    banks = {
        screen: json.loads((output_root / "banks" / screen / "bank_manifest.json").read_text(encoding="utf-8"))
        for screen in SCREENS
    }
    calibrations = {
        screen: json.loads(
            (output_root / "calibration" / screen / "calibration_result.json").read_text(encoding="utf-8")
        )
        for screen in SCREENS
    }
    evaluations = {
        screen: json.loads((output_root / "evaluation" / screen / "r1_cases.json").read_text(encoding="utf-8"))
        for screen in SCREENS
    }
    summaries = json.loads(
        (output_root / "r1_end_to_end_screening_stability.json").read_text(encoding="utf-8")
    )["screens"]
    runtime_path = output_root / "runtime.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["executed_protocol_sha256"] = original_protocol_sha256
    runtime["protocol_sha256"] = public_protocol_sha256
    runtime["artifact_only_refinalization"] = True
    atomic_json(runtime, str(runtime_path))

    # Remove the prior machine-local verification command before the public
    # repository checker scans the completed result directory.
    atomic_json(
        {"decision": "PENDING_ARTIFACT_ONLY_REAUDIT"},
        str(output_root / "verification.json"),
    )
    tracked_now = _tracked_snapshot(root)
    verification = _verify(
        root=root,
        output_root=output_root,
        protocol_sha256=public_protocol_sha256,
        banks=banks,
        calibrations=calibrations,
        evaluations=evaluations,
        summaries=summaries,
        tracked_before=tracked_now,
    )
    verification["checks"]["execution_protocol_original_hash_recorded"] = (
        command_record["executed_protocol_sha256"] == original_protocol_sha256
    )
    verification["decision"] = (
        "PASS_R1_COMPLETE_AND_AUDITED"
        if all(verification["checks"].values())
        else "FAIL_R1_AUDIT"
    )
    atomic_json(verification, str(output_root / "verification.json"))
    _write_report(output_root, protocol, summaries, verification, runtime)
    hashes = _artifact_hashes(output_root)
    final = {
        "decision": verification["decision"],
        "output_root": f"results/{EXPECTED_OUTPUT_NAME}",
        "summary_csv": f"results/{EXPECTED_OUTPUT_NAME}/r1_end_to_end_screening_stability.csv",
        "report": f"results/{EXPECTED_OUTPUT_NAME}/R1_END_TO_END_SCREENING_STABILITY_REPORT.md",
        "artifact_count": len(hashes),
        "elapsed_seconds": runtime["total_elapsed_seconds"],
        "scientific_rerun": False,
    }
    print(json.dumps(final, ensure_ascii=False, indent=2), flush=True)
    return final


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument(
        "--output-root",
        default=f"results/{EXPECTED_OUTPUT_NAME}",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--safe-mode",
        choices=("default", "gru-native", "gru-cpu"),
        default="default",
    )
    gate = parser.add_mutually_exclusive_group(required=True)
    gate.add_argument("--prepare-only", action="store_true")
    gate.add_argument("--execute", action="store_true")
    gate.add_argument("--finalize-existing-artifacts", action="store_true")
    parser.add_argument("--protocol-sha256")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume only after a crashed/interrupted run and separate user confirmation.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = Path(args.root).resolve()
    output_root = _ensure_output_root(root, Path(args.output_root))
    if args.prepare_only:
        if args.protocol_sha256 or args.resume:
            raise ValueError("--prepare-only cannot be combined with --protocol-sha256 or --resume")
        prepare(root, output_root, args.device, args.safe_mode)
        return 0
    if args.finalize_existing_artifacts:
        if args.resume:
            raise ValueError("--finalize-existing-artifacts cannot be combined with --resume")
        if not args.protocol_sha256:
            raise ValueError("--finalize-existing-artifacts requires the executed protocol SHA-256")
        finalize_existing_artifacts(
            root=root,
            output_root=output_root,
            original_protocol_sha256=args.protocol_sha256,
        )
        return 0
    if not args.protocol_sha256:
        raise ValueError("--execute requires --protocol-sha256 from the prepare gate")
    execute(
        root=root,
        output_root=output_root,
        device=args.device,
        safe_mode=args.safe_mode,
        protocol_sha256=args.protocol_sha256,
        resume=args.resume,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
