# -*- coding: utf-8 -*-
"""C23-aligned Stage-2 V4 family-conditional ridge admission model.

This is a minimal re-estimation of the target-conditioned Top-36 -> Top-12
readout. The C1 bank, profile construction, hard feasible set and C23 target
adaptation are frozen. Lower predicted score is better.
"""
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple
import numpy as np


def _percentile(values: Mapping[int, float], lower_is_better: bool) -> Dict[int, float]:
    items = sorted(values, key=lambda k: ((values[k] if lower_is_better else -values[k]), int(k)))
    n = max(1, len(items) - 1)
    return {int(k): float(i / n) for i, k in enumerate(items)}


def _feature(profile: Mapping[str, Any], case: Mapping[str, Any], arch: Mapping[str, Any], pi50: Sequence[float]) -> np.ndarray:
    p = list(map(float, profile["profile_vector"]))
    b = list(map(float, case["budget_features"]))
    c = list(map(float, case["case_features"]))
    e = list(map(float, arch["embedding"]))
    idx = int(arch["arch_idx"])
    return np.asarray(p + b + c + e + [float(pi50[idx])], dtype=np.float64)


def fit_ridge(X: np.ndarray, y: np.ndarray, alpha: float) -> Dict[str, Any]:
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    mean = X.mean(axis=0)
    scale = X.std(axis=0)
    scale = np.where(scale < 1e-8, 1.0, scale)
    Xz = (X - mean) / scale
    Xb = np.concatenate([np.ones((Xz.shape[0], 1)), Xz], axis=1)
    reg = np.eye(Xb.shape[1], dtype=np.float64) * float(alpha)
    reg[0, 0] = 0.0
    w = np.linalg.solve(Xb.T @ Xb + reg, Xb.T @ y)
    return {"mean": mean.tolist(), "scale": scale.tolist(), "weights": w.tolist(), "alpha": float(alpha)}


def predict_ridge(model: Mapping[str, Any], X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float64)
    mean = np.asarray(model["mean"], dtype=np.float64)
    scale = np.asarray(model["scale"], dtype=np.float64)
    w = np.asarray(model["weights"], dtype=np.float64)
    Xz = (X - mean) / scale
    Xb = np.concatenate([np.ones((Xz.shape[0], 1)), Xz], axis=1)
    return Xb @ w


def fit_family_model(cases: Sequence[Mapping[str, Any]], profiles: Mapping[str, Mapping[str, Any]], architecture_tables: Mapping[int, Mapping[int, Mapping[str, Any]]], pi50: Sequence[float], alpha: float) -> Dict[str, Any]:
    by_family: Dict[str, Tuple[List[np.ndarray], List[float]]] = {}
    all_x: List[np.ndarray] = []
    all_y: List[float] = []
    for case in cases:
        profile = profiles[str(case["profile_key"])]
        H = int(case["H"])
        table = architecture_tables[H]
        for idx, score in zip(case["candidate_indices"], case["check_mse"]):
            arch = table[int(idx)]
            x = _feature(profile, case, arch, pi50)
            y = float(np.log(max(float(score), 1e-12)))
            fam = str(arch["family"])
            by_family.setdefault(fam, ([], []))[0].append(x)
            by_family[fam][1].append(y)
            all_x.append(x); all_y.append(y)
    global_model = fit_ridge(np.vstack(all_x), np.asarray(all_y), alpha)
    family_models = {}
    for fam, (xs, ys) in by_family.items():
        family_models[fam] = fit_ridge(np.vstack(xs), np.asarray(ys), alpha)
    return {"alpha": float(alpha), "global_model": global_model, "family_models": family_models}


def predict_scores(model: Mapping[str, Any], profile: Mapping[str, Any], case: Mapping[str, Any], architecture_table: Mapping[int, Mapping[str, Any]], pi50: Sequence[float]) -> Dict[int, float]:
    out: Dict[int, float] = {}
    for idx in map(int, case["candidate_indices"]):
        arch = architecture_table[idx]
        x = _feature(profile, case, arch, pi50).reshape(1, -1)
        sub = model["family_models"].get(str(arch["family"]), model["global_model"])
        out[idx] = float(predict_ridge(sub, x)[0])
    return out


def admit(model: Mapping[str, Any], profile: Mapping[str, Any], case: Mapping[str, Any], architecture_table: Mapping[int, Mapping[str, Any]], pi50: Sequence[float], top36: int = 36, top12: int = 12) -> Dict[str, Any]:
    feasible = list(map(int, case["candidate_indices"]))
    pred = predict_scores(model, profile, case, architecture_table, pi50)
    # A small source-prior rank term stabilizes extrapolation while preserving
    # target-conditioned ranking. Lower rank is better.
    src = {i: float(pi50[i]) for i in feasible}
    pred_rank = _percentile(pred, lower_is_better=True)
    src_rank = _percentile(src, lower_is_better=False)
    fused = {i: 0.85 * pred_rank[i] + 0.15 * src_rank[i] for i in feasible}
    order = sorted(feasible, key=lambda i: (fused[i], pred[i], int(i)))
    k36 = min(int(top36), len(order))
    if k36 < int(top12):
        raise RuntimeError("Hard-feasible set has fewer than Top-12 candidates")
    first = order[:k36]
    # Family-conditional tie correction: normalize predicted score within each
    # family before fine ranking, without imposing a quota.
    fam_values: Dict[str, Dict[int, float]] = {}
    for i in first:
        fam_values.setdefault(str(architecture_table[i]["family"]), {})[i] = pred[i]
    fam_rank: Dict[int, float] = {}
    for values in fam_values.values():
        fam_rank.update(_percentile(values, lower_is_better=True))
    fine = sorted(first, key=lambda i: (0.70 * fused[i] + 0.30 * fam_rank[i], pred[i], int(i)))
    return {
        "top36": [int(i) for i in first],
        "top12": [int(i) for i in fine[: int(top12)]],
        "predicted_log_scores": {str(i): float(pred[i]) for i in feasible},
        "fused_rank_scores": {str(i): float(fused[i]) for i in feasible},
        "hard_feasible_count": int(len(feasible)),
    }
