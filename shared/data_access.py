# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Tuple

import torch

from core.data.center_api import (
    MetaDatasetCache,
    _allocate_raw_segments,
    _normalize_value_channels_from_support,
    build_feature_matrix,
    make_windows,
)


def _boundaries(cfg, cache: MetaDatasetCache, center_id: int, H: int, K: int):
    rec = cache.centers[int(center_id)]
    if rec.y is None:
        raise ValueError("CenterRecord.y is None")
    L = int(cfg.main.task.L)
    H = int(H)
    K = int(K)
    X_series = build_feature_matrix(cfg, rec)
    y_series = rec.y
    support_steps = L + H + K - 1
    min_eval_steps = L + H
    n_sup, n_val, n_chk, n_test = _allocate_raw_segments(
        total_steps=int(X_series.shape[0]),
        support_steps=support_steps,
        min_eval_steps=min_eval_steps,
        val_ratio=float(cfg.main.task.val_ratio),
        chk_ratio=float(cfg.main.task.chk_ratio),
        test_ratio=float(cfg.main.task.test_ratio),
    )
    return rec, X_series, y_series, L, H, K, n_sup, n_val, n_chk, n_test


def get_support_validation_check(
    cfg,
    cache: MetaDatasetCache,
    center_id: int,
    H: int,
    K: int,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, str, str]:
    rec, Xsrs, ysrs, L, H, K, n_sup, n_val, n_chk, _n_test = _boundaries(cfg, cache, center_id, H, K)
    b0, b1, b2, b3 = 0, n_sup, n_sup + n_val, n_sup + n_val + n_chk
    Xs, ys = make_windows(Xsrs[b0:b1], ysrs[b0:b1], L=L, H=H)
    Xv, yv = make_windows(Xsrs[b1:b2], ysrs[b1:b2], L=L, H=H)
    Xc, yc = make_windows(Xsrs[b2:b3], ysrs[b2:b3], L=L, H=H)
    if int(Xs.shape[0]) != K:
        raise RuntimeError(f"Support count mismatch: {Xs.shape[0]} != {K}")
    if bool(getattr(cfg.main.task, "normalize_values_from_support", False)):
        Xs, Xv, Xc = _normalize_value_channels_from_support(
            (Xs, Xv, Xc),
            k_max=int(cfg.main.sim.k_max),
            include_mask=bool(cfg.main.task.include_mask),
        )
    return Xs, ys, Xv, yv, Xc, yc, rec.tier_name, rec.center_type


def get_test_only(
    cfg,
    cache: MetaDatasetCache,
    center_id: int,
    H: int,
    K: int,
) -> Tuple[torch.Tensor, torch.Tensor]:
    rec, Xsrs, ysrs, L, H, K, n_sup, n_val, n_chk, n_test = _boundaries(cfg, cache, center_id, H, K)
    left = n_sup + n_val + n_chk
    right = left + n_test
    Xt, yt = make_windows(Xsrs[left:right], ysrs[left:right], L=L, H=H)
    if bool(getattr(cfg.main.task, "normalize_values_from_support", False)):
        # Reconstruct support only to obtain the same support statistics. The
        # Test tensor is still materialized only after the final model is fixed.
        Xsup, _ys = make_windows(Xsrs[:n_sup], ysrs[:n_sup], L=L, H=H)
        Xsup, Xt = _normalize_value_channels_from_support(
            (Xsup, Xt),
            k_max=int(cfg.main.sim.k_max),
            include_mask=bool(cfg.main.task.include_mask),
        )
    return Xt, yt
