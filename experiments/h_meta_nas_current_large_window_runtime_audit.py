"""Five-repeat H-Meta-NAS target-side runtime audit on the frozen large-window protocol.

This is a timing-only experiment.  It loads the frozen H-Meta-NAS source bank
and never retrains it or evaluates held-out prediction performance.  The local
data accessor is a faithful extraction of the raw-timeline split algorithm in
Git commit 16fe4b8, the version bound to the formal H-Meta-NAS performance
artifact.  It intentionally does not use the active K/80/60/200 accessor.
"""

from __future__ import annotations

import argparse
import copy
import csv
import gc
import hashlib
import json
import os
import platform
import random
import socket
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.methods.h_meta_nas_cfg import CFG, config_dict
from core.data.center_api import _allocate_raw_segments, _normalize_value_channels_from_support, build_feature_matrix, make_windows
from core.methods.ours.stage2_runtime import candidate_backend_context, candidate_device, synchronize_if_cuda
from core.space import build_model, profile_arch
from experiments.h_meta_nas_recovery import _load_torch, _mutants, _state_key
from shared.evaluation.common import build_runtime, eval_metrics, feasible_indices, file_sha256, seed_all


STUDY = "h_meta_nas_current_large_window_runtime_audit_v1"
HISTORICAL_PROTOCOL_COMMIT = "16fe4b8cb09500ebd94d14bb5257bb8a2d7ac0ba"
EXPECTED_REPEATS = 5
EXPECTED_CASES = 80
EXPECTED_CANDIDATES = 12
DEFAULT_OUTPUT = ROOT / "results" / "audited_provenance" / STUDY
DEFAULT_BANK = ROOT / "results" / CFG.protocol_version / "source_meta_bank.pt"
DEFAULT_FORMAL = ROOT / "results" / CFG.protocol_version / "h_meta_nas_formal.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return file_sha256(str(path)).lower()


def atomic_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path}")
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def normalized(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True))


def git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def script_sha256() -> str:
    digest = hashlib.sha256()
    with Path(__file__).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def synchronize(device: torch.device) -> None:
    synchronize_if_cuda(device)


def environment(device: torch.device) -> dict[str, Any]:
    properties = torch.cuda.get_device_properties(device)
    return {
        "captured_at_utc": utc_now(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "numpy": np.__version__,
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "cuda_device_name": torch.cuda.get_device_name(device),
        "cuda_device_index": int(device.index or 0),
        "cuda_total_memory_bytes": int(properties.total_memory),
        "cuda_compute_capability": [int(properties.major), int(properties.minor)],
    }


def large_window_boundaries(*, total_steps: int, L: int, H: int, K: int) -> dict[str, tuple[int, int]]:
    """Exact raw-boundary calculation from 16fe4b8's data accessor."""
    support_steps = int(L) + int(H) + int(K) - 1
    n_support, n_validation, n_check, n_test = _allocate_raw_segments(
        total_steps=int(total_steps),
        support_steps=support_steps,
        min_eval_steps=int(L) + int(H),
        val_ratio=0.2,
        chk_ratio=0.1,
        test_ratio=0.1,
    )
    starts = (0, n_support, n_support + n_validation, n_support + n_validation + n_check)
    ends = (n_support, n_support + n_validation, n_support + n_validation + n_check, n_support + n_validation + n_check + n_test)
    return dict(zip(("support", "validation", "check", "test"), zip(starts, ends)))


def historical_large_window_case(cfg: Any, cache: Any, center_id: int, H: int, K: int) -> tuple[Any, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, dict[str, int]]:
    """Materialize only support/validation; check/test remain unopened."""
    record = cache.centers[int(center_id)]
    if record.y is None:
        raise ValueError("Center record has no target series")
    L, H, K = int(cfg.main.task.L), int(H), int(K)
    series = build_feature_matrix(cfg, record)
    bounds = large_window_boundaries(total_steps=int(series.shape[0]), L=L, H=H, K=K)
    counts = {name: int(right - left - L - H + 1) for name, (left, right) in bounds.items()}
    expected = {
        (1, 10): {"support": 10, "validation": 1351, "check": 628, "test": 627},
        (1, 20): {"support": 20, "validation": 1346, "check": 625, "test": 625},
        (4, 10): {"support": 10, "validation": 1346, "check": 624, "test": 624},
        (4, 20): {"support": 20, "validation": 1342, "check": 621, "test": 621},
    }[(H, K)]
    if counts != expected:
        raise RuntimeError(f"Large-window count mismatch for H={H}, K={K}: {counts} != {expected}")
    support_left, support_right = bounds["support"]
    validation_left, validation_right = bounds["validation"]
    Xs, ys = make_windows(series[support_left:support_right], record.y[support_left:support_right], L=L, H=H)
    Xv, yv = make_windows(series[validation_left:validation_right], record.y[validation_left:validation_right], L=L, H=H)
    if bool(getattr(cfg.main.task, "normalize_values_from_support", False)):
        Xs, Xv = _normalize_value_channels_from_support(
            (Xs, Xv), k_max=int(cfg.main.sim.k_max), include_mask=bool(cfg.main.task.include_mask)
        )
    return record, Xs, ys, Xv, yv, counts


def adapt_and_validate(*, spec: Any, state: Mapping[str, torch.Tensor], Xs: torch.Tensor, ys: torch.Tensor, Xv: torch.Tensor, yv: torch.Tensor, H: int, L: int, input_dim: int, device: torch.device, seed: int) -> tuple[torch.nn.Module, dict[str, float]]:
    actual = candidate_device(spec, device, "gru-native")
    with candidate_backend_context(spec, actual, "gru-native"):
        seed_all(seed, actual)
        model = build_model(spec, input_dim=input_dim, H=H, L=L, device=str(actual))
        model.load_state_dict(state, strict=True)
        optimizer = torch.optim.SGD(model.parameters(), lr=CFG.target_lr)
        support_x, support_y = Xs.to(actual), ys.to(actual)
        model.train()
        for _ in range(CFG.target_steps):
            optimizer.zero_grad(set_to_none=True)
            loss = ((model(support_x) - support_y) ** 2).mean()
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite target MSE")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), CFG.target_grad_clip)
            optimizer.step()
        validation = eval_metrics(model, Xv, yv)
        synchronize(actual)
        return model, validation


def execute_target_case(*, bank: Mapping[str, Any], cfg: Any, architectures: Sequence[Any], device: torch.device, Xs: torch.Tensor, ys: torch.Tensor, Xv: torch.Tensor, yv: torch.Tensor, tier: str, H: int, K: int, center_id: int, L: int, input_dim: int) -> dict[str, Any]:
    seed = CFG.train_seed + 1009 * int(center_id) + 37 * int(H) + 53 * int(K)
    rng = random.Random(seed)
    feasible = feasible_indices(cfg, architectures, tier, L, input_dim, H)
    if not feasible:
        raise RuntimeError("No feasible candidate")
    population = rng.sample(feasible, min(CFG.population_size, len(feasible)))
    visited: set[int] = set()
    evaluated: list[dict[str, Any]] = []
    best: tuple[tuple[float, float, float, int], dict[str, Any]] | None = None
    best_state: dict[str, torch.Tensor] | None = None
    for generation in range(CFG.generations):
        generation_rows: list[dict[str, Any]] = []
        for arch_idx in population:
            if arch_idx in visited:
                continue
            model, validation = adapt_and_validate(
                spec=architectures[arch_idx], state=bank["states"][_state_key(H, arch_idx)],
                Xs=Xs, ys=ys, Xv=Xv, yv=yv, H=H, L=L, input_dim=input_dim,
                device=device, seed=seed + arch_idx + 10000 * generation,
            )
            params, flops = profile_arch(architectures[arch_idx], L=L, input_dim=input_dim, H=H)
            row = {"generation": generation, "arch_idx": int(arch_idx), "validation": validation, "params": float(params), "flops": float(flops)}
            evaluated.append(row)
            generation_rows.append(row)
            visited.add(arch_idx)
            score = (float(validation["weighted_mse"]), float(params), float(flops), int(arch_idx))
            if best is None or score < best[0]:
                best = (score, row)
                best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
            del model
            gc.collect()
            torch.cuda.empty_cache()
        if generation + 1 < CFG.generations:
            parents = sorted(generation_rows, key=lambda row: (row["validation"]["weighted_mse"], row["arch_idx"]))[:CFG.parent_count]
            population = []
            for parent in parents:
                for candidate in _mutants(parent["arch_idx"], feasible, visited | set(population), architectures, rng):
                    if candidate not in population:
                        population.append(candidate)
                        break
            remaining = [idx for idx in feasible if idx not in visited and idx not in population]
            rng.shuffle(remaining)
            population += remaining[:max(0, CFG.population_size - len(population))]
    if best is None or best_state is None:
        raise RuntimeError("Search did not select a candidate")
    return {"seed": seed, "feasible_candidate_count": len(feasible), "candidate_count": len(evaluated), "selected": best[1], "selected_state": best_state}


def preflight(bank_path: Path, formal_path: Path) -> tuple[Mapping[str, Any], Mapping[str, Any], dict[str, Any]]:
    bank, formal = _load_torch(bank_path), json.loads(formal_path.read_text(encoding="utf-8"))
    if not bank.get("complete") or int(bank.get("completed_iterations", -1)) != CFG.source_outer_iterations:
        raise RuntimeError("Frozen source bank is incomplete")
    if normalized(bank.get("protocol")) != normalized(config_dict()):
        raise RuntimeError("Source-bank H-Meta configuration mismatch")
    if not formal.get("complete") or formal.get("decision") != "H_META_NAS_COMPLETE":
        raise RuntimeError("Formal H-Meta result is incomplete")
    if normalized(formal.get("protocol")) != normalized(config_dict()):
        raise RuntimeError("Formal H-Meta configuration mismatch")
    if len(formal.get("records", {})) != EXPECTED_CASES:
        raise RuntimeError("Formal result does not contain 80 cases")
    bank_hash, formal_hash = sha256(bank_path), sha256(formal_path)
    if formal.get("source_bank_sha256", "").lower() != bank_hash:
        raise RuntimeError("Formal result does not bind this source bank")
    return bank, formal, {
        "source_meta_bank_path": str(bank_path.resolve()), "source_meta_bank_sha256": bank_hash,
        "formal_performance_path": str(formal_path.resolve()), "formal_performance_sha256": formal_hash,
    }


def protocol_table() -> dict[str, dict[str, int]]:
    return {
        "H1_K10": {"support": 10, "validation": 1351, "check": 628, "test": 627},
        "H1_K20": {"support": 20, "validation": 1346, "check": 625, "test": 625},
        "H4_K10": {"support": 10, "validation": 1346, "check": 624, "test": 624},
        "H4_K20": {"support": 20, "validation": 1342, "check": 621, "test": 621},
    }


def summarize(state: Mapping[str, Any], output: Path) -> dict[str, Any]:
    rows = sorted(state["records"].values(), key=lambda row: (row["repeat"], row["case_number"]))
    repeat_rows = []
    for repeat in range(1, EXPECTED_REPEATS + 1):
        subset = [row for row in rows if row["repeat"] == repeat]
        if len(subset) != EXPECTED_CASES:
            raise RuntimeError(f"Repeat {repeat} is incomplete")
        values = np.asarray([row["online_seconds"] for row in subset], dtype=np.float64)
        repeat_rows.append({"repeat": repeat, "N_cases": len(subset), "total_seconds": float(values.sum()), "mean_seconds": float(values.mean()), "std_case_seconds": float(values.std(ddof=1))})
    means = np.asarray([row["mean_seconds"] for row in repeat_rows], dtype=np.float64)
    summary = {
        "study": STUDY,
        "decision": "PASS_CURRENT_LARGE_WINDOW_RUNTIME_AUDIT",
        "complete": True,
        "protocol": state["protocol"],
        "method": state["method"],
        "provenance": state["provenance"],
        "timing_scope": state["timing_scope"],
        "environment": state["environment"],
        "N_repeats": EXPECTED_REPEATS,
        "N_cases_per_repeat": EXPECTED_CASES,
        "repeat_results": repeat_rows,
        "five_repeat_mean_seconds": float(means.mean()),
        "five_repeat_sample_sd_seconds": float(means.std(ddof=1)),
        "manuscript_rounded": f"{means.mean():.3f} ± {means.std(ddof=1):.3f} s",
        "sanity_checks": {
            "all_repeats_have_80_cases": True,
            "case_keys_identical_across_repeats": True,
            "all_window_counts_match": True,
            "all_candidate_counts_are_12": all(row["adapted_candidate_count"] == EXPECTED_CANDIDATES for row in rows),
            "all_frozen_selections_match": all(row["selected_arch_matches_formal"] for row in rows),
            "check_materialized": False,
            "test_materialized": False,
            "check_or_test_inside_timer": False,
        },
    }
    write_csv(output / "per_case_runtime_all_repeats.csv", rows)
    write_csv(output / "per_repeat_80_case_runtime.csv", repeat_rows)
    atomic_json(summary, output / "h_meta_nas_current_large_window_runtime_manifest.json")
    return summary


def run(output: Path, bank_path: Path, formal_path: Path, device_name: str, command: str, dry_run: bool) -> dict[str, Any]:
    device = torch.device(device_name)
    if device.type != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("This audit requires a CUDA-enabled PyTorch environment")
    bank, formal, assets = preflight(bank_path, formal_path)
    cfg, cache, architectures, requested, _safe = build_runtime(device_name, "gru-native", (CFG.locked_pool,))
    if len(architectures) != CFG.architecture_count:
        raise RuntimeError("Architecture count mismatch")
    jobs = [(center_id, H, K) for center_id in range(CFG.locked_pool[0], CFG.locked_pool[0] + CFG.locked_pool[1]) for H in CFG.H_list for K in CFG.K_list]
    if len(jobs) != EXPECTED_CASES:
        raise RuntimeError("Expected exactly 80 target jobs")
    expected_keys: set[str] = set()
    for center_id, H, K in jobs:
        record, _Xs, _ys, _Xv, _yv, _counts = historical_large_window_case(cfg, cache, center_id, H, K)
        expected_keys.add(f"c{center_id}_h{H}_k{K}_b{record.tier_name}")
    if expected_keys != set(formal["records"]):
        raise RuntimeError("Large-window case keys do not match formal performance artifact")
    if dry_run:
        return {"dry_run": True, "case_count": len(jobs), "case_keys_match_formal": True, "window_counts": protocol_table(), "assets": assets, "environment": environment(requested)}

    output.mkdir(parents=True, exist_ok=True)
    state_path = output / "h_meta_nas_current_large_window_runtime_raw.json"
    immutable = {
        "study": STUDY,
        "protocol": {"historical_source_commit": HISTORICAL_PROTOCOL_COMMIT, "split_rule": "raw chronological segmentation before separate window generation", "window_counts": protocol_table(), "centers": list(range(980, 1000)), "case_keys": sorted(expected_keys)},
        "method": {"architecture_count": 66, "population_size": 6, "generations": 2, "adapted_candidates": 12, "optimizer": "SGD", "loss": "MSE", "target_updates": 50, "selection_metric": "validation weighted MSE", "selection_uses_check": False, "selection_uses_test": False},
        "provenance": {**assets, "runtime_code_path": str(Path(__file__).resolve()), "runtime_code_sha256": script_sha256(), "git_commit": git_value("rev-parse", "HEAD"), "git_worktree_dirty": bool(git_value("status", "--porcelain")), "command": command},
    }
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        for key, value in immutable.items():
            if normalized(state.get(key)) != normalized(value):
                raise RuntimeError(f"Cannot resume: immutable field changed: {key}")
    else:
        state = {**immutable, "created_at_utc": utc_now(), "environment": environment(requested), "timing_scope": {"included": ["feasible filtering and population construction", "candidate model construction", "frozen initialization loading", "two-generation search", "50 SGD/MSE updates per candidate", "validation evaluation", "final validation-only selection"], "excluded": ["source/meta training", "data construction", "check evaluation", "test evaluation", "reporting"], "cuda_synchronization": "immediately before start and immediately after final selection"}, "records": {}, "complete": False}
        atomic_json(state, state_path)

    for repeat in range(1, EXPECTED_REPEATS + 1):
        for case_number, (center_id, H, K) in enumerate(jobs, 1):
            record, Xs, ys, Xv, yv, counts = historical_large_window_case(cfg, cache, center_id, H, K)
            case_key = f"c{center_id}_h{H}_k{K}_b{record.tier_name}"
            record_key = f"r{repeat}_{case_key}"
            if record_key in state["records"]:
                continue
            synchronize(requested)
            started = time.perf_counter()
            execution = execute_target_case(bank=bank, cfg=cfg, architectures=architectures, device=requested, Xs=Xs, ys=ys, Xv=Xv, yv=yv, tier=record.tier_name, H=H, K=K, center_id=center_id, L=int(cfg.main.task.L), input_dim=int(Xs.shape[-1]))
            synchronize(requested)
            seconds = float(time.perf_counter() - started)
            selected_matches = int(execution["selected"]["arch_idx"]) == int(formal["records"][case_key]["arch_idx"])
            if execution["candidate_count"] != EXPECTED_CANDIDATES or not selected_matches:
                raise RuntimeError(f"Frozen method-identity check failed for {case_key}")
            state["records"][record_key] = {"repeat": repeat, "case_number": case_number, "case_key": case_key, "center_id": center_id, "H": H, "K": K, "budget_tier": record.tier_name, "validation_window_count": counts["validation"], "check_window_count": counts["check"], "test_window_count": counts["test"], "feasible_candidate_count": execution["feasible_candidate_count"], "adapted_candidate_count": execution["candidate_count"], "selected_arch_idx": int(execution["selected"]["arch_idx"]), "selected_arch_matches_formal": selected_matches, "target_seed": execution["seed"], "online_seconds": seconds, "cuda_synchronized_before_and_after": True, "check_materialized": False, "test_materialized": False, "selection_uses_check": False, "selection_uses_test": False}
            state["last_updated_at_utc"] = utc_now()
            atomic_json(state, state_path)
            print(f"[{STUDY}] repeat={repeat}/{EXPECTED_REPEATS} case={case_number}/{EXPECTED_CASES} {case_key} online={seconds:.6f}s", flush=True)
            del execution
            gc.collect()
            torch.cuda.empty_cache()
    state["complete"] = len(state["records"]) == EXPECTED_REPEATS * EXPECTED_CASES
    state["completed_at_utc"] = utc_now()
    atomic_json(state, state_path)
    if not state["complete"]:
        raise RuntimeError("Runtime audit incomplete")
    return summarize(state, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-meta-bank", type=Path, default=DEFAULT_BANK)
    parser.add_argument("--formal-result", type=Path, default=DEFAULT_FORMAL)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    summary = run(args.output_dir.resolve(), args.source_meta_bank.resolve(), args.formal_result.resolve(), args.device, " ".join([Path(sys.executable).name, *sys.argv]), args.dry_run)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
