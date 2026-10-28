# core/methods/ours/paper_engine.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
from contextlib import nullcontext
import csv
import hashlib
import json
import os
import random
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import torch
import torch.nn.functional as F
from torch.func import functional_call

from core.data.center_api import build_meta_dataset_cache, get_center_split_from_cache
from core.methods.ours.adapt import adapt_condition_modulated, adapt_steps
from core.methods.ours.source_prior import build_or_load_source_pooled_c1
from core.methods.ours.paper_modules import (
    GROUP_TO_ID,
    PaperConditionStack,
    build_budget_features,
    build_task_features,
    parameter_group,
    portrait_from_support,
)
from core.methods.ours.weight_bank import (
    BankMeta,
    init_bank_from_space,
    load_weight_bank,
    make_bank_key_shared,
    reptile_meta_train,
    resolve_bank_key,
    save_weight_bank,
)
from core.space import build_model, enumerate_A_base, is_feasible, profile_arch
from core.utils.metrics import (
    eval_mae,
    eval_mse,
    eval_paper_sequence_consistency,
    eval_weighted_mse,
    eval_worst10,
    mean_std,
)
from core.utils.timer import ProgressTracker, Timer


def _space_fingerprint(A: Sequence[Any]) -> str:
    text = "|".join(str(x.arch_key) for x in A)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(int(chunk_size))
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _tensor_to_2d_list(
    x: torch.Tensor,
) -> List[List[float]]:
    """Convert a tensor to a JSON-safe two-dimensional float list."""
    x2 = x.detach().cpu().reshape(x.shape[0], -1)
    return [
        [float(v) for v in row]
        for row in x2.tolist()
    ]


def _tier_limits(cfg, tier: str) -> Tuple[float, float]:
    obj = getattr(cfg.main.budget, str(tier))
    return float(obj.flops), float(obj.params)


def _feasible(cfg, spec, tier: str, L: int, input_dim: int, H: int) -> bool:
    return bool(is_feasible(spec, cfg.main.budget, str(tier), int(L), int(input_dim), int(H)))


def _load_prior_model(
    *,
    spec,
    H: int,
    L: int,
    input_dim: int,
    bank: Dict[str, Dict[str, torch.Tensor]],
    device: torch.device,
):
    model = build_model(spec, input_dim=int(input_dim), H=int(H), L=int(L), device=str(device))
    key, _hit = resolve_bank_key(
        bank,
        H=int(H),
        arch_key=str(spec.arch_key),
        input_dim=int(input_dim),
        L=int(L),
    )
    if key is not None:
        model.load_state_dict(bank[key], strict=True)
        prior_state = {k: v.detach().clone() for k, v in bank[key].items()}
    else:
        prior_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    return model, prior_state


def _budget_compatibility(
    *,
    spec,
    cfg,
    tier: str,
    L: int,
    input_dim: int,
    H: int,
) -> float:
    params, flops = profile_arch(spec, L=int(L), input_dim=int(input_dim), H=int(H))
    bf, bp = _tier_limits(cfg, tier)
    # Positive inside the feasible region and smoothly negative outside.
    rf = float(bf) / max(1.0, float(flops))
    rp = float(bp) / max(1.0, float(params))
    margin = min(rf, rp)
    return float(max(-3.0, min(3.0, torch.log(torch.tensor(max(margin, 1e-6))).item())))


def _rank_candidates(
    *,
    rho: torch.Tensor,
    A: Sequence[Any],
    cfg,
    tier: str,
    L: int,
    input_dim: int,
    H: int,
    budget_weight: float,
    use_budget: bool,
) -> Tuple[List[int], Dict[int, float]]:
    scores: Dict[int, float] = {}
    for i, spec in enumerate(A):
        compat = _budget_compatibility(
            spec=spec, cfg=cfg, tier=tier, L=L, input_dim=input_dim, H=H
        ) if use_budget else 0.0
        scores[int(i)] = float(rho[int(i)].detach().item()) + float(budget_weight) * compat
    ranked = sorted(scores, key=lambda i: (-scores[i], i))
    return ranked, scores


def _env_flag(name: str, default: bool = False) -> bool:
    raw = str(os.environ.get(name, "")).strip().lower()
    if raw == "":
        return bool(default)
    return raw in {"1", "true", "yes", "y", "on"}


def _env_csv_set(name: str) -> set[str]:
    raw = str(os.environ.get(name, "")).strip()
    if raw == "" or raw.lower() in {"all", "*"}:
        return set()
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def _rank_position(ranked: Sequence[int]) -> Dict[int, int]:
    return {int(idx): int(pos + 1) for pos, idx in enumerate(ranked)}


def _diagnostic_task_enabled(
    *,
    tier: str,
    H: int,
    K: int,
    tiers: set[str],
    hk_pairs: set[str],
) -> bool:
    if tiers and str(tier).lower() not in tiers:
        return False
    if hk_pairs and f"{int(H)}:{int(K)}" not in hk_pairs:
        return False
    return True


def _resolve_condition_flags(
    mcfg,
) -> Tuple[bool, bool, bool, bool, bool, bool]:
    """Return state, admission-budget, adaptation-budget, task and controls.

    The formal C1 path intentionally separates the learned structural residual
    from the explicit resource term.  This keeps the paper-level chain intact
    while allowing the 2x2 admission study to identify whether improvements
    come from target condition, budget handling, or their combination.
    """
    mode = str(getattr(mcfg, "condition_ablation_mode", "full")).lower()
    no_condition = mode == "no_condition"
    use_state = (mode != "no_center_signature") and (not no_condition)
    preinsert_enabled = (mode != "no_constraint_preinsertion") and (not no_condition)
    use_budget_admission = bool(
        getattr(mcfg, "admission_use_budget_condition", False)
    ) and preinsert_enabled
    use_budget_adaptation = bool(
        getattr(mcfg, "adaptation_use_budget_condition", True)
    ) and preinsert_enabled
    use_task = bool(getattr(mcfg, "arch_use_task", True)) and (not no_condition)
    use_prior_mod = bool(getattr(mcfg, "cond_prior_mod_enable", True)) and (not no_condition)
    use_adapt_mod = bool(getattr(mcfg, "adapt_condition_scale_enable", True)) and (not no_condition)
    return (
        use_state,
        use_budget_admission,
        use_budget_adaptation,
        use_task,
        use_prior_mod,
        use_adapt_mod,
    )


def _diversity_aware_select(
    ranked: Sequence[int],
    *,
    A: Sequence[Any],
    k: int,
    min_per_family: int,
    cfg,
    tier: str,
    L: int,
    input_dim: int,
    H: int,
    feasible_first: bool,
) -> List[int]:
    """Select top-k candidates with a generic architecture-family floor.

    The rule is invariant across centers, horizons, support sizes, and budget
    tiers.  It prevents an entire architecture family from disappearing during
    learned admission while leaving all remaining slots to the learned rank.
    When requested, already-feasible architectures are considered before
    infeasible ones, which implements resource-aware pre-admission without
    using validation or test labels.
    """
    k = max(0, min(int(k), len(ranked)))
    if k == 0:
        return []

    seen = set()
    ordered = []
    for i0 in ranked:
        i = int(i0)
        if i not in seen:
            seen.add(i)
            ordered.append(i)

    feasible: List[int] = []
    infeasible: List[int] = []
    if feasible_first:
        feasible = [
            i for i in ordered
            if _feasible(cfg, A[i], tier, L, input_dim, H)
        ]
        feasible_set = set(feasible)
        infeasible = [i for i in ordered if i not in feasible_set]
        ordered = feasible + infeasible

    families = [str(x) for x in getattr(cfg.main.arch, "families", ())]
    if not families:
        families = sorted({str(A[i].family) for i in ordered})

    quota = max(0, int(min_per_family))
    selected_set = set()
    if quota > 0:
        # Under hard pre-admission, enforce the family floor only among families
        # that have feasible members. This never inserts an infeasible model
        # merely to satisfy diversity (e.g., no MLP is feasible in the tight
        # tier of the current architecture space).
        quota_source = feasible if feasible_first and feasible else ordered
        for fam in families:
            fam_items = [i for i in quota_source if str(A[i].family) == fam]
            for i in fam_items[:quota]:
                if len(selected_set) >= k:
                    break
                selected_set.add(i)

    for i in ordered:
        if len(selected_set) >= k:
            break
        selected_set.add(i)

    return [i for i in ordered if i in selected_set][:k]


def _select_candidate(
    candidates: List[Dict[str, Any]],
    *,
    feasible_decision: bool,
    selection_mode: str,
    beta: float,
    rel_slack: float,
    abs_slack: float,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Select a candidate without allowing consistency to dominate accuracy.

    The default mode first identifies the best validation error inside the hard
    feasible set.  Consistency is used only among candidates whose validation
    error lies inside a small near-optimal interval.
    """
    if not feasible_decision:
        pool = sorted(candidates, key=lambda x: (x["f_pred"], x["arch_idx"]))
        return (pool[0] if pool else None), {
            "selection_mode": "validation_only_without_hard_filter",
            "feasible_pool_size": len(candidates),
            "near_optimal_pool_size": 1 if pool else 0,
            "validation_threshold": None,
        }

    feasible = [x for x in candidates if bool(x["hard_feasible"])]
    if not feasible:
        return None, {
            "selection_mode": str(selection_mode),
            "feasible_pool_size": 0,
            "near_optimal_pool_size": 0,
            "validation_threshold": None,
        }

    mode = str(selection_mode).strip().lower()
    best_pred = min(feasible, key=lambda x: (x["f_pred"], x["arch_idx"]))

    if mode == "weighted_sum":
        selected = min(
            feasible,
            key=lambda x: (
                float(x["f_pred"]) + float(beta) * float(x["f_cons"]),
                x["f_pred"],
                x["arch_idx"],
            ),
        )
        threshold = None
        near = feasible
    elif mode == "validation_first":
        selected = min(
            feasible,
            key=lambda x: (x["f_pred"], x["f_cons"], x["arch_idx"]),
        )
        threshold = float(best_pred["f_pred"])
        near = [selected]
    elif mode == "near_optimal_consistency":
        threshold = (
            float(best_pred["f_pred"]) * (1.0 + max(0.0, float(rel_slack)))
            + max(0.0, float(abs_slack))
        )
        near = [x for x in feasible if float(x["f_pred"]) <= threshold]
        selected = min(near, key=lambda x: (x["f_cons"], x["f_pred"], x["arch_idx"]))
    else:
        raise ValueError(
            f"Unsupported selection_mode={selection_mode!r}. "
            "Use validation_first, near_optimal_consistency, or weighted_sum."
        )

    return selected, {
        "selection_mode": mode,
        "feasible_pool_size": len(feasible),
        "near_optimal_pool_size": len(near),
        "validation_threshold": threshold,
        "best_validation_arch_idx": int(best_pred["arch_idx"]),
        "best_validation_error": float(best_pred["f_pred"]),
    }


def _teacher_episode(
    *,
    cfg,
    mcfg,
    cache,
    A,
    bank,
    cid: int,
    H: int,
    K: int,
    device: torch.device,
    seed: int,
    n_arch: int,
    adapt_n: int,
) -> Dict[str, Any]:
    Xs, ys, Xv, yv, _Xc, _yc, _Xt, _yt, tier, _ctype = get_center_split_from_cache(
        cfg, cache, int(cid), int(H), int(K)
    )
    Xs, ys, Xv, yv = Xs.to(device), ys.to(device), Xv.to(device), yv.to(device)
    input_dim = int(Xs.shape[-1])
    rng = random.Random(int(seed) + 1009 * int(cid) + 37 * int(H) + 53 * int(K))
    idxs = list(range(len(A)))
    if int(n_arch) <= 4:
        # Fast deterministic smoke subset: use the lightest candidates.
        idxs.sort(key=lambda i: sum(profile_arch(A[i], L=int(cfg.main.task.L), input_dim=input_dim, H=int(H))))
    else:
        rng.shuffle(idxs)
    idxs = idxs[: min(int(n_arch), len(idxs))]
    Xv_eval, yv_eval = (Xv[:64], yv[:64]) if int(n_arch) <= 4 else (Xv, yv)

    losses: Dict[int, float] = {}
    for i in idxs:
        spec = A[int(i)]
        model, prior = _load_prior_model(
            spec=spec, H=H, L=int(cfg.main.task.L), input_dim=input_dim, bank=bank, device=device
        )
        adapt_steps(
            model,
            Xs,
            ys,
            steps=int(adapt_n),
            lr=float(mcfg.adapt_lr),
            robust_loss_type="huber",
            huber_delta=float(mcfg.huber_delta),
            cvar_lambda=0.0,
            prior_state=prior,
            prior_group_lambdas=None,
            seed=int(seed) + int(i),
        )
        model.eval()
        with torch.no_grad():
            pv = model(Xv_eval)
        loss = float(eval_mse(pv, yv_eval))
        feasibility_penalty = float(
            getattr(mcfg, "control_teacher_feasibility_penalty", 0.0)
        )
        if (
            feasibility_penalty != 0.0
            and not _feasible(
                cfg, spec, tier, int(cfg.main.task.L), input_dim, H
            )
        ):
            loss += feasibility_penalty
        losses[int(i)] = loss

    vals = torch.tensor([-losses[i] for i in idxs], device=device, dtype=torch.float32)
    target_probs = torch.softmax(vals / 0.25, dim=0).detach()
    best_idx = int(idxs[int(torch.argmax(target_probs).item())])
    return {
        "cid": int(cid),
        "H": int(H),
        "K": int(K),
        "tier": str(tier),
        "idxs": idxs,
        "target_probs": target_probs.cpu(),
        "best_idx": best_idx,
        "losses": losses,
    }


def _functional_controller_val_loss(
    *,
    model,
    prior_state: Dict[str, torch.Tensor],
    Xs: torch.Tensor,
    ys: torch.Tensor,
    Xv: torch.Tensor,
    yv: torch.Tensor,
    modulation: torch.Tensor,
    prior_lambda: torch.Tensor,
    inner_steps: int,
    lr: float,
    huber_delta: float,
) -> torch.Tensor:
    params0 = {
        n: p.detach().clone().requires_grad_(True)
        for n, p in model.named_parameters()
    }
    params = dict(params0)
    buffers = {n: b.detach() for n, b in model.named_buffers()}

    # A differentiable inner loop requires second-order gradients when the
    # outer controller loss is backpropagated. CuDNN RNN kernels do not
    # implement double backward, so GRU/LSTM/RNN candidates must use the
    # native PyTorch RNN path for this meta-gradient only.
    has_cudnn_rnn = bool(
        Xs.is_cuda
        and torch.backends.cudnn.enabled
        and any(
            isinstance(module, (torch.nn.GRU, torch.nn.LSTM, torch.nn.RNN))
            for module in model.modules()
        )
    )
    rnn_backend_context = (
        torch.backends.cudnn.flags(enabled=False)
        if has_cudnn_rnn
        else nullcontext()
    )

    with rnn_backend_context:
        for _ in range(int(inner_steps)):
            merged = {**params, **buffers}
            pred = functional_call(model, merged, (Xs,))
            loss = F.huber_loss(pred, ys, delta=float(huber_delta), reduction="mean")
            grads = torch.autograd.grad(loss, tuple(params.values()), create_graph=True)
            new_params = {}
            for (name, p), grad in zip(params.items(), grads):
                gid = GROUP_TO_ID[parameter_group(name)]
                p0 = params0[name]
                new_params[name] = (
                    p
                    - float(lr) * modulation[gid] * grad
                    - float(lr) * prior_lambda * (p - p0)
                )
            params = new_params

        pred_v = functional_call(model, {**params, **buffers}, (Xv,))
        val_loss = ((pred_v - yv) ** 2).mean()

    return val_loss


def _make_stack(mcfg, portrait_dim: int, num_arch: int, device: torch.device) -> PaperConditionStack:
    return PaperConditionStack(
        portrait_dim=int(portrait_dim),
        budget_dim=5,
        task_dim=int(mcfg.task_feature_dim),
        num_arch=int(num_arch),
        state_hidden_dim=int(mcfg.state_hidden_dim),
        state_embed_dim=int(mcfg.state_embed_dim),
        budget_hidden_dim=int(mcfg.budget_hidden_dim),
        budget_embed_dim=int(mcfg.budget_embed_dim),
        task_hidden_dim=int(mcfg.task_hidden_dim),
        task_embed_dim=int(mcfg.task_embed_dim),
        condition_dim=int(mcfg.condition_dim),
        condition_hidden_dim=int(mcfg.condition_hidden_dim),
        arch_residual_alpha_max=float(mcfg.arch_residual_alpha_max),
        arch_residual_alpha_init=float(mcfg.arch_residual_alpha_init),
        modulation_min=float(mcfg.modulation_min),
        modulation_max=float(mcfg.modulation_max),
        prior_lambda_min=float(mcfg.prior_lambda_min),
        prior_lambda_max=float(mcfg.prior_lambda_max),
    ).to(device)


def _train_or_load_control(
    *,
    cfg,
    mcfg,
    cache,
    A,
    bank,
    bank_path: str,
    bank_meta: BankMeta,
    prior_stats: Dict[str, Any],
    device: torch.device,
    control_path: str,
    smoke: bool,
) -> Tuple[PaperConditionStack, torch.Tensor, Dict[str, Any]]:
    L = int(cfg.main.task.L)
    H0 = int(cfg.main.task.H_list[0])
    K0 = int(cfg.main.task.K_list[0])
    Xs0, *_ = get_center_split_from_cache(cfg, cache, 0, H0, K0)
    portrait0 = portrait_from_support(Xs0.to(device))
    stack = _make_stack(
        mcfg,
        int(portrait0.numel()),
        len(A),
        device,
    )

    # Apply the same ablation switches during offline control learning
    # and online target-center instantiation.
    ablation_mode = str(
        getattr(mcfg, "condition_ablation_mode", "full")
    )
    (
        train_use_state,
        train_use_budget_admission,
        train_use_budget_adaptation,
        train_use_task,
        train_use_prior_mod,
        train_use_adapt_mod,
    ) = _resolve_condition_flags(mcfg)

    bank_path_abs = os.path.abspath(str(bank_path))
    if not os.path.isfile(bank_path_abs):
        raise FileNotFoundError(f"C1 WeightBank not found: {bank_path_abs}")
    bank_sha256 = _sha256_file(bank_path_abs)
    provenance = {
        "artifact_type": "condition_stack",
        "control_protocol_version": str(mcfg.control_version_tag),
        "prior_type": str(prior_stats.get("prior_type", "")),
        "prior_protocol_version": str(
            prior_stats.get("protocol_version", "")
        ),
        "bank_path_basename": os.path.basename(bank_path_abs),
        "bank_sha256": bank_sha256,
        "space_fingerprint": str(bank_meta.space_fingerprint),
        "input_dim": int(bank_meta.input_dim),
        "H_list": [int(x) for x in bank_meta.H_list],
        "K_list": [int(x) for x in cfg.main.task.K_list],
        "data_seed": int(cfg.main.sim.seed),
        "source_prior_seed": int(mcfg.source_prior_seed),
        "control_seed": int(mcfg.control_seed),
        "n_source_centers": int(cfg.main.split.n_train_centers),
        "num_architectures": int(len(A)),
        "admission_use_budget_condition": bool(
            train_use_budget_admission
        ),
        "adaptation_use_budget_condition": bool(
            train_use_budget_adaptation
        ),
        "teacher_feasibility_penalty": float(
            getattr(mcfg, "control_teacher_feasibility_penalty", 0.0)
        ),
    }

    if os.path.isfile(control_path) and not bool(
            mcfg.control_train_retrain
    ):
        obj = torch.load(control_path, map_location=device)
        loaded_provenance = dict(obj.get("provenance", {}))
        if bool(getattr(mcfg, "control_require_bank_provenance", True)):
            mismatches = {
                key: {"expected": value, "loaded": loaded_provenance.get(key)}
                for key, value in provenance.items()
                if loaded_provenance.get(key) != value
            }
            if mismatches:
                raise RuntimeError(
                    "Existing condition controller is not bound to the current "
                    "formal C1 WeightBank/protocol. Retrain it with "
                    "tools/train_condition_stack_c1.py. Mismatches: "
                    + json.dumps(mismatches, ensure_ascii=False, sort_keys=True)
                )
        stack.load_state_dict(obj["state_dict"], strict=True)
        stats = dict(obj.get("train_stats", {}))
        stats["loaded_from_artifact"] = True
        stats["provenance"] = loaded_provenance
        return stack, obj["pi"].to(device), stats

    n_train = int(cfg.main.split.n_train_centers)
    configured_centers = int(mcfg.control_train_centers)
    if configured_centers <= 0:
        centers_n = n_train
    else:
        centers_n = min(n_train, configured_centers)
    if smoke:
        centers_n = min(centers_n, 2)
    Hs = [int(cfg.main.task.H_list[0])] if smoke else list(map(int, cfg.main.task.H_list))
    if smoke or not bool(getattr(mcfg, "control_use_all_support_sizes", True)):
        Ks = [int(K0)]
    else:
        Ks = list(map(int, cfg.main.task.K_list))
    teacher_archs = 4 if smoke else int(mcfg.control_teacher_archs_per_task)
    teacher_steps = 1 if smoke else int(mcfg.control_teacher_adapt_steps)
    episodes: List[Dict[str, Any]] = []
    teacher_total = max(1, len(Hs) * len(Ks) * int(centers_n))
    teacher_done = 0
    print(
        "[ConditionController] building source teacher episodes: "
        f"total={teacher_total}, archs_per_task={teacher_archs}, "
        f"adapt_steps={teacher_steps}",
        flush=True,
    )
    for H in Hs:
        for K in Ks:
            for cid in range(centers_n):
                episodes.append(_teacher_episode(
                    cfg=cfg,
                    mcfg=mcfg,
                    cache=cache,
                    A=A,
                    bank=bank,
                    cid=cid,
                    H=H,
                    K=K,
                    device=device,
                    seed=int(mcfg.control_seed),
                    n_arch=teacher_archs,
                    adapt_n=teacher_steps,
                ))
                teacher_done += 1
                if teacher_done == 1 or teacher_done % 5 == 0 or teacher_done == teacher_total:
                    print(
                        "[ConditionController] teacher "
                        f"{teacher_done}/{teacher_total} "
                        f"(center={cid}, H={H}, K={K})",
                        flush=True,
                    )

    # Shared structural prior pi: average source-task evidence per architecture.
    accum = torch.zeros(len(A), dtype=torch.float32)
    counts = torch.zeros(len(A), dtype=torch.float32)
    for ep in episodes:
        vals = ep["losses"]
        if not vals:
            continue
        ordered = sorted(vals, key=lambda i: vals[i])
        denom = max(1, len(ordered) - 1)
        for rank, i in enumerate(ordered):
            accum[int(i)] += 1.0 - float(rank) / float(denom)
            counts[int(i)] += 1.0
    pi = accum / counts.clamp_min(1.0)
    pi = (pi - pi.mean()) / pi.std(unbiased=False).clamp_min(1e-6)
    pi = pi.to(device)

    opt = torch.optim.Adam(
        stack.parameters(), lr=float(mcfg.control_lr), weight_decay=float(mcfg.control_weight_decay)
    )
    epochs = 1 if smoke else int(mcfg.control_train_epochs)
    losses_log: List[float] = []
    structure_losses_log: List[float] = []
    adaptation_losses_log: List[float] = []
    anchor_losses_log: List[float] = []
    alpha_log: List[float] = []
    max_flops = float(cfg.main.budget.loose.flops)
    max_params = float(cfg.main.budget.loose.params)
    max_H = max(map(int, cfg.main.task.H_list))
    max_K = max(map(int, cfg.main.task.K_list))

    train_total = max(1, int(epochs) * len(episodes))
    train_done = 0
    print(
        "[ConditionController] optimizing controller: "
        f"epochs={epochs}, updates={train_total}",
        flush=True,
    )
    for epoch in range(epochs):
        random.Random(int(mcfg.control_seed) + epoch).shuffle(episodes)
        for ep in episodes:
            Xs, ys, Xv, yv, *_rest = get_center_split_from_cache(
                cfg, cache, int(ep["cid"]), int(ep["H"]), int(ep["K"])
            )
            Xs, ys, Xv, yv = Xs.to(device), ys.to(device), Xv.to(device), yv.to(device)
            portrait = portrait_from_support(Xs)
            bf, bp = _tier_limits(cfg, ep["tier"])
            budget = build_budget_features(
                budget_flops=bf,
                budget_params=bp,
                tier_name=ep["tier"],
                max_flops=max_flops,
                max_params=max_params,
                device=device,
                dtype=Xs.dtype,
            )
            task = build_task_features(
                H=int(ep["H"]),
                K=int(ep["K"]),
                max_H=max_H,
                max_K=max_K,
                device=device,
                dtype=Xs.dtype,
            )
            out = stack(
                portrait,
                budget,
                task,
                pi,
                use_state=train_use_state,
                use_budget_in_admission=train_use_budget_admission,
                use_budget_in_adaptation=train_use_budget_adaptation,
                use_task=train_use_task,
                use_prior_modulation=train_use_prior_mod,
                use_adaptation_modulation=train_use_adapt_mod,
            )

            idx = torch.tensor(
                ep["idxs"],
                device=device,
                dtype=torch.long,
            )
            target_probs = ep["target_probs"].to(device)
            structure_loss = -(target_probs * torch.log_softmax(out["rho"][idx], dim=0)).sum()

            if smoke:
                # Smoke mode validates the full execution chain without the
                # expensive higher-order controller meta-gradient.
                adapt_val_loss = torch.zeros((), device=device)
            else:
                spec = A[int(ep["best_idx"])]
                model, prior = _load_prior_model(
                    spec=spec,
                    H=int(ep["H"]),
                    L=L,
                    input_dim=int(Xs.shape[-1]),
                    bank=bank,
                    device=device,
                )
                adapt_val_loss = _functional_controller_val_loss(
                    model=model,
                    prior_state=prior,
                    Xs=Xs,
                    ys=ys,
                    Xv=Xv,
                    yv=yv,
                    modulation=out["modulation"],
                    prior_lambda=out["prior_lambda"],
                    inner_steps=int(mcfg.control_inner_steps),
                    lr=float(mcfg.adapt_lr),
                    huber_delta=float(mcfg.huber_delta),
                )
            # Trust-region regularization keeps the learned target-specific
            # ranking close to the transferable global prior unless source-side
            # evidence consistently supports a residual correction.
            anchor_loss = ((out["rho"] - pi) ** 2).mean()
            total = (
                float(mcfg.control_structure_loss_weight) * structure_loss
                + float(mcfg.control_adaptation_loss_weight) * adapt_val_loss
                + float(mcfg.control_anchor_loss_weight) * anchor_loss
            )
            opt.zero_grad(set_to_none=True)
            total.backward()
            torch.nn.utils.clip_grad_norm_(stack.parameters(), 5.0)
            opt.step()
            losses_log.append(float(total.detach().item()))
            structure_losses_log.append(float(structure_loss.detach().item()))
            adaptation_losses_log.append(float(adapt_val_loss.detach().item()))
            anchor_losses_log.append(float(anchor_loss.detach().item()))
            alpha_log.append(float(out["arch_alpha"].detach().item()))
            train_done += 1
            if train_done == 1 or train_done % 10 == 0 or train_done == train_total:
                print(
                    "[ConditionController] update "
                    f"{train_done}/{train_total} "
                    f"epoch={epoch + 1}/{epochs} "
                    f"loss={losses_log[-1]:.6g} "
                    f"alpha={alpha_log[-1]:.4f}",
                    flush=True,
                )

    stats = {
        "episodes": len(episodes),
        "epochs": epochs,
        "source_centers": int(centers_n),
        "H_values": [int(x) for x in Hs],
        "K_values": [int(x) for x in Ks],
        "teacher_adapt_steps": int(teacher_steps),
        "mean_loss": float(sum(losses_log) / max(1, len(losses_log))),
        "mean_structure_loss": float(
            sum(structure_losses_log) / max(1, len(structure_losses_log))
        ),
        "mean_adaptation_loss": float(
            sum(adaptation_losses_log) / max(1, len(adaptation_losses_log))
        ),
        "mean_anchor_loss": float(
            sum(anchor_losses_log) / max(1, len(anchor_losses_log))
        ),
        "mean_arch_alpha": float(sum(alpha_log) / max(1, len(alpha_log))),
        "controller_architecture": "split_anchored_c1_v1",
        "ablation_tag": str(
            getattr(mcfg, "ablation_tag", "full")
        ),
        "condition_ablation_mode": ablation_mode,
        "train_use_state": bool(train_use_state),
        "train_use_budget_in_admission": bool(
            train_use_budget_admission
        ),
        "train_use_budget_in_adaptation": bool(
            train_use_budget_adaptation
        ),
        "train_use_task": bool(train_use_task),
        "train_use_task_in_admission": bool(train_use_task),
        "train_use_task_in_adaptation": False,
        "task_feature_dim": int(mcfg.task_feature_dim),
        "arch_residual_alpha_max": float(mcfg.arch_residual_alpha_max),
        "arch_residual_alpha_init": float(mcfg.arch_residual_alpha_init),
        "control_anchor_loss_weight": float(mcfg.control_anchor_loss_weight),
        "teacher_feasibility_penalty": float(
            getattr(mcfg, "control_teacher_feasibility_penalty", 0.0)
        ),
        "train_use_prior_modulation": bool(
            train_use_prior_mod
        ),
        "train_use_adaptation_modulation": bool(
            train_use_adapt_mod
        ),
    }
    os.makedirs(os.path.dirname(control_path), exist_ok=True)
    stats["provenance"] = provenance
    torch.save({
        "state_dict": {k: v.detach().cpu() for k, v in stack.state_dict().items()},
        "pi": pi.detach().cpu(),
        "portrait_dim": int(portrait0.numel()),
        "controller_architecture": "split_anchored_c1_v1",
        "provenance": provenance,
        "train_stats": stats,
    }, control_path)
    return stack, pi, stats


def _build_or_load_bank(*, cfg, mcfg, cache, A, device: torch.device, bank_path: str, smoke: bool):
    """Build/load the frozen shared prior used by the formal pipeline.

    ``source_pooled_c1`` is the selected formal protocol. The previous Reptile
    path remains available only as ``legacy_reptile`` for historical runs.
    """
    prior_type = str(getattr(mcfg, "prior_type", "legacy_reptile")).strip().lower()
    if prior_type == "source_pooled_c1":
        return build_or_load_source_pooled_c1(
            cfg=cfg,
            mcfg=mcfg,
            cache=cache,
            A=A,
            device=device,
            bank_path=bank_path,
            smoke=smoke,
        )

    if prior_type != "legacy_reptile":
        raise ValueError(
            f"Unsupported prior_type={prior_type!r}; use source_pooled_c1 "
            "or legacy_reptile."
        )

    L = int(cfg.main.task.L)
    H_list = [int(cfg.main.task.H_list[0])] if smoke else list(map(int, cfg.main.task.H_list))
    Xs0, *_ = get_center_split_from_cache(
        cfg, cache, 0, H_list[0], int(cfg.main.task.K_list[0])
    )
    input_dim = int(Xs0.shape[-1])
    fp = _space_fingerprint(A)

    if smoke:
        return (
            BankMeta(space_fingerprint=fp, input_dim=input_dim, H_list=H_list),
            {},
            {"prior_type": "legacy_reptile", "status": "smoke_empty_bank"},
        )

    if os.path.isfile(bank_path):
        meta, bank = load_weight_bank(bank_path, map_location="cpu")
        if meta.space_fingerprint == fp and meta.input_dim == input_dim:
            return meta, bank, {"prior_type": "legacy_reptile", "status": "loaded"}

    meta = BankMeta(space_fingerprint=fp, input_dim=input_dim, H_list=H_list)
    bank = init_bank_from_space(A, input_dim=input_dim, H_list=H_list, L=L, device=device)
    if bool(mcfg.do_meta_train):
        bank = reptile_meta_train(
            A_specs=A,
            bank=bank,
            input_dim=input_dim,
            H_list=H_list,
            L=L,
            train_center_ids=list(range(int(cfg.main.split.n_train_centers))),
            get_task_split_fn=get_center_split_from_cache,
            cfg=cfg,
            cache=cache,
            meta_epochs=int(mcfg.meta_epochs),
            meta_tasks_per_epoch=int(mcfg.meta_tasks_per_epoch),
            archs_per_task=int(mcfg.archs_per_task),
            inner_steps=int(mcfg.inner_steps),
            inner_lr=float(mcfg.inner_lr),
            meta_step_size=float(mcfg.meta_step_size),
            meta_seed=int(mcfg.meta_seed),
            device=device,
        )
    save_weight_bank(bank_path, meta, bank)
    return meta, bank, {"prior_type": "legacy_reptile", "status": "complete"}


def _write_outputs(out_dir: str, method_name: str, detail: List[dict]) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{method_name}_detail.json"), "w", encoding="utf-8") as f:
        json.dump(detail, f, ensure_ascii=False, indent=2)

    groups: Dict[Tuple[int, int, str, str], List[dict]] = {}
    for r in detail:
        groups.setdefault((r["H"], r["K"], r["center_type"], r["tier"]), []).append(r)
    summary = []
    for key, rows in sorted(groups.items()):
        H, K, ctype, tier = key
        feasible = [r for r in rows if int(r["FeasibleStar"]) == 1]
        def ms(field):
            return mean_std([float(r[field]) for r in feasible if r.get(field) is not None])
        mse_m, mse_s = ms("MSE_test")
        mae_m, mae_s = ms("MAE_test")
        w_m, w_s = ms("Worst10_test")
        summary.append({
            "method": method_name,
            "H": H, "K": K, "center_type": ctype, "tier": tier,
            "N_total": len(rows), "N_eval": len(feasible),
            "FeasibleRate": sum(int(r["FeasibleStar"]) for r in rows) / max(1, len(rows)),
            "MSE_test_mean": mse_m, "MSE_test_std": mse_s,
            "MAE_test_mean": mae_m, "MAE_test_std": mae_s,
            "Worst10_test_mean": w_m, "Worst10_test_std": w_s,
        })
    with open(os.path.join(out_dir, f"{method_name}_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    if summary:
        with open(os.path.join(out_dir, f"{method_name}_summary.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
            w.writeheader(); w.writerows(summary)


def run_paper_aligned(cfg, *, method_name: str) -> Dict[str, float]:
    mcfg = cfg.method
    device_name = str(cfg.main.device)
    if device_name.startswith("cuda") and not torch.cuda.is_available():
        device_name = "cpu"
    device = torch.device(device_name)
    cfg.main.device = str(device)
    smoke = bool(getattr(cfg, "runtime", {}).get("smoke", False))
    out_dir = os.path.abspath(str(cfg.main.out_dir))
    os.makedirs(out_dir, exist_ok=True)

    cache = build_meta_dataset_cache(cfg)
    A = enumerate_A_base(cfg.main.arch)
    if len(A) != 66:
        raise RuntimeError(f"Paper protocol requires 66 candidates, got {len(A)}")
    L = int(cfg.main.task.L)

    version_tag = str(mcfg.runner_version_tag)
    bank_version_tag = str(getattr(mcfg, "bank_version_tag", version_tag))
    control_version_tag = str(getattr(mcfg, "control_version_tag", version_tag))
    source_tag = f"src{int(cfg.main.split.n_train_centers)}"

    # Fair-V5 factorial diagnostics must reuse exactly the same source-side
    # weight bank and complete condition stack.  Set OURS_ARTIFACT_DIR to a
    # shared directory before running Full and the diagnostic variants.
    shared_artifact_dir = str(os.environ.get("OURS_ARTIFACT_DIR", "")).strip()
    artifact_root = os.path.abspath(shared_artifact_dir) if shared_artifact_dir else out_dir
    os.makedirs(artifact_root, exist_ok=True)
    bank_path = str(
        mcfg.bank_path
        or os.path.join(artifact_root, f"ours_weight_bank_{bank_version_tag}_{source_tag}.pt")
    )
    control_path = str(
        mcfg.control_path
        or os.path.join(artifact_root, f"ours_condition_stack_{control_version_tag}_{source_tag}.pt")
    )
    bank_meta, bank, prior_stats = _build_or_load_bank(
        cfg=cfg,
        mcfg=mcfg,
        cache=cache,
        A=A,
        device=device,
        bank_path=bank_path,
        smoke=smoke,
    )
    stack, pi, train_stats = _train_or_load_control(
        cfg=cfg,
        mcfg=mcfg,
        cache=cache,
        A=A,
        bank=bank,
        bank_path=bank_path,
        bank_meta=bank_meta,
        prior_stats=prior_stats,
        device=device,
        control_path=control_path,
        smoke=smoke,
    )
    stack.eval()

    n_train = int(cfg.main.split.n_train_centers)
    n_test = min(
        int(cfg.main.split.n_test_centers),
        1 if smoke else int(cfg.main.split.n_test_centers),
    )
    test_ids = list(range(n_train, n_train + n_test))

    full_H_list = list(map(int, cfg.main.task.H_list))
    full_K_list = list(map(int, cfg.main.task.K_list))

    export_downstream = bool(
        getattr(cfg.main, "export_downstream", False)
    )
    downstream_rep_only = bool(
        getattr(cfg.main, "downstream_rep_only", True)
    )
    downstream_rows: List[dict] = []

    if export_downstream and downstream_rep_only:
        # The journal operational check uses one representative setting.
        # Raw predictions are exported once and reused for every threshold q.
        H_list = [1 if 1 in full_H_list else int(full_H_list[0])]
        K_list = [20 if 20 in full_K_list else int(full_K_list[-1])]
    else:
        H_list = [int(full_H_list[0])] if smoke else full_H_list
        K_list = [int(full_K_list[0])] if smoke else full_K_list

    progress = ProgressTracker(
        total=max(1, len(H_list) * len(K_list) * len(test_ids)),
        name=method_name,
        print_every=max(1, int(mcfg.progress_print_every)),
    )
    max_flops = float(cfg.main.budget.loose.flops)
    max_params = float(cfg.main.budget.loose.params)
    max_H = max(map(int, cfg.main.task.H_list))
    max_K = max(map(int, cfg.main.task.K_list))
    protocol_adapt_steps = int(cfg.main.search.T_adapt_steps)
    configured_adapt_steps = int(
        getattr(mcfg, "adapt_steps", protocol_adapt_steps)
    )
    if configured_adapt_steps != protocol_adapt_steps:
        raise RuntimeError(
            "Ours adapt_steps must equal the common protocol "
            f"T_adapt_steps: {configured_adapt_steps} != {protocol_adapt_steps}"
        )
    T_adapt = 2 if smoke else configured_adapt_steps

    tag = str(getattr(mcfg, "ablation_tag", "full")).lower()
    (
        use_state,
        use_budget_admission,
        use_budget_adaptation,
        use_task,
        use_prior_mod,
        use_adapt_mod,
    ) = _resolve_condition_flags(mcfg)
    diagnostic_mode = str(getattr(mcfg, "diagnostic_mode", "full")).strip().lower()
    diagnostic_active = diagnostic_mode in {
        "global_plain",
        "admission_only",
        "adaptation_only",
        "admission_no_task",
        "adaptation_no_task",
        "full_split",
        "full_no_task",
    }
    diag_admission_condition = bool(
        getattr(mcfg, "diagnostic_admission_condition", True)
    )
    diag_adaptation_condition = bool(
        getattr(mcfg, "diagnostic_adaptation_condition", True)
    )
    diag_task_in_admission = bool(
        getattr(mcfg, "diagnostic_task_in_admission", True)
    )
    # Fair-V5.2 intentionally has no direct task-descriptor path to the
    # adaptation controller.  Keep the field for output compatibility, but the
    # effective value is always False.
    diag_task_in_adaptation = False
    diag_keep_budget = bool(
        getattr(mcfg, "diagnostic_keep_budget_preinsertion", True)
    )
    feasible_decision = bool(getattr(mcfg, "feasible_decision_enable", True))
    selection_mode = str(getattr(mcfg, "selection_mode", "near_optimal_consistency"))
    selection_rel_slack = float(getattr(mcfg, "selection_rel_slack", 0.005))
    selection_abs_slack = float(getattr(mcfg, "selection_abs_slack", 1e-8))

    # ------------------------------------------------------------------
    # Post-selection diagnostics. These switches never alter candidate
    # admission, target adaptation, DT* selection, or the reported main result.
    # They only expose the internal ranking path and, after DT* is fixed,
    # evaluate additional candidates for causal diagnosis.
    # ------------------------------------------------------------------
    diagnostic_trace_enable = _env_flag("OURS_DIAGNOSTIC_ENABLE", False)
    diagnostic_scope = str(
        os.environ.get("OURS_DIAGNOSTIC_SCOPE", "stage1")
    ).strip().lower()
    if diagnostic_scope not in {"admitted", "stage1", "feasible_all"}:
        raise ValueError(
            "OURS_DIAGNOSTIC_SCOPE must be admitted, stage1, or feasible_all"
        )
    diagnostic_tiers = _env_csv_set("OURS_DIAGNOSTIC_TIERS")
    diagnostic_hk_pairs = _env_csv_set("OURS_DIAGNOSTIC_HK")
    diagnostic_max_tasks = int(
        str(os.environ.get("OURS_DIAGNOSTIC_MAX_TASKS", "0")).strip() or "0"
    )
    diagnostic_records: List[dict] = []
    diagnostic_tasks_done = 0

    if diagnostic_trace_enable:
        print(
            "[CandidateDiagnostic] enabled "
            f"scope={diagnostic_scope} "
            f"tiers={sorted(diagnostic_tiers) if diagnostic_tiers else 'all'} "
            f"hk={sorted(diagnostic_hk_pairs) if diagnostic_hk_pairs else 'all'} "
            f"max_tasks={diagnostic_max_tasks if diagnostic_max_tasks > 0 else 'all'}"
        )

    detail: List[dict] = []
    for H in H_list:
        for K in K_list:
            for cid in test_ids:
                timer = Timer(); t_all = timer.tic()
                Xs, ys, Xv, yv, Xc, yc, Xt, yt, tier, ctype = get_center_split_from_cache(
                    cfg, cache, cid, H, K
                )
                Xs, ys = Xs.to(device), ys.to(device)
                Xv, yv = Xv.to(device), yv.to(device)
                Xc, yc = Xc.to(device), yc.to(device)
                # Keep test tensors untouched until DT* is fixed.
                input_dim = int(Xs.shape[-1])
                bf, bp = _tier_limits(cfg, tier)
                portrait = portrait_from_support(Xs)
                budget = build_budget_features(
                    budget_flops=bf, budget_params=bp, tier_name=tier,
                    max_flops=max_flops, max_params=max_params,
                    device=device, dtype=Xs.dtype,
                )
                task = build_task_features(
                    H=int(H),
                    K=int(K),
                    max_H=max_H,
                    max_K=max_K,
                    device=device,
                    dtype=Xs.dtype,
                )
                with torch.no_grad():
                    if diagnostic_active:
                        # Two interventions are evaluated from the same frozen
                        # complete stack.  The admission branch controls rho;
                        # the adaptation branch controls m and lambda.
                        admission_control = stack(
                            portrait, budget, task, pi,
                            use_state=True,
                            use_budget_in_admission=False,
                            use_budget_in_adaptation=False,
                            use_task=diag_task_in_admission,
                            use_prior_modulation=diag_admission_condition,
                            use_adaptation_modulation=False,
                        )
                        adaptation_control = stack(
                            portrait, budget, task, pi,
                            use_state=True,
                            use_budget_in_admission=False,
                            use_budget_in_adaptation=True,
                            use_task=diag_task_in_adaptation,
                            use_prior_modulation=False,
                            use_adaptation_modulation=diag_adaptation_condition,
                        )
                        control = {
                            "condition": admission_control["arch_condition"],
                            "arch_condition": admission_control["arch_condition"],
                            "adapt_condition": adaptation_control["adapt_condition"],
                            "arch_gate": admission_control["arch_gate"],
                            "adapt_gate": adaptation_control["adapt_gate"],
                            "rho": admission_control["rho"],
                            "arch_alpha": admission_control["arch_alpha"],
                            "arch_residual": admission_control["arch_residual"],
                            "modulation": adaptation_control["modulation"],
                            "prior_lambda": adaptation_control["prior_lambda"],
                        }
                        admission_budget_enabled = bool(diag_keep_budget)
                    else:
                        control = stack(
                            portrait, budget, task, pi,
                            use_state=use_state,
                            use_budget_in_admission=use_budget_admission,
                            use_budget_in_adaptation=use_budget_adaptation,
                            use_task=use_task,
                            use_prior_modulation=use_prior_mod,
                            use_adaptation_modulation=use_adapt_mod,
                        )
                        admission_budget_enabled = bool(
                            getattr(mcfg, "admission_budget_score_enable", True)
                        ) and str(
                            getattr(mcfg, "condition_ablation_mode", "full")
                        ).lower() not in {
                            "no_constraint_preinsertion",
                            "no_condition",
                        }
                ranked, admission_scores = _rank_candidates(
                    rho=control["rho"], A=A, cfg=cfg, tier=tier, L=L,
                    input_dim=input_dim, H=H,
                    budget_weight=float(mcfg.admission_budget_weight),
                    use_budget=admission_budget_enabled,
                )
                ranked_full = list(ranked)
                if smoke:
                    # Keep smoke execution cheap but still ensure at least one
                    # deployable candidate under the sampled budget tier.
                    light = [
                        i for i, spec in enumerate(A)
                        if _feasible(cfg, spec, tier, L, input_dim, H)
                    ][:2]
                    if not light:
                        light = ranked[:2]
                    light_set = set(light)
                    ranked = [i for i in ranked if i in light_set]
                stage1_limit = 2 if smoke else int(mcfg.cand_stage1_k)
                stage2_limit = 1 if smoke else min(int(cfg.main.search.K_arch), int(mcfg.cand_stage2_k))
                use_diversity = bool(getattr(mcfg, "diversity_admission_enable", True)) and not smoke
                stage1_quota = int(getattr(mcfg, "stage1_min_per_family", 0)) if use_diversity else 0
                stage2_quota = int(getattr(mcfg, "stage2_min_per_family", 0)) if use_diversity else 0
                feasible_first = (
                    bool(getattr(mcfg, "feasible_first_admission", True))
                    and bool(admission_budget_enabled)
                    and not smoke
                )
                stage1 = _diversity_aware_select(
                    ranked,
                    A=A,
                    k=stage1_limit,
                    min_per_family=stage1_quota,
                    cfg=cfg,
                    tier=tier,
                    L=L,
                    input_dim=input_dim,
                    H=H,
                    feasible_first=feasible_first,
                )
                admitted = _diversity_aware_select(
                    stage1,
                    A=A,
                    k=stage2_limit,
                    min_per_family=stage2_quota,
                    cfg=cfg,
                    tier=tier,
                    L=L,
                    input_dim=input_dim,
                    H=H,
                    feasible_first=feasible_first,
                )

                # Candidate-admission audit. The reference pool uses the shared
                # structural prior without target condition or budget information.
                # These diagnostics use no test data.
                base_ranked, _base_scores = _rank_candidates(
                    rho=pi,
                    A=A,
                    cfg=cfg,
                    tier=tier,
                    L=L,
                    input_dim=input_dim,
                    H=H,
                    budget_weight=0.0,
                    use_budget=False,
                )
                base_stage1 = _diversity_aware_select(
                    base_ranked,
                    A=A,
                    k=stage1_limit,
                    min_per_family=stage1_quota,
                    cfg=cfg,
                    tier=tier,
                    L=L,
                    input_dim=input_dim,
                    H=H,
                    feasible_first=False,
                )
                admission_changed_pool = int(set(stage1) != set(base_stage1))

                no_budget_ranked, _no_budget_scores = _rank_candidates(
                    rho=control["rho"],
                    A=A,
                    cfg=cfg,
                    tier=tier,
                    L=L,
                    input_dim=input_dim,
                    H=H,
                    budget_weight=0.0,
                    use_budget=False,
                )
                no_budget_stage1 = _diversity_aware_select(
                    no_budget_ranked,
                    A=A,
                    k=stage1_limit,
                    min_per_family=stage1_quota,
                    cfg=cfg,
                    tier=tier,
                    L=L,
                    input_dim=input_dim,
                    H=H,
                    feasible_first=False,
                )
                budget_changed_pool = int(set(stage1) != set(no_budget_stage1))

                # Exact global-admission counterfactual under the same budget
                # pre-insertion and diversity rules. This is more informative
                # than the legacy no-budget base pool and is used only for
                # diagnostics.
                global_budget_ranked, global_budget_scores = _rank_candidates(
                    rho=pi,
                    A=A,
                    cfg=cfg,
                    tier=tier,
                    L=L,
                    input_dim=input_dim,
                    H=H,
                    budget_weight=float(mcfg.admission_budget_weight),
                    use_budget=admission_budget_enabled,
                )
                global_budget_stage1 = _diversity_aware_select(
                    global_budget_ranked,
                    A=A,
                    k=stage1_limit,
                    min_per_family=stage1_quota,
                    cfg=cfg,
                    tier=tier,
                    L=L,
                    input_dim=input_dim,
                    H=H,
                    feasible_first=feasible_first,
                )
                global_budget_admitted = _diversity_aware_select(
                    global_budget_stage1,
                    A=A,
                    k=stage2_limit,
                    min_per_family=stage2_quota,
                    cfg=cfg,
                    tier=tier,
                    L=L,
                    input_dim=input_dim,
                    H=H,
                    feasible_first=feasible_first,
                )

                task_diag_enabled = bool(
                    diagnostic_trace_enable
                    and _diagnostic_task_enabled(
                        tier=tier,
                        H=H,
                        K=K,
                        tiers=diagnostic_tiers,
                        hk_pairs=diagnostic_hk_pairs,
                    )
                    and (
                        diagnostic_max_tasks <= 0
                        or diagnostic_tasks_done < diagnostic_max_tasks
                    )
                )

                score_trace: List[Dict[str, Any]] = []
                if task_diag_enabled:
                    rank_global_no_budget = _rank_position(base_ranked)
                    rank_condition_no_budget = _rank_position(no_budget_ranked)
                    rank_global_budget = _rank_position(global_budget_ranked)
                    rank_condition_budget = _rank_position(ranked_full)
                    pos_stage1 = _rank_position(stage1)
                    pos_stage2 = _rank_position(admitted)
                    pos_global_stage1 = _rank_position(global_budget_stage1)
                    pos_global_stage2 = _rank_position(global_budget_admitted)

                    arch_residual_vec = control["arch_residual"].detach().cpu().reshape(-1)
                    rho_vec = control["rho"].detach().cpu().reshape(-1)
                    pi_vec = pi.detach().cpu().reshape(-1)
                    alpha_value = float(control["arch_alpha"].detach().item())

                    for idx, spec in enumerate(A):
                        params_i, flops_i = profile_arch(
                            spec,
                            L=L,
                            input_dim=input_dim,
                            H=H,
                        )
                        compat_i = (
                            _budget_compatibility(
                                spec=spec,
                                cfg=cfg,
                                tier=tier,
                                L=L,
                                input_dim=input_dim,
                                H=H,
                            )
                            if admission_budget_enabled
                            else 0.0
                        )
                        score_trace.append({
                            "arch_idx": int(idx),
                            "arch_key": str(spec.arch_key),
                            "family": str(spec.family),
                            "params": float(params_i),
                            "flops": float(flops_i),
                            "hard_feasible": int(
                                _feasible(cfg, spec, tier, L, input_dim, H)
                            ),
                            "global_prior_score": float(pi_vec[idx].item()),
                            "arch_residual_raw": float(arch_residual_vec[idx].item()),
                            "arch_residual_alpha": float(alpha_value),
                            "effective_residual": float(
                                rho_vec[idx].item() - pi_vec[idx].item()
                            ),
                            "conditioned_prior_score": float(rho_vec[idx].item()),
                            "budget_compatibility": float(compat_i),
                            "global_budget_score": float(global_budget_scores[int(idx)]),
                            "conditioned_budget_score": float(admission_scores[int(idx)]),
                            "rank_global_no_budget": int(rank_global_no_budget[int(idx)]),
                            "rank_condition_no_budget": int(rank_condition_no_budget[int(idx)]),
                            "rank_global_budget": int(rank_global_budget[int(idx)]),
                            "rank_condition_budget": int(rank_condition_budget[int(idx)]),
                            "global_stage1_position": pos_global_stage1.get(int(idx)),
                            "global_stage2_position": pos_global_stage2.get(int(idx)),
                            "condition_stage1_position": pos_stage1.get(int(idx)),
                            "condition_stage2_position": pos_stage2.get(int(idx)),
                            "selected_global_stage1": int(int(idx) in set(global_budget_stage1)),
                            "selected_global_stage2": int(int(idx) in set(global_budget_admitted)),
                            "selected_condition_stage1": int(int(idx) in set(stage1)),
                            "selected_condition_stage2": int(int(idx) in set(admitted)),
                        })

                if stage1:
                    stage1_logits = torch.tensor(
                        [admission_scores[int(i)] for i in stage1],
                        dtype=torch.float32,
                    )
                    stage1_prob = torch.softmax(stage1_logits, dim=0)
                    selection_entropy = float(
                        -(stage1_prob * torch.log(stage1_prob.clamp_min(1e-12))).sum().item()
                    )
                else:
                    selection_entropy = 0.0
                admitted_families = sorted({str(A[int(i)].family) for i in admitted})
                family_diversity = float(len(admitted_families) / max(1, len(cfg.main.arch.families)))

                candidates: List[dict] = []
                model_cache: Dict[int, torch.nn.Module] = {}
                for i in admitted:
                    spec = A[int(i)]
                    model, prior_state = _load_prior_model(
                        spec=spec, H=H, L=L, input_dim=input_dim, bank=bank, device=device
                    )
                    model.eval()
                    Xv_eval, yv_eval = (Xv[:64], yv[:64]) if smoke else (Xv, yv)
                    Xc_eval, yc_eval = (Xc[:64], yc[:64]) if smoke else (Xc, yc)
                    with torch.no_grad():
                        pv_pre = model(Xv_eval)
                    pre_f_pred = eval_weighted_mse(pv_pre, yv_eval)
                    pre_worst10_val = eval_worst10(pv_pre, yv_eval, p=0.1)

                    adapt_condition_modulated(
                        model, Xs, ys,
                        steps=T_adapt,
                        lr=float(mcfg.adapt_lr),
                        modulation=control["modulation"],
                        prior_lambda=control["prior_lambda"],
                        prior_state=prior_state,
                        weight_decay=float(mcfg.adapt_weight_decay),
                        huber_delta=float(mcfg.huber_delta),
                        batch_size=int(mcfg.adapt_batch_size),
                        seed=int(mcfg.adapt_seed) + 1000 * cid + i,
                        max_grad_norm=float(mcfg.max_grad_norm),
                    )
                    model.eval()
                    with torch.no_grad():
                        pv = model(Xv_eval)
                        pc = model(Xc_eval)
                    f_pred = eval_weighted_mse(pv, yv_eval)
                    post_worst10_val = eval_worst10(pv, yv_eval, p=0.1)
                    f_cons, cons_parts = eval_paper_sequence_consistency(
                        pc, yc_eval, eta=tuple(mcfg.consistency_eta)
                    )
                    hard = _feasible(cfg, spec, tier, L, input_dim, H)
                    weighted_score = float(f_pred) + float(mcfg.dt_star_beta) * float(f_cons)
                    candidates.append({
                        "arch_idx": int(i),
                        "f_pred": f_pred,
                        "f_cons": f_cons,
                        "score": weighted_score,
                        "hard_feasible": hard,
                        "cons_parts": cons_parts,
                        "pre_f_pred": float(pre_f_pred),
                        "pre_worst10_val": float(pre_worst10_val),
                        "post_worst10_val": float(post_worst10_val),
                    })
                    model_cache[int(i)] = model

                selected, selection_diag = _select_candidate(
                    candidates,
                    feasible_decision=feasible_decision,
                    selection_mode=selection_mode,
                    beta=float(mcfg.dt_star_beta),
                    rel_slack=selection_rel_slack,
                    abs_slack=selection_abs_slack,
                )

                feasible_candidates = [x for x in candidates if bool(x["hard_feasible"])]
                best_pred_candidate = (
                    min(feasible_candidates, key=lambda x: (x["f_pred"], x["arch_idx"]))
                    if feasible_candidates else None
                )
                best_tail_candidate = (
                    min(feasible_candidates, key=lambda x: (x["post_worst10_val"], x["arch_idx"]))
                    if feasible_candidates else None
                )

                row: Dict[str, Any] = {
                    "method": method_name,
                    "shared_prior_type": str(
                        prior_stats.get(
                            "prior_type", getattr(mcfg, "prior_type", "unknown")
                        )
                    ),
                    "shared_prior_protocol_version": prior_stats.get("protocol_version"),
                    "shared_prior_status": prior_stats.get("status"),
                    "source_prior_seed": prior_stats.get(
                        "source_prior_seed", getattr(mcfg, "source_prior_seed", None)
                    ),
                    "source_pretrain_K": prior_stats.get(
                        "source_pretrain_K", getattr(mcfg, "source_pretrain_K", None)
                    ),
                    "source_pretrain_epochs": prior_stats.get(
                        "source_pretrain_epochs", getattr(mcfg, "source_pretrain_epochs", None)
                    ),
                    "source_refine_updates": prior_stats.get(
                        "source_refine_updates", getattr(mcfg, "source_refine_updates", None)
                    ),
                    "adapt_lr": float(mcfg.adapt_lr),
                    "ablation": (
                        ""
                        if method_name == "ours"
                        else tag
                    ),
                    "ablation_condition_mode": str(
                        getattr(
                            mcfg,
                            "condition_ablation_mode",
                            "full",
                        )
                    ),
                    "ablation_use_state": int(use_state),
                    "ablation_use_budget": int(use_budget),
                    "ablation_use_task": int(
                        (diag_task_in_admission or diag_task_in_adaptation)
                        if diagnostic_active else use_task
                    ),
                    "ablation_use_prior_modulation": int(
                        diag_admission_condition if diagnostic_active else use_prior_mod
                    ),
                    "ablation_use_adaptation_modulation": int(
                        diag_adaptation_condition if diagnostic_active else use_adapt_mod
                    ),
                    "diagnostic_mode": str(diagnostic_mode),
                    "diagnostic_admission_condition": int(
                        diag_admission_condition if diagnostic_active else use_prior_mod
                    ),
                    "diagnostic_adaptation_condition": int(
                        diag_adaptation_condition if diagnostic_active else use_adapt_mod
                    ),
                    "diagnostic_task_in_admission": int(
                        diag_task_in_admission if diagnostic_active else use_task
                    ),
                    "diagnostic_task_in_adaptation": 0,
                    "diagnostic_budget_preinsertion": int(
                        admission_budget_enabled
                    ),
                    "shared_artifact_dir": str(artifact_root),
                    "ablation_use_feasible_decision": int(
                        feasible_decision
                    ),
                    "center_id": int(cid),
                    "center_type": str(ctype),
                    "tier": str(tier),
                    "H": int(H), "K": int(K),
                    "stage1_size": len(stage1),
                    "adapted_candidates": len(admitted),
                    "candidate_budget": int(cfg.main.search.K_arch),
                    "selection_mode": str(selection_diag.get("selection_mode")),
                    "selection_rel_slack": float(selection_rel_slack),
                    "selection_abs_slack": float(selection_abs_slack),
                    "feasible_pool_size": int(selection_diag.get("feasible_pool_size", 0)),
                    "near_optimal_pool_size": int(selection_diag.get("near_optimal_pool_size", 0)),
                    "selection_validation_threshold": selection_diag.get("validation_threshold"),
                    "best_validation_arch_idx": selection_diag.get("best_validation_arch_idx"),
                    "best_validation_error": selection_diag.get("best_validation_error"),
                    "adapt_steps": int(T_adapt),
                    "control_train_centers_used": int(train_stats.get("source_centers", 0)),
                    "control_train_stats": train_stats,
                    "stage1_arch_indices": [int(i) for i in stage1],
                    "admitted_arch_indices": [int(i) for i in admitted],
                    "admitted_families": admitted_families,
                    "admission_changed_pool": int(admission_changed_pool),
                    "budget_changed_pool": int(budget_changed_pool),
                    "selection_entropy": float(selection_entropy),
                    "candidate_family_diversity": float(family_diversity),
                    "task_features": [float(x) for x in task.detach().cpu().tolist()],
                    "controller_architecture": "split_anchored_c1_v1",
                    "arch_residual_alpha": float(control["arch_alpha"].detach().item()),
                    "arch_gate_values": [
                        float(x) for x in control["arch_gate"].detach().cpu().tolist()
                    ],
                    "adapt_gate_values": [
                        float(x) for x in control["adapt_gate"].detach().cpu().tolist()
                    ],
                    "adaptation_modulation_values": [
                        float(x) for x in control["modulation"].detach().cpu().tolist()
                    ],
                    "adaptation_prior_lambda": float(
                        control["prior_lambda"].detach().cpu().item()
                    ),
                    "diversity_admission_enable": int(use_diversity),
                    "stage1_min_per_family": int(stage1_quota),
                    "stage2_min_per_family": int(stage2_quota),
                    "feasible_first_admission": int(feasible_first),
                    "MSE_test": None, "MAE_test": None, "Worst10_test": None,
                }
                if selected is None:
                    row.update({"evaluated": 0, "FeasibleStar": 0, "F_pred_val": None, "F_cons_chk": None})
                else:
                    i = int(selected["arch_idx"])
                    spec = A[i]
                    model_star = model_cache[i]
                    # Strict test isolation: this is the formal DT* test forward
                    # pass, after admission, adaptation and selection are complete.
                    # Optional extra candidate test passes occur only afterwards
                    # in the post-selection diagnostic block and never affect DT*.
                    Xt_dev, yt_dev = Xt.to(device), yt.to(device)
                    if smoke:
                        Xt_dev, yt_dev = Xt_dev[:64], yt_dev[:64]
                    with torch.no_grad():
                        pt = model_star(Xt_dev)
                    params, flops = profile_arch(spec, L=L, input_dim=input_dim, H=H)
                    row.update({
                        "evaluated": 1,
                        "FeasibleStar": int(_feasible(cfg, spec, tier, L, input_dim, H)),
                        "F_pred_val": float(selected["f_pred"]),
                        "F_cons_chk": float(selected["f_cons"]),
                        "selected_pre_F_pred_val": float(selected["pre_f_pred"]),
                        "selected_pre_Worst10_val": float(selected["pre_worst10_val"]),
                        "selected_post_Worst10_val": float(selected["post_worst10_val"]),
                        "selected_improves_prediction": int(
                            float(selected["f_pred"]) < float(selected["pre_f_pred"])
                        ),
                        "selected_improves_worst10": int(
                            float(selected["post_worst10_val"]) < float(selected["pre_worst10_val"])
                        ),
                        "matches_best_feasible_predictor": int(
                            best_pred_candidate is not None
                            and i == int(best_pred_candidate["arch_idx"])
                        ),
                        "matches_best_tail_predictor": int(
                            best_tail_candidate is not None
                            and i == int(best_tail_candidate["arch_idx"])
                        ),
                        "C_trend_chk": float(selected["cons_parts"]["trend"]),
                        "C_peak_chk": float(selected["cons_parts"]["peak"]),
                        "C_var_chk": float(selected["cons_parts"]["variation"]),
                        "dt_star_arch_idx": i,
                        "dt_star_arch_key": str(spec.arch_key),
                        "dt_star_family": str(spec.family),
                        "dt_star_params": float(params),
                        "dt_star_flops": float(flops),
                        "MSE_test": float(eval_mse(pt, yt_dev)),
                        "MAE_test": float(eval_mae(pt, yt_dev)),
                        "Worst10_test": float(eval_worst10(pt, yt_dev, p=0.1)),
                    })

                    if export_downstream:
                        keep_this_case = (
                            not downstream_rep_only
                            or (
                                int(H) == int(H_list[0])
                                and int(K) == int(K_list[0])
                            )
                        )

                        if keep_this_case:
                            # Threshold estimation uses only support and
                            # validation labels. Check/test labels never
                            # determine the overload threshold.
                            y_ref = torch.cat([ys, yv], dim=0)

                            downstream_rows.append({
                                "method": str(method_name),
                                "seed": int(getattr(cfg.main.sim, "seed", -1)),
                                "center_id": int(cid),
                                "center_type": str(ctype),
                                "tier": str(tier),
                                "H": int(H),
                                "K": int(K),
                                "reference_protocol": "support_plus_validation",
                                "n_reference_windows": int(y_ref.shape[0]),
                                "n_test_windows": int(yt_dev.shape[0]),
                                "y_ref": _tensor_to_2d_list(y_ref),
                                "y_true": _tensor_to_2d_list(yt_dev),
                                "y_pred": _tensor_to_2d_list(pt),
                                "dt_star_arch_idx": int(i),
                                "dt_star_arch_key": str(spec.arch_key),
                                "dt_star_family": str(spec.family),
                            })

                # ------------------------------------------------------
                # Post-selection candidate diagnostics.
                # IMPORTANT: DT* has already been fixed above. The extra
                # validation/check/test evaluations below are oracle-style
                # diagnostics only and cannot affect the reported selection.
                # ------------------------------------------------------
                if task_diag_enabled and selected is not None:
                    if diagnostic_scope == "admitted":
                        diagnostic_indices = [int(x) for x in admitted]
                    elif diagnostic_scope == "stage1":
                        diagnostic_indices = [int(x) for x in stage1]
                    else:
                        diagnostic_indices = [
                            int(idx)
                            for idx, spec_i in enumerate(A)
                            if _feasible(cfg, spec_i, tier, L, input_dim, H)
                        ]

                    admitted_metric_map = {
                        int(x["arch_idx"]): x for x in candidates
                    }
                    posthoc_candidates: List[Dict[str, Any]] = []

                    for idx in diagnostic_indices:
                        spec_i = A[int(idx)]
                        if int(idx) in model_cache:
                            model_i = model_cache[int(idx)]
                            metric_i = admitted_metric_map[int(idx)]
                            f_pred_i = float(metric_i["f_pred"])
                            f_cons_i = float(metric_i["f_cons"])
                            worst10_val_i = float(metric_i["post_worst10_val"])
                            source_i = "formal_admitted"
                        else:
                            model_i, prior_i = _load_prior_model(
                                spec=spec_i,
                                H=H,
                                L=L,
                                input_dim=input_dim,
                                bank=bank,
                                device=device,
                            )
                            adapt_condition_modulated(
                                model_i,
                                Xs,
                                ys,
                                steps=T_adapt,
                                lr=float(mcfg.adapt_lr),
                                modulation=control["modulation"],
                                prior_lambda=control["prior_lambda"],
                                prior_state=prior_i,
                                weight_decay=float(mcfg.adapt_weight_decay),
                                huber_delta=float(mcfg.huber_delta),
                                batch_size=int(mcfg.adapt_batch_size),
                                seed=int(mcfg.adapt_seed) + 1000 * cid + int(idx),
                                max_grad_norm=float(mcfg.max_grad_norm),
                            )
                            model_i.eval()
                            with torch.no_grad():
                                pv_i = model_i(Xv_eval)
                                pc_i = model_i(Xc_eval)
                            f_pred_i = float(eval_weighted_mse(pv_i, yv_eval))
                            worst10_val_i = float(eval_worst10(pv_i, yv_eval, p=0.1))
                            f_cons_i, _parts_i = eval_paper_sequence_consistency(
                                pc_i,
                                yc_eval,
                                eta=tuple(mcfg.consistency_eta),
                            )
                            f_cons_i = float(f_cons_i)
                            source_i = "posthoc_extra"

                        model_i.eval()
                        with torch.no_grad():
                            pt_i = model_i(Xt_dev)
                        mse_i = float(eval_mse(pt_i, yt_dev))
                        mae_i = float(eval_mae(pt_i, yt_dev))
                        worst10_i = float(eval_worst10(pt_i, yt_dev, p=0.1))
                        params_i, flops_i = profile_arch(
                            spec_i,
                            L=L,
                            input_dim=input_dim,
                            H=H,
                        )
                        posthoc_candidates.append({
                            "arch_idx": int(idx),
                            "arch_key": str(spec_i.arch_key),
                            "family": str(spec_i.family),
                            "source": str(source_i),
                            "hard_feasible": int(
                                _feasible(cfg, spec_i, tier, L, input_dim, H)
                            ),
                            "params": float(params_i),
                            "flops": float(flops_i),
                            "selected_dt_star": int(
                                int(idx) == int(selected["arch_idx"])
                            ),
                            "in_formal_stage1": int(int(idx) in set(stage1)),
                            "in_formal_stage2": int(int(idx) in set(admitted)),
                            "F_pred_val": float(f_pred_i),
                            "F_cons_chk": float(f_cons_i),
                            "Worst10_val": float(worst10_val_i),
                            "MSE_test": float(mse_i),
                            "MAE_test": float(mae_i),
                            "Worst10_test": float(worst10_i),
                        })

                    admitted_posthoc = [
                        x for x in posthoc_candidates
                        if int(x["in_formal_stage2"]) == 1
                        and int(x["hard_feasible"]) == 1
                    ]
                    scope_posthoc = [
                        x for x in posthoc_candidates
                        if int(x["hard_feasible"]) == 1
                    ]
                    selected_test = float(row["MSE_test"])
                    best_admitted_test = (
                        min(admitted_posthoc, key=lambda x: (x["MSE_test"], x["arch_idx"]))
                        if admitted_posthoc else None
                    )
                    best_scope_test = (
                        min(scope_posthoc, key=lambda x: (x["MSE_test"], x["arch_idx"]))
                        if scope_posthoc else None
                    )
                    best_admitted_val = (
                        min(admitted_posthoc, key=lambda x: (x["F_pred_val"], x["arch_idx"]))
                        if admitted_posthoc else None
                    )
                    best_scope_val = (
                        min(scope_posthoc, key=lambda x: (x["F_pred_val"], x["arch_idx"]))
                        if scope_posthoc else None
                    )

                    selection_regret = (
                        selected_test - float(best_admitted_test["MSE_test"])
                        if best_admitted_test is not None else None
                    )
                    admission_regret = (
                        float(best_admitted_test["MSE_test"])
                        - float(best_scope_test["MSE_test"])
                        if best_admitted_test is not None and best_scope_test is not None
                        else None
                    )
                    end_to_end_regret = (
                        selected_test - float(best_scope_test["MSE_test"])
                        if best_scope_test is not None else None
                    )

                    trace_id = (
                        f"c{int(cid)}_H{int(H)}_K{int(K)}_{str(tier)}"
                    )
                    row.update({
                        "candidate_diagnostic_enabled": 1,
                        "candidate_diagnostic_trace_id": trace_id,
                        "candidate_diagnostic_scope": str(diagnostic_scope),
                        "candidate_diagnostic_count": int(len(posthoc_candidates)),
                        "selection_regret_test": selection_regret,
                        "admission_regret_test": admission_regret,
                        "end_to_end_regret_test": end_to_end_regret,
                        "oracle_best_admitted_arch_idx": (
                            None if best_admitted_test is None
                            else int(best_admitted_test["arch_idx"])
                        ),
                        "oracle_best_scope_arch_idx": (
                            None if best_scope_test is None
                            else int(best_scope_test["arch_idx"])
                        ),
                    })

                    diagnostic_records.append({
                        "trace_id": trace_id,
                        "method": str(method_name),
                        "ablation": str(row.get("ablation", "")),
                        "center_id": int(cid),
                        "center_type": str(ctype),
                        "tier": str(tier),
                        "H": int(H),
                        "K": int(K),
                        "scope": str(diagnostic_scope),
                        "strict_test_isolation": 1,
                        "posthoc_test_used_for_selection": 0,
                        "formal_stage1_arch_indices": [int(x) for x in stage1],
                        "formal_stage2_arch_indices": [int(x) for x in admitted],
                        "global_stage1_arch_indices": [
                            int(x) for x in global_budget_stage1
                        ],
                        "global_stage2_arch_indices": [
                            int(x) for x in global_budget_admitted
                        ],
                        "formal_selected_arch_idx": int(selected["arch_idx"]),
                        "formal_selected_MSE_test": float(selected_test),
                        "score_trace": score_trace,
                        "posthoc_candidates": posthoc_candidates,
                        "regret": {
                            "selection_regret_test": selection_regret,
                            "admission_regret_test": admission_regret,
                            "end_to_end_regret_test": end_to_end_regret,
                            "best_admitted_test": best_admitted_test,
                            "best_scope_test": best_scope_test,
                            "best_admitted_validation": best_admitted_val,
                            "best_scope_validation": best_scope_val,
                        },
                    })
                    diagnostic_tasks_done += 1
                timer.toc("total", t_all)
                row["time_breakdown"] = {k: float(v) for k, v in timer.items()}
                detail.append(row)
                progress.step(); progress.print(extra=f"H={H} K={K} center={cid} feasible={row.get('FeasibleStar',0)}")

    _write_outputs(out_dir, method_name, detail)

    if diagnostic_trace_enable:
        diagnostic_path = os.path.join(
            out_dir,
            f"{method_name}_candidate_diagnostics.json",
        )
        with open(diagnostic_path, "w", encoding="utf-8") as f:
            json.dump(
                diagnostic_records,
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(
            "[CandidateDiagnostic] Saved: "
            f"{diagnostic_path} (tasks={len(diagnostic_records)})"
        )

    if export_downstream:
        downstream_path = os.path.join(
            out_dir,
            f"{method_name}_downstream_case.json",
        )
        with open(downstream_path, "w", encoding="utf-8") as f:
            json.dump(
                downstream_rows,
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(
            "[DownstreamExport] Saved raw predictions: "
            f"{downstream_path} "
            f"(rows={len(downstream_rows)})"
        )

    return {"ok": 1.0, "records": float(len(detail))}
