# -*- coding: utf-8 -*-
"""Budget-preserving C2.3 adaptation-mode controller.

The controller chooses REG50 or STD50 *before* target adaptation using only
pre-adaptation Support/Validation features. After the chosen branch is run,
Validation may reject it to DIRECT0. Check and Test are never used online.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np


FEATURE_NAMES: Tuple[str, ...] = (
    "log_direct_support",
    "log_direct_val",
    "log_val_support_ratio",
    "target_mean_shift",
    "target_std_log_ratio",
    "input_mean_shift",
    "input_std_log_ratio",
    "k_is_10",
    "h_is_4",
    "family_mlp",
    "family_tcn",
    "family_gru",
)


def _safe_log(x: float, eps: float = 1e-12) -> float:
    return float(np.log(max(float(x), eps)))


def _to_numpy(x: Any) -> np.ndarray:
    if hasattr(x, "detach"):
        x = x.detach()
    if hasattr(x, "cpu"):
        x = x.cpu()
    if hasattr(x, "numpy"):
        x = x.numpy()
    return np.asarray(x, dtype=np.float64)


def extract_pre_adaptation_features(
    *,
    direct_support_loss: float,
    direct_val_loss: float,
    Xs: Any,
    ys: Any,
    Xv: Any,
    yv: Any,
    H: int,
    K: int,
    family: str,
) -> Dict[str, float]:
    """Build features available before any target gradient update."""
    xs = _to_numpy(Xs)
    xv = _to_numpy(Xv)
    ys_np = _to_numpy(ys)
    yv_np = _to_numpy(yv)
    eps = 1e-12

    ys_mean = float(np.mean(ys_np))
    yv_mean = float(np.mean(yv_np))
    ys_std = float(np.std(ys_np))
    yv_std = float(np.std(yv_np))

    # Flatten all non-feature axes while preserving the last feature axis.
    xs2 = xs.reshape(-1, xs.shape[-1]) if xs.ndim >= 2 else xs.reshape(-1, 1)
    xv2 = xv.reshape(-1, xv.shape[-1]) if xv.ndim >= 2 else xv.reshape(-1, 1)
    xs_mean = np.mean(xs2, axis=0)
    xv_mean = np.mean(xv2, axis=0)
    xs_std = np.std(xs2, axis=0)
    xv_std = np.std(xv2, axis=0)
    input_mean_shift = float(np.mean(np.abs(xv_mean - xs_mean) / (xs_std + 1e-6)))
    input_std_log_ratio = float(np.mean(np.abs(np.log((xv_std + 1e-6) / (xs_std + 1e-6)))))

    fam = str(family).upper()
    values = {
        "log_direct_support": _safe_log(direct_support_loss),
        "log_direct_val": _safe_log(direct_val_loss),
        "log_val_support_ratio": _safe_log(direct_val_loss) - _safe_log(direct_support_loss),
        "target_mean_shift": float(abs(yv_mean - ys_mean) / (ys_std + 1e-6)),
        "target_std_log_ratio": float(abs(np.log((yv_std + 1e-6) / (ys_std + 1e-6)))),
        "input_mean_shift": input_mean_shift,
        "input_std_log_ratio": input_std_log_ratio,
        "k_is_10": 1.0 if int(K) == 10 else 0.0,
        "h_is_4": 1.0 if int(H) == 4 else 0.0,
        "family_mlp": 1.0 if fam == "MLP" else 0.0,
        "family_tcn": 1.0 if fam == "TCN" else 0.0,
        "family_gru": 1.0 if fam == "GRU" else 0.0,
    }
    return values


def vectorize_feature_dict(features: Dict[str, float]) -> np.ndarray:
    return np.asarray([float(features[name]) for name in FEATURE_NAMES], dtype=np.float64)


def standardize_matrix(
    X: np.ndarray,
    mean: np.ndarray = None,
    scale: np.ndarray = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = np.asarray(X, dtype=np.float64)
    if mean is None:
        mean = X.mean(axis=0)
    if scale is None:
        scale = X.std(axis=0)
    scale = np.where(np.asarray(scale) < 1e-8, 1.0, np.asarray(scale))
    return (X - mean) / scale, np.asarray(mean), np.asarray(scale)


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-z))


def train_binary_logistic(
    X: np.ndarray,
    y: np.ndarray,
    *,
    l2: float,
    steps: int,
    lr: float,
) -> Dict[str, Any]:
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    Xz, mean, scale = standardize_matrix(X)
    Xb = np.concatenate([np.ones((Xz.shape[0], 1)), Xz], axis=1)
    w = np.zeros(Xb.shape[1], dtype=np.float64)

    # Stable full-batch gradient descent; small data, deterministic result.
    for step in range(int(steps)):
        p = _sigmoid(Xb @ w)
        grad = (Xb.T @ (p - y)) / float(len(y))
        grad[1:] += float(l2) * w[1:] / float(len(y))
        eta = float(lr) / np.sqrt(1.0 + step / 100.0)
        w -= eta * grad

    return {
        "feature_names": list(FEATURE_NAMES),
        "feature_mean": mean.tolist(),
        "feature_scale": scale.tolist(),
        "weights": w.tolist(),
        "l2": float(l2),
        "steps": int(steps),
        "lr": float(lr),
    }


def predict_std_probability(model: Dict[str, Any], X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float64)
    mean = np.asarray(model["feature_mean"], dtype=np.float64)
    scale = np.asarray(model["feature_scale"], dtype=np.float64)
    w = np.asarray(model["weights"], dtype=np.float64)
    Xz, _, _ = standardize_matrix(X, mean=mean, scale=scale)
    Xb = np.concatenate([np.ones((Xz.shape[0], 1)), Xz], axis=1)
    return _sigmoid(Xb @ w)


def choose_mode(prob_std50: float, threshold: float) -> str:
    return "STD50" if float(prob_std50) >= float(threshold) else "REG50"


def relative_improvement(new_loss: float, ref_loss: float, eps: float = 1e-12) -> float:
    return float((float(ref_loss) - float(new_loss)) / (abs(float(ref_loss)) + float(eps)))


def safe_accept_selected_mode(
    *,
    direct_val: float,
    selected_val: float,
    selected_mode: str,
    tau: float,
) -> Dict[str, Any]:
    score = relative_improvement(selected_val, direct_val)
    accepted = score >= float(tau)
    return {
        "pre_adaptation_mode": str(selected_mode),
        "accepted_adaptation": bool(accepted),
        "acceptance_score": float(score),
        "final_mode": str(selected_mode) if accepted else "DIRECT0",
        "selected_steps": 50 if accepted else 0,
    }
