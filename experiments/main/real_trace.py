# -*- coding: utf-8 -*-
from __future__ import annotations

import contextlib
import csv
import gc
import hashlib
import json
import os
import random
import tarfile
import time
from collections import defaultdict
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from configs.methods.main_experiments_cfg import CFG, config_dict
from core.config import load_and_merge
from core.methods.ours.stage2_runtime import (
    candidate_backend_context,
    candidate_device,
    configure_stage2_runtime,
    synchronize_if_cuda,
)
from core.space import build_model, enumerate_A_base, is_feasible, profile_arch
from shared.evaluation.common import atomic_json, eval_metrics, file_sha256, seed_all
from .pipeline import _atomic_torch_save, _asset_record, _candidate_lex


RAW_COLUMNS = (
    "machine_id",
    "time_stamp",
    "cpu_util_percent",
    "mem_util_percent",
    "mem_gps",
    "mkpi",
    "net_in",
    "net_out",
    "disk_io_percent",
)


@contextlib.contextmanager
def _open_machine_usage_text(path: str):
    path = os.path.abspath(path)
    if path.lower().endswith((".tar.gz", ".tgz")):
        tf = tarfile.open(path, "r:gz")
        try:
            members = [
                m for m in tf.getmembers() if m.isfile() and m.name.endswith("machine_usage.csv")
            ]
            if not members:
                raise FileNotFoundError("machine_usage.csv not found in archive")
            raw = tf.extractfile(members[0])
            if raw is None:
                raise RuntimeError("Unable to open machine_usage.csv member")
            import io

            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            try:
                yield text
            finally:
                text.close()
        finally:
            tf.close()
    else:
        with open(path, "r", encoding="utf-8", newline="") as f:
            yield f


def _stable_key(text: str) -> Tuple[str, str]:
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), text


def _parse_row(row: Sequence[str]) -> Optional[Tuple[str, float, np.ndarray]]:
    if len(row) < 9:
        return None
    try:
        mid = str(row[0])
        ts = float(row[1])
        vals = np.asarray([float(x) for x in row[2:9]], dtype=np.float64)
    except (TypeError, ValueError):
        return None
    if not mid or not np.isfinite(ts):
        return None
    return mid, ts, vals


def _count_machines(path: str) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    started = time.perf_counter()
    seen = 0
    with _open_machine_usage_text(path) as f:
        for row in csv.reader(f):
            seen += 1
            parsed = _parse_row(row)
            if parsed is not None:
                counts[parsed[0]] += 1
            if seen % 5_000_000 == 0:
                print(
                    f"[FinalExp:RealPrep] pass=1 rows={seen} "
                    f"machines={len(counts)} elapsed={(time.perf_counter()-started)/3600:.2f}h",
                    flush=True,
                )
    print(
        f"[FinalExp:RealPrep] pass=1 complete rows={seen} "
        f"machines={len(counts)} elapsed={(time.perf_counter()-started)/3600:.2f}h",
        flush=True,
    )
    return dict(counts)


def _collect_selected(path: str, selected: set[str]) -> Dict[str, List[Tuple[float, np.ndarray]]]:
    rows: Dict[str, List[Tuple[float, np.ndarray]]] = {m: [] for m in selected}
    started = time.perf_counter()
    seen = 0
    kept = 0
    with _open_machine_usage_text(path) as f:
        for row in csv.reader(f):
            seen += 1
            parsed = _parse_row(row)
            if parsed is None:
                continue
            mid, ts, vals = parsed
            if mid in rows:
                rows[mid].append((ts, vals))
                kept += 1
            if seen % 5_000_000 == 0:
                print(
                    f"[FinalExp:RealPrep] pass=2 rows={seen} kept={kept} "
                    f"elapsed={(time.perf_counter()-started)/3600:.2f}h",
                    flush=True,
                )
    print(
        f"[FinalExp:RealPrep] pass=2 complete rows={seen} kept={kept} "
        f"elapsed={(time.perf_counter()-started)/3600:.2f}h",
        flush=True,
    )
    return rows


def _resample_machine(
    records: Sequence[Tuple[float, np.ndarray]], max_points: int
) -> Tuple[np.ndarray, np.ndarray, float]:
    by_ts: Dict[float, List[np.ndarray]] = defaultdict(list)
    for ts, vals in records:
        by_ts[float(ts)].append(np.asarray(vals, dtype=np.float64))
    ts = np.asarray(sorted(by_ts), dtype=np.float64)
    if ts.size < 3:
        raise ValueError("Too few timestamps")
    vals = np.stack([np.nanmean(np.stack(by_ts[t]), axis=0) for t in ts], axis=0)
    diffs = np.diff(ts)
    diffs = diffs[diffs > 0]
    step = float(np.median(diffs)) if diffs.size else 60.0
    step = max(1.0, step)
    grid = np.arange(ts[0], ts[-1] + 0.5 * step, step, dtype=np.float64)
    if grid.size > max_points:
        grid = grid[-max_points:]
    out = np.zeros((grid.size, 7), dtype=np.float64)
    mask = np.zeros((grid.size, 7), dtype=np.float64)
    # Metrics with known [0,100] range except mkpi at column 3.
    for j in range(7):
        v = vals[:, j].copy()
        valid = np.isfinite(v)
        if j != 3:
            valid &= (v >= 0.0) & (v <= 100.0)
        else:
            valid &= v >= 0.0
        if valid.sum() < 2:
            raise ValueError(f"Metric {j} has insufficient valid values")
        out[:, j] = np.interp(grid, ts[valid], v[valid])
        # observed if a raw timestamp is within half a sampling interval
        pos = np.searchsorted(ts[valid], grid)
        left = np.clip(pos - 1, 0, valid.sum() - 1)
        right = np.clip(pos, 0, valid.sum() - 1)
        tv = ts[valid]
        dist = np.minimum(np.abs(grid - tv[left]), np.abs(grid - tv[right]))
        mask[:, j] = (dist <= 0.51 * step).astype(np.float64)
    return out, mask, step


def _source_normalization(raws: Sequence[np.ndarray]) -> Dict[str, float]:
    mkpi = np.concatenate([x[:, 3] for x in raws])
    mkpi = mkpi[np.isfinite(mkpi) & (mkpi >= 0)]
    scale = float(np.quantile(np.log1p(mkpi), 0.99)) if mkpi.size else 1.0
    return {"mkpi_log_scale": max(scale, 1e-6)}


def _feature_matrix(
    raw: np.ndarray, mask7: np.ndarray, step: float, norm: Mapping[str, float]
) -> Tuple[np.ndarray, np.ndarray]:
    base = np.zeros_like(raw, dtype=np.float64)
    # raw order: cpu, mem, mem_gps, mkpi, net_in, net_out, disk_io
    bounded = [0, 1, 2, 4, 5, 6]
    for j in bounded:
        base[:, j] = np.clip(raw[:, j], 0.0, 100.0) / 100.0
    base[:, 3] = np.clip(
        np.log1p(np.maximum(raw[:, 3], 0.0)) / float(norm["mkpi_log_scale"]),
        0.0,
        2.0,
    )
    diff_cols = []
    diff_masks = []
    for j in (0, 1, 4, 5):
        d = np.diff(base[:, j], prepend=base[0, j])
        diff_cols.append(d[:, None])
        m = np.minimum(mask7[:, j], np.roll(mask7[:, j], 1))
        m[0] = 0.0
        diff_masks.append(m[:, None])
    cpu = base[:, 0]
    roll = np.convolve(cpu, np.ones(6) / 6.0, mode="same")[:, None]
    roll_mask = np.convolve(mask7[:, 0], np.ones(6), mode="same")
    roll_mask = (roll_mask >= 3).astype(np.float64)[:, None]
    values12 = np.concatenate([base] + diff_cols + [roll], axis=1)
    masks12 = np.concatenate([mask7] + diff_masks + [roll_mask], axis=1)
    dt = np.full((raw.shape[0], 1), min(1.0, step / 600.0), dtype=np.float64)
    X = np.concatenate([values12, masks12, dt], axis=1).astype(np.float32)
    y = base[:, 0].astype(np.float32)
    return X, y


def prepare_alibaba_trace(
    input_path: str, out_dir: str, *, verify_archive: bool = True
) -> Dict[str, Any]:
    input_path = os.path.abspath(input_path)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    if not os.path.isfile(input_path):
        raise FileNotFoundError(input_path)
    archive_hash = file_sha256(input_path)
    if (
        verify_archive
        and input_path.lower().endswith((".tar.gz", ".tgz"))
        and archive_hash.lower() != CFG.real_trace_expected_archive_sha256.lower()
    ):
        raise RuntimeError(
            "Alibaba machine_usage archive SHA-256 mismatch. "
            "Use -SkipArchiveHashCheck only for an explicitly documented mirror."
        )
    counts = _count_machines(input_path)
    eligible = sorted(
        [m for m, n in counts.items() if n >= CFG.real_min_points], key=_stable_key
    )
    needed = CFG.real_source_machines + CFG.real_target_machines
    if len(eligible) < needed:
        raise RuntimeError(
            f"Only {len(eligible)} machines have >= {CFG.real_min_points} points; "
            f"need {needed}."
        )
    selected = eligible[:needed]
    source_ids = selected[: CFG.real_source_machines]
    target_ids = selected[CFG.real_source_machines : needed]
    collected = _collect_selected(input_path, set(selected))
    resampled: Dict[str, Tuple[np.ndarray, np.ndarray, float]] = {}
    for mid in selected:
        resampled[mid] = _resample_machine(
            collected[mid], CFG.real_max_points_per_machine
        )
    norm = _source_normalization([resampled[m][0] for m in source_ids])
    arrays: Dict[str, Any] = {}
    target_cv: Dict[str, float] = {}
    for i, mid in enumerate(selected):
        raw, mask, step = resampled[mid]
        X, y = _feature_matrix(raw, mask, step, norm)
        arrays[f"X_{i}"] = X
        arrays[f"y_{i}"] = y
        arrays[f"id_{i}"] = np.asarray(mid)
        arrays[f"step_{i}"] = np.asarray(step, dtype=np.float64)
        if mid in target_ids:
            target_cv[mid] = float(np.std(y) / (np.mean(y) + 1e-6))
    npz_path = os.path.join(out_dir, "alibaba2018_machine_usage_processed.npz")
    np.savez_compressed(npz_path, **arrays)
    ordered_cv = sorted(target_ids, key=lambda m: (target_cv[m], _stable_key(m)))
    third = max(1, len(ordered_cv) // 3)
    center_types = {}
    for rank, mid in enumerate(ordered_cv):
        center_types[mid] = "A" if rank < third else ("B" if rank < 2 * third else "C")
    # Deterministic weakly-independent budget assignment: 6 tight, 8 medium, 6 loose.
    budget_order = sorted(target_ids, key=lambda m: _stable_key("budget:" + m))
    budget_tiers = {}
    for rank, mid in enumerate(budget_order):
        budget_tiers[mid] = "tight" if rank < 6 else ("medium" if rank < 14 else "loose")
    manifest = {
        "study": "alibaba2018_machine_usage_semi_real_preparation",
        "decision": "PASS_REAL_TRACE_PREPARED",
        "protocol": config_dict(),
        "source": {
            "dataset": "Alibaba cluster-trace-v2018 machine_usage",
            "input_path": input_path,
            "input_sha256": archive_hash,
            "official_expected_archive_sha256": CFG.real_trace_expected_archive_sha256,
            "archive_hash_verified": (
                not input_path.lower().endswith((".tar.gz", ".tgz"))
                or archive_hash.lower() == CFG.real_trace_expected_archive_sha256.lower()
            ),
        },
        "processed_npz": npz_path,
        "processed_sha256": file_sha256(npz_path),
        "source_machine_ids": source_ids,
        "target_machine_ids": target_ids,
        "center_types": center_types,
        "budget_tiers": budget_tiers,
        "normalization": norm,
        "feature_definition": {
            "value_channels": [
                "cpu", "memory", "memory_bandwidth", "log_mkpi", "net_in",
                "net_out", "disk_io", "cpu_diff", "memory_diff", "net_in_diff",
                "net_out_diff", "cpu_roll6"
            ],
            "mask_channels": 12,
            "time_gap_channels": 1,
            "input_dim": 25,
            "target": "cpu_utilization",
        },
        "semi_real_note": (
            "Workload observations are real Alibaba machine-usage traces; "
            "deployment budget tiers are deterministic semi-synthetic labels."
        ),
        "test_used": False,
    }
    manifest_path = os.path.join(out_dir, "real_trace_manifest.json")
    atomic_json(manifest, manifest_path)
    return manifest


def _load_processed(manifest_path: str):
    manifest = json.load(open(manifest_path, "r", encoding="utf-8"))
    if manifest.get("decision") != "PASS_REAL_TRACE_PREPARED":
        raise RuntimeError("Real trace is not prepared")
    npz_path = manifest["processed_npz"]
    if file_sha256(npz_path) != manifest["processed_sha256"]:
        raise RuntimeError("Processed real-trace NPZ hash mismatch")
    data = np.load(npz_path, allow_pickle=False)
    ids: List[str] = []
    i = 0
    while f"id_{i}" in data:
        ids.append(str(data[f"id_{i}"].item()))
        i += 1
    mapping = {
        mid: (data[f"X_{j}"], data[f"y_{j}"])
        for j, mid in enumerate(ids)
    }
    return manifest, mapping


def _make_windows(X: np.ndarray, y: np.ndarray, L: int, H: int):
    n = X.shape[0] - L - H + 1
    if n <= 0:
        raise ValueError("Not enough points")
    Xw = np.stack([X[i : i + L] for i in range(n)]).astype(np.float32)
    yw = np.stack([y[i + L : i + L + H] for i in range(n)]).astype(np.float32)
    return torch.from_numpy(Xw), torch.from_numpy(yw)


def _real_case_split(X: np.ndarray, y: np.ndarray, L: int, H: int, K: int):
    lengths = [
        L + H + K - 1,
        L + H + 80 - 1,
        L + H + 60 - 1,
        L + H + 200 - 1,
    ]
    total = sum(lengths)
    if X.shape[0] < total:
        raise RuntimeError(f"Real center has {X.shape[0]} points; need {total}")
    X = X[-total:]
    y = y[-total:]
    cuts = np.cumsum([0] + lengths)
    parts = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        parts.append(_make_windows(X[a:b], y[a:b], L, H))
    if int(parts[0][0].shape[0]) != K:
        raise RuntimeError("Real support count mismatch")
    return parts  # support, val, check, test


def _real_source_windows(X: np.ndarray, y: np.ndarray, L: int, H: int):
    Xw, yw = _make_windows(X, y, L, H)
    n = int(Xw.shape[0])
    take = min(CFG.real_source_windows_per_machine, n)
    idx = np.linspace(0, n - 1, take, dtype=int)
    return Xw[idx], yw[idx]


def _real_runtime(device: str, safe_mode: str):
    requested = torch.device(device)
    if requested.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    safe = configure_stage2_runtime(requested, safe_mode)
    cfg = load_and_merge("ours", main_module="configs.main_cfg", methods_pkg="configs.methods", smoke=False)
    A = enumerate_A_base(cfg.main.arch)
    return cfg, A, requested, safe


def build_real_bank(
    project_root: str,
    manifest_path: str,
    out_dir: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    del project_root
    manifest, mapping = _load_processed(manifest_path)
    cfg, A, requested, safe = _real_runtime(device, safe_mode)
    L = int(cfg.main.task.L)
    input_dim = 25
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    bank_manifest_path = os.path.join(out_dir, "real_bank_manifest.json")
    run_mode = "smoke" if smoke else "formal"
    bank = json.load(open(bank_manifest_path, encoding="utf-8")) if os.path.isfile(bank_manifest_path) else {
        "study": "alibaba2018_real_source_bank",
        "decision": "REAL_BANK_IN_PROGRESS",
        "run_mode": run_mode,
        "protocol": config_dict(),
        "real_trace_manifest_sha256": file_sha256(manifest_path),
        "assets": {},
        "test_used": False,
        "target_machines_used": False,
    }
    if bank.get("run_mode") != run_mode:
        raise RuntimeError("Smoke/formal outputs cannot share real-bank directory")
    epochs = 1 if smoke else CFG.real_source_epochs
    jobs = [(H, idx) for H in CFG.H_list for idx in CFG.compact_arch_indices]
    if smoke:
        # Build all six H=1 compact candidates so smoke evaluation can run
        # the actual anchor-safe selector rather than a partial surrogate.
        jobs = [(CFG.H_list[0], idx) for idx in CFG.compact_arch_indices]
    started_all = time.perf_counter()
    completed_new = 0
    for job_no, (H, idx) in enumerate(jobs, 1):
        key = f"h{H}_a{idx}"
        out_file = os.path.join(out_dir, f"real_h{H}_a{idx}.pt")
        old = bank.get("assets", {}).get(key)
        if old and os.path.isfile(out_file) and file_sha256(out_file) == old.get("sha256"):
            continue
        spec = A[idx]
        actual = candidate_device(spec, requested, safe)
        checkpoint = out_file + ".progress.pt"
        with candidate_backend_context(spec, actual, safe):
            seed = CFG.train_seed + 101 * H + idx
            seed_all(seed, actual)
            model = build_model(spec, input_dim=input_dim, H=H, L=L, device=str(actual))
            opt = optim.Adam(model.parameters(), lr=CFG.real_source_lr, weight_decay=CFG.real_source_weight_decay)
            start_epoch = 0
            if os.path.isfile(checkpoint):
                state = torch.load(checkpoint, map_location=actual)
                model.load_state_dict(state["model"], strict=True)
                opt.load_state_dict(state["optimizer"])
                start_epoch = int(state.get("next_epoch", 0))
            last_loss = None
            for epoch in range(start_epoch, epochs):
                centers = list(manifest["source_machine_ids"])
                random.Random(seed + epoch).shuffle(centers)
                if smoke:
                    centers = centers[:2]
                losses = []
                for mid in centers:
                    Xw, yw = _real_source_windows(mapping[mid][0], mapping[mid][1], L, H)
                    if smoke:
                        Xw, yw = Xw[:20], yw[:20]
                    gen = torch.Generator(device=Xw.device)
                    gen.manual_seed(seed + epoch + int(hashlib.sha256(mid.encode()).hexdigest()[:8], 16))
                    order = torch.randperm(int(Xw.shape[0]), generator=gen)
                    for left in range(0, int(Xw.shape[0]), CFG.real_source_batch_size):
                        ids = order[left:left + CFG.real_source_batch_size]
                        xb, yb = Xw.index_select(0, ids).to(actual), yw.index_select(0, ids).to(actual)
                        model.train(); opt.zero_grad(set_to_none=True)
                        loss = ((model(xb.contiguous()) - yb.contiguous()) ** 2).mean()
                        if not torch.isfinite(loss):
                            raise RuntimeError("Non-finite real source loss")
                        loss.backward(); opt.step(); losses.append(float(loss.detach().item()))
                last_loss = float(np.mean(losses))
                _atomic_torch_save({
                    "model": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                    "optimizer": opt.state_dict(),
                    "next_epoch": epoch + 1,
                }, checkpoint)
                elapsed_job = time.perf_counter() - started_all
                completed_epoch_units = completed_new * epochs + (epoch + 1)
                total_epoch_units = len(jobs) * epochs
                eta = elapsed_job / max(1, completed_epoch_units) * max(0, total_epoch_units - completed_epoch_units)
                print(
                    f"[FinalExp:RealBank] job={job_no}/{len(jobs)} H={H} A={idx} "
                    f"epoch={epoch+1}/{epochs} loss={last_loss:.6g} "
                    f"elapsed={elapsed_job/3600:.2f}h eta={eta/3600:.2f}h",
                    flush=True,
                )
            synchronize_if_cuda(actual)
            _atomic_torch_save({k: v.detach().cpu() for k, v in model.state_dict().items()}, out_file)
            if os.path.isfile(checkpoint): os.remove(checkpoint)
            del model, opt
        params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
        bank.setdefault("assets", {})[key] = {
            "path": out_file,
            "sha256": file_sha256(out_file),
            "H": int(H), "arch_idx": int(idx), "arch_key": str(spec.arch_key),
            "family": str(spec.family), "epochs": int(epochs), "final_source_loss": last_loss,
            "params": float(params), "flops": float(flops),
        }
        bank["completed_assets"] = len(bank["assets"]); bank["expected_assets"] = len(jobs)
        atomic_json(bank, bank_manifest_path)
        completed_new += 1
        elapsed_all = time.perf_counter() - started_all
        remaining_jobs = len(jobs) - len(bank["assets"])
        eta_all = elapsed_all / max(1, completed_new) * max(0, remaining_jobs)
        print(
            f"[FinalExp:RealBank] completed={len(bank['assets'])}/{len(jobs)} "
            f"elapsed={elapsed_all/3600:.2f}h eta={eta_all/3600:.2f}h",
            flush=True,
        )
        gc.collect()
        if requested.type == "cuda": torch.cuda.empty_cache()
    bank["complete"] = len(bank.get("assets", {})) == len(jobs)
    bank["decision"] = "PASS_REAL_SOURCE_BANK" if bank["complete"] else "REAL_BANK_INCOMPLETE"
    atomic_json(bank, bank_manifest_path)
    return bank


def _load_real_bank_model(bank: Mapping[str, Any], A, H, idx, input_dim, L, device):
    item = bank["assets"][f"h{H}_a{idx}"]
    model = build_model(A[idx], input_dim=input_dim, H=H, L=L, device=str(device))
    state = torch.load(item["path"], map_location=device)
    model.load_state_dict(state, strict=True)
    return model


def run_real_eval(
    project_root: str,
    manifest_path: str,
    bank_dir: str,
    out_path: str,
    device: str,
    safe_mode: str,
    smoke: bool = False,
) -> Dict[str, Any]:
    del project_root
    trace, mapping = _load_processed(manifest_path)
    bank_path = os.path.join(os.path.abspath(bank_dir), "real_bank_manifest.json")
    bank = json.load(open(bank_path, "r", encoding="utf-8"))
    if bank.get("decision") != "PASS_REAL_SOURCE_BANK":
        raise RuntimeError("Real source bank is not PASS")
    cfg, A, requested, safe = _real_runtime(device, safe_mode)
    L = int(cfg.main.task.L); input_dim = 25
    targets = list(trace["target_machine_ids"])
    jobs = [(mid, H, K) for mid in targets for H in CFG.H_list for K in CFG.K_list]
    if smoke:
        jobs = [job for job in jobs if int(job[1]) == int(CFG.H_list[0])][:2]
    run_mode = "smoke" if smoke else "formal"
    result = json.load(open(out_path, encoding="utf-8")) if os.path.isfile(out_path) else {
        "study": "alibaba2018_semi_real_evaluation",
        "decision": "REAL_EVAL_IN_PROGRESS",
        "run_mode": run_mode,
        "protocol": config_dict(),
        "trace_manifest_sha256": file_sha256(manifest_path),
        "bank_manifest_sha256": file_sha256(bank_path),
        "records": {},
        "methods": ["ours", "pt_ft", "scratch50"],
        "selection_uses_test": False,
    }
    if result.get("run_mode") != run_mode:
        raise RuntimeError("Smoke/formal outputs cannot share real-eval file")
    records = dict(result.get("records", {}))
    started_all = time.perf_counter()
    completed_new = 0
    for job_no, (mid, H, K) in enumerate(jobs, 1):
        tier = str(trace["budget_tiers"][mid]); ctype = str(trace["center_types"][mid])
        key = f"m{hashlib.sha256(mid.encode()).hexdigest()[:10]}_h{H}_k{K}_b{tier}"
        if key in records and records[key].get("complete"): continue
        (Xs, ys), (Xv, yv), (Xc, yc), (Xt, yt) = _real_case_split(mapping[mid][0], mapping[mid][1], L, H, K)
        feasible = [i for i in CFG.compact_arch_indices if is_feasible(A[i], cfg.main.budget, tier, L, input_dim, H)]
        if 57 not in feasible: raise RuntimeError("Real A57 anchor infeasible")
        seed = CFG.train_seed + int(hashlib.sha256(mid.encode()).hexdigest()[:8], 16) + 37 * H + 53 * K
        rows = []; states = {}
        for idx in feasible:
            spec = A[idx]; actual = candidate_device(spec, requested, safe)
            with candidate_backend_context(spec, actual, safe):
                model = _load_real_bank_model(bank, A, H, idx, input_dim, L, actual)
                seed_all(seed, actual); model.train(); opt = optim.SGD(model.parameters(), lr=CFG.target_lr)
                for _ in range(1 if smoke else CFG.target_steps):
                    opt.zero_grad(set_to_none=True); loss = ((model(Xs.to(actual)) - ys.to(actual)) ** 2).mean(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), CFG.target_grad_clip); opt.step()
                val = eval_metrics(model, Xv, yv); chk = eval_metrics(model, Xc, yc)
                params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
                token = "PT_A57" if idx == 57 else f"A{idx}"
                rows.append({"token": token, "arch_idx": int(idx), "arch_key": str(spec.arch_key), "family": str(spec.family), "params": float(params), "flops": float(flops), "hard_feasible": True, "validation": val, "check": chk})
                states[token] = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                del model, opt
        anchor = next(r for r in rows if r["token"] == "PT_A57")
        alts = [r for r in rows if r["token"] != "PT_A57"]
        best_alt = min(alts, key=_candidate_lex) if alts else None
        switched = best_alt is not None and float(best_alt["validation"]["weighted_mse"]) <= float(anchor["validation"]["weighted_mse"]) * (1.0 - CFG.frozen_margin_rel)
        selected = best_alt if switched else anchor
        test_by_token = {}
        for row in rows:
            token = row["token"]; spec = A[row["arch_idx"]]; actual = candidate_device(spec, requested, safe)
            with candidate_backend_context(spec, actual, safe):
                model = build_model(spec, input_dim=input_dim, H=H, L=L, device=str(actual)); model.load_state_dict(states[token], strict=True); test_by_token[token] = eval_metrics(model, Xt, yt); del model
        seed_all(seed, requested)
        scratch = build_model(A[57], input_dim=input_dim, H=H, L=L, device=str(requested)); opt = optim.SGD(scratch.parameters(), lr=CFG.target_lr)
        for _ in range(1 if smoke else CFG.target_steps):
            opt.zero_grad(set_to_none=True); loss = ((scratch(Xs.to(requested)) - ys.to(requested)) ** 2).mean(); loss.backward(); torch.nn.utils.clip_grad_norm_(scratch.parameters(), CFG.target_grad_clip); opt.step()
        scratch_test = eval_metrics(scratch, Xt, yt); del scratch, opt
        records[key] = {
            "complete": True, "machine_id_hash": hashlib.sha256(mid.encode()).hexdigest(),
            "center_type": ctype, "budget_tier": tier, "H": int(H), "K": int(K),
            "ours": {"selected_token": selected["token"], "switched": bool(switched), "test": test_by_token[selected["token"]]},
            "pt_ft": {"test": test_by_token["PT_A57"]},
            "scratch50": {"test": scratch_test},
            "selection_uses_test": False,
        }
        result["records"] = records; result["N_records"] = len(records); result["expected_records"] = len(jobs); result["complete"] = len(records) == len(jobs)
        atomic_json(result, out_path)
        completed_new += 1
        elapsed_all = time.perf_counter() - started_all
        remaining = len(jobs) - len(records)
        eta = elapsed_all / max(1, completed_new) * max(0, remaining)
        print(
            f"[FinalExp:RealEval] {job_no}/{len(jobs)} {key} "
            f"selected={selected['token']} elapsed={elapsed_all/3600:.2f}h "
            f"eta={eta/3600:.2f}h",
            flush=True,
        )
        gc.collect()
        if requested.type == "cuda": torch.cuda.empty_cache()
    result["decision"] = "PASS_REAL_TRACE_EVAL" if result.get("complete") else "REAL_EVAL_INCOMPLETE"
    atomic_json(result, out_path)
    return result
