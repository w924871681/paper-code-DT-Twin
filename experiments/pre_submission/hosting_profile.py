# -*- coding: utf-8 -*-
"""Measure frozen candidate inference cost on representative CPU/GPU hosts.

The experiment does not retrain or adapt a model. It profiles the seven
frozen source candidates with batch size one and writes raw/summary evidence.
"""
from __future__ import annotations

import io
import json
import os
import platform
import statistics
import time
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np
import torch

from configs.methods.pre_submission_enhancements_cfg import CFG, config_dict
from configs.methods.main_evaluation_cfg import CFG as MAIN_CFG
from core.methods.ours.paper_engine import _load_prior_model
from core.methods.ours.stage2_runtime import (
    candidate_backend_context,
    candidate_device,
    configure_stage2_runtime,
    synchronize_if_cuda,
)
from core.methods.ours.weight_bank import load_weight_bank
from core.space import build_model, profile_arch
from main_evaluation.pipeline import _load_strong_manifest, _load_strong_model
from shared.data_access import get_support_validation_check
from shared.evaluation.common import atomic_json, build_runtime, file_sha256


def _quantile(values: Sequence[float], q: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=float), q))


def _state_size_bytes(model: torch.nn.Module) -> int:
    buffer = io.BytesIO()
    torch.save({k: v.detach().cpu() for k, v in model.state_dict().items()}, buffer)
    return int(buffer.tell())


def _load_candidate(
    *,
    project_root: str,
    strong_manifest: Mapping[str, Any],
    legacy_bank: Mapping[str, Mapping[str, torch.Tensor]],
    A: Sequence[Any],
    token: str,
    arch_idx: int,
    H: int,
    input_dim: int,
    L: int,
    device: torch.device,
) -> torch.nn.Module:
    spec = A[int(arch_idx)]
    if token == "LEGACY_C1_A57":
        model, _ = _load_prior_model(
            spec=spec,
            H=int(H),
            L=int(L),
            input_dim=int(input_dim),
            bank=dict(legacy_bank),
            device=device,
        )
        return model
    return _load_strong_model(
        project_root,
        strong_manifest,
        A,
        H=int(H),
        idx=int(arch_idx),
        input_dim=int(input_dim),
        L=int(L),
        device=device,
    )


def _measure_one(
    model: torch.nn.Module,
    x: torch.Tensor,
    *,
    device: torch.device,
    warmups: int,
    timed_inferences: int,
    repeats: int,
) -> Dict[str, Any]:
    model.eval()
    x = x.to(device).contiguous()
    repeat_rows: List[Dict[str, float]] = []
    all_ms: List[float] = []

    with torch.inference_mode():
        for _ in range(int(warmups)):
            _ = model(x)
        synchronize_if_cuda(device)

        baseline_allocated = 0
        if device.type == "cuda":
            torch.cuda.empty_cache()
            synchronize_if_cuda(device)
            baseline_allocated = int(torch.cuda.memory_allocated(device))
            torch.cuda.reset_peak_memory_stats(device)

        for repeat_idx in range(int(repeats)):
            samples_ms: List[float] = []
            for _ in range(int(timed_inferences)):
                synchronize_if_cuda(device)
                started = time.perf_counter_ns()
                _ = model(x)
                synchronize_if_cuda(device)
                elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
                samples_ms.append(float(elapsed_ms))
            all_ms.extend(samples_ms)
            repeat_rows.append(
                {
                    "repeat": int(repeat_idx),
                    "mean_ms": float(np.mean(samples_ms)),
                    "median_ms": float(np.median(samples_ms)),
                    "p95_ms": _quantile(samples_ms, 0.95),
                    "std_ms": float(np.std(samples_ms, ddof=1)) if len(samples_ms) > 1 else 0.0,
                }
            )

        peak_delta_bytes = None
        if device.type == "cuda":
            synchronize_if_cuda(device)
            peak_delta_bytes = max(
                0, int(torch.cuda.max_memory_allocated(device)) - baseline_allocated
            )

    repeat_means = [row["mean_ms"] for row in repeat_rows]
    return {
        "N_samples": int(len(all_ms)),
        "N_repeats": int(len(repeat_rows)),
        "mean_ms": float(np.mean(all_ms)),
        "median_ms": float(np.median(all_ms)),
        "p95_ms": _quantile(all_ms, 0.95),
        "sample_std_ms": float(np.std(all_ms, ddof=1)) if len(all_ms) > 1 else 0.0,
        "repeat_mean_std_ms": (
            float(statistics.stdev(repeat_means)) if len(repeat_means) > 1 else 0.0
        ),
        "peak_device_memory_bytes": peak_delta_bytes,
        "repeat_rows": repeat_rows,
    }


def _device_metadata(device: torch.device) -> Dict[str, Any]:
    obj: Dict[str, Any] = {
        "requested": str(device),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torch_num_threads": int(torch.get_num_threads()),
    }
    if device.type == "cuda":
        obj.update(
            {
                "cuda_available": bool(torch.cuda.is_available()),
                "cuda_version": torch.version.cuda,
                "device_name": torch.cuda.get_device_name(device),
                "device_capability": list(torch.cuda.get_device_capability(device)),
            }
        )
    else:
        obj["device_name"] = platform.processor() or "CPU"
    return obj


def run_hosting_profile(
    project_root: str,
    out_path: str,
    *,
    devices: Iterable[str] = ("cpu", "cuda"),
    safe_mode: str = "gru-native",
    warmups: int | None = None,
    timed_inferences: int | None = None,
    repeats: int | None = None,
    smoke: bool = False,
    host_label: str | None = None,
) -> Dict[str, Any]:
    root = os.path.abspath(project_root)
    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    strong_manifest_path = os.path.join(root, CFG.strong_bank_manifest_path)
    c1_bank_path = os.path.join(root, CFG.c1_bank_path)
    strong_manifest = _load_strong_manifest(root, strong_manifest_path)
    _meta, legacy_bank = load_weight_bank(c1_bank_path, map_location="cpu")

    # Build only the locked synthetic pool and use one real case tensor per H.
    cfg, cache, A, _requested, _safe = build_runtime(
        "cpu", "default", (MAIN_CFG.locked_pool,)
    )
    L = int(cfg.main.task.L)
    warmups = int(5 if smoke else (warmups or CFG.hosting_warmups))
    timed_inferences = int(20 if smoke else (timed_inferences or CFG.hosting_timed_inferences))
    repeats = int(1 if smoke else (repeats or CFG.hosting_repeats))

    planned: List[Tuple[str, int]] = [
        ("PT_A57", CFG.anchor_arch_idx),
        ("LEGACY_C1_A57", CFG.anchor_arch_idx),
    ] + [(f"STRONG_A{idx}", int(idx)) for idx in CFG.compact_non_anchor_indices]

    result: Dict[str, Any] = {
        "study": "frozen_candidate_hosting_profile",
        "decision": "HOSTING_PROFILE_IN_PROGRESS",
        "protocol": config_dict(),
        "run_mode": "smoke" if smoke else "formal",
        "strong_bank_manifest_sha256": file_sha256(strong_manifest_path),
        "c1_bank_sha256": file_sha256(c1_bank_path),
        "selection_or_adaptation_performed": False,
        "host_label": str(host_label or platform.node() or "host"),
        "records": [],
    }

    requested_devices: List[torch.device] = []
    for text in devices:
        text = str(text).strip()
        if not text:
            continue
        dev = torch.device(text)
        if dev.type == "cuda" and not torch.cuda.is_available():
            print("[HostingProfile] CUDA unavailable; skipping CUDA profile", flush=True)
            continue
        configure_stage2_runtime(dev, safe_mode)
        requested_devices.append(dev)
    if not requested_devices:
        raise RuntimeError("No requested hosting device is available")

    result["devices"] = [_device_metadata(d) for d in requested_devices]

    for H in CFG.H_list:
        Xs, _ys, _Xv, _yv, _Xc, _yc, tier, center_type = get_support_validation_check(
            cfg,
            cache,
            CFG.hosting_profile_center_id,
            int(H),
            CFG.hosting_profile_support_size,
        )
        input_dim = int(Xs.shape[-1])
        x = Xs[: CFG.hosting_batch_size].contiguous()

        for token, idx in planned:
            spec = A[int(idx)]
            params, operations = profile_arch(spec, L=L, input_dim=input_dim, H=int(H))
            for requested_device in requested_devices:
                actual = candidate_device(spec, requested_device, safe_mode)
                with candidate_backend_context(spec, actual, safe_mode):
                    model = _load_candidate(
                        project_root=root,
                        strong_manifest=strong_manifest,
                        legacy_bank=legacy_bank,
                        A=A,
                        token=token,
                        arch_idx=idx,
                        H=int(H),
                        input_dim=input_dim,
                        L=L,
                        device=actual,
                    )
                    model_bytes = _state_size_bytes(model)
                    measured = _measure_one(
                        model,
                        x,
                        device=actual,
                        warmups=warmups,
                        timed_inferences=timed_inferences,
                        repeats=repeats,
                    )
                    row = {
                        "host_label": str(host_label or platform.node() or "host"),
                        "token": token,
                        "arch_idx": int(idx),
                        "arch_key": str(spec.arch_key),
                        "family": str(spec.family),
                        "H": int(H),
                        "input_dim": int(input_dim),
                        "L": int(L),
                        "profile_center_id": int(CFG.hosting_profile_center_id),
                        "profile_center_type": str(center_type),
                        "profile_budget_tier": str(tier),
                        "requested_device": str(requested_device),
                        "actual_device": str(actual),
                        "safe_mode": str(safe_mode),
                        "parameters": int(params),
                        "estimated_operations": int(operations),
                        "serialized_state_bytes": int(model_bytes),
                        **measured,
                    }
                    result["records"].append(row)
                    print(
                        f"[HostingProfile] {token} H={H} device={actual} "
                        f"median={row['median_ms']:.4f}ms p95={row['p95_ms']:.4f}ms",
                        flush=True,
                    )
                    del model
                    if actual.type == "cuda":
                        torch.cuda.empty_cache()

    result["decision"] = "PASS_HOSTING_PROFILE_COMPLETE"
    atomic_json(result, out_path)
    return result
