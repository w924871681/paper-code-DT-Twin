# core/methods/ours/source_prior.py
# -*- coding: utf-8 -*-
"""Source-trained transferable prior used by the formal Ours pipeline.

The selected formal prior is the compute-matched pooled source prior (C1):

1. pooled source pretraining from a deterministic random initialization; and
2. a fixed number of pooled supervised refinement updates.

Only source-center support data are read. Target-center data, validation data,
check data, and test data are never used here. The artifact is checkpointed
after every (horizon, architecture) entry, so a native CUDA interruption can be
resumed without retraining completed entries.
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import random
import time
from dataclasses import asdict
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence, Tuple

import torch
import torch.nn.functional as F
import torch.optim as optim

from core.data.center_api import get_center_split_from_cache
from core.methods.ours.weight_bank import (
    BankMeta,
    _build_model_auto,
    make_bank_key_legacy,
    make_bank_key_shared,
)


PRIOR_TYPE = "source_pooled_c1"
PROTOCOL_VERSION = "source_pooled_c1_v1"


def _set_seed(seed: int) -> None:
    random.seed(int(seed))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))


def _release_cuda() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _space_fingerprint(A: Sequence[Any]) -> str:
    text = "|".join(str(x.arch_key) for x in A)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _clone_state(state: Mapping[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
    return {str(k): v.detach().cpu().clone() for k, v in state.items()}


def _store_shared_state(
    bank: MutableMapping[str, Dict[str, torch.Tensor]],
    *,
    H: int,
    arch_key: str,
    input_dim: int,
    L: int,
    state: Mapping[str, torch.Tensor],
) -> None:
    cpu_state = _clone_state(state)
    shared = make_bank_key_shared(
        H=int(H), arch_key=str(arch_key), input_dim=int(input_dim), L=int(L)
    )
    legacy = make_bank_key_legacy(int(H), str(arch_key))
    bank[shared] = _clone_state(cpu_state)
    bank[legacy] = _clone_state(cpu_state)


def _pooled_source_support(
    cfg,
    cache,
    source_ids: Sequence[int],
    *,
    H: int,
    K: int,
) -> Tuple[torch.Tensor, torch.Tensor]:
    xs: List[torch.Tensor] = []
    ys: List[torch.Tensor] = []
    for cid in source_ids:
        Xs, y, *_ = get_center_split_from_cache(
            cfg, cache, int(cid), int(H), int(K)
        )
        xs.append(Xs.detach().cpu())
        ys.append(y.detach().cpu())
    if not xs:
        raise RuntimeError("No source-center support tensors were collected")
    return torch.cat(xs, dim=0).contiguous(), torch.cat(ys, dim=0).contiguous()


def _loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    *,
    name: str,
    huber_delta: float,
) -> torch.Tensor:
    mode = str(name).strip().lower()
    if mode == "mse":
        return ((pred - target) ** 2).mean()
    if mode == "huber":
        return F.huber_loss(
            pred, target, delta=float(huber_delta), reduction="mean"
        )
    raise ValueError(f"Unsupported source-prior loss: {name!r}")


def _save_artifact(
    path: str,
    *,
    meta: BankMeta,
    bank: Mapping[str, Mapping[str, torch.Tensor]],
    training_info: Mapping[str, Any],
) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.tmp"
    torch.save(
        {
            "meta": asdict(meta),
            "bank": dict(bank),
            "training_info": dict(training_info),
        },
        tmp,
    )
    os.replace(tmp, path)


def _load_artifact(
    path: str,
) -> Tuple[BankMeta, Dict[str, Dict[str, torch.Tensor]], Dict[str, Any]]:
    obj = torch.load(path, map_location="cpu")
    meta = BankMeta(**dict(obj["meta"]))
    bank = {
        str(k): _clone_state(v)
        for k, v in dict(obj["bank"]).items()
    }
    info = dict(obj.get("training_info", {}))
    return meta, bank, info


def _protocol_signature(
    *,
    cfg,
    mcfg,
    A: Sequence[Any],
    input_dim: int,
    H_list: Sequence[int],
    L: int,
) -> Dict[str, Any]:
    return {
        "prior_type": PRIOR_TYPE,
        "protocol_version": PROTOCOL_VERSION,
        "space_fingerprint": _space_fingerprint(A),
        "input_dim": int(input_dim),
        "H_list": [int(x) for x in H_list],
        "L": int(L),
        "data_seed": int(cfg.main.sim.seed),
        "source_prior_seed": int(mcfg.source_prior_seed),
        "n_source_centers": int(cfg.main.split.n_train_centers),
        "source_pretrain_K": int(mcfg.source_pretrain_K),
        "source_pretrain_epochs": int(mcfg.source_pretrain_epochs),
        "source_pretrain_lr": float(mcfg.source_pretrain_lr),
        "source_pretrain_batch_size": int(mcfg.source_pretrain_batch_size),
        "source_pretrain_loss": str(mcfg.source_pretrain_loss),
        "source_refine_updates": int(mcfg.source_refine_updates),
        "source_refine_lr": float(mcfg.source_refine_lr),
        "source_refine_batch_schedule": [
            int(x) for x in mcfg.source_refine_batch_schedule
        ],
        "source_refine_loss": str(mcfg.source_refine_loss),
        "source_weight_decay": float(mcfg.source_weight_decay),
        "huber_delta": float(mcfg.huber_delta),
        "max_grad_norm": float(mcfg.max_grad_norm),
        "num_architectures": int(len(A)),
    }


def _same_protocol(info: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    for key, value in expected.items():
        if info.get(key) != value:
            return False
    return True


def _completed_token(H: int, arch_idx: int) -> str:
    return f"H{int(H)}::A{int(arch_idx)}"


def build_or_load_source_pooled_c1(
    *,
    cfg,
    mcfg,
    cache,
    A: Sequence[Any],
    device: torch.device,
    bank_path: str,
    smoke: bool = False,
) -> Tuple[BankMeta, Dict[str, Dict[str, torch.Tensor]], Dict[str, Any]]:
    """Build or load the formal C1 source prior.

    The procedure matches the selected diagnostic C1 protocol:
    pooled MSE pretraining followed by 180 pooled Huber updates. Both phases
    use only source-center support windows. Completed architecture entries are
    checkpointed and reused on resume.
    """
    L = int(cfg.main.task.L)
    H_list = (
        [int(cfg.main.task.H_list[0])]
        if smoke
        else [int(x) for x in cfg.main.task.H_list]
    )
    K0 = int(mcfg.source_pretrain_K)
    Xs0, *_ = get_center_split_from_cache(cfg, cache, 0, H_list[0], K0)
    input_dim = int(Xs0.shape[-1])
    meta = BankMeta(
        space_fingerprint=_space_fingerprint(A),
        input_dim=input_dim,
        H_list=H_list,
    )

    if smoke:
        return meta, {}, {
            "prior_type": PRIOR_TYPE,
            "protocol_version": PROTOCOL_VERSION,
            "status": "smoke_empty_bank",
        }

    expected = _protocol_signature(
        cfg=cfg,
        mcfg=mcfg,
        A=A,
        input_dim=input_dim,
        H_list=H_list,
        L=L,
    )
    force = bool(getattr(mcfg, "source_prior_force_retrain", False))
    resume = bool(getattr(mcfg, "source_prior_resume", True))

    bank: Dict[str, Dict[str, torch.Tensor]] = {}
    info: Dict[str, Any] = {}
    if os.path.isfile(bank_path) and not force:
        loaded_meta, loaded_bank, loaded_info = _load_artifact(bank_path)
        valid_meta = (
            str(loaded_meta.space_fingerprint) == str(meta.space_fingerprint)
            and int(loaded_meta.input_dim) == int(meta.input_dim)
            and [int(x) for x in loaded_meta.H_list] == [int(x) for x in meta.H_list]
        )
        valid_protocol = _same_protocol(loaded_info, expected)
        if valid_meta and valid_protocol:
            if str(loaded_info.get("status")) == "complete":
                return loaded_meta, loaded_bank, loaded_info
            if resume:
                bank, info = loaded_bank, loaded_info
                print(
                    f"[SourcePrior:C1] resume partial artifact: {bank_path}",
                    flush=True,
                )
            else:
                raise RuntimeError(
                    "A matching but incomplete source-prior artifact exists and "
                    "source_prior_resume=False"
                )
        else:
            raise RuntimeError(
                "Existing source-prior artifact does not match the frozen C1 "
                "protocol. Use a new OURS_ARTIFACT_DIR or set "
                "source_prior_force_retrain=True."
            )

    if not info:
        info = {
            **expected,
            "status": "building",
            "source_center_ids": list(
                range(int(cfg.main.split.n_train_centers))
            ),
            "completed_entries": [],
            "entry_logs": [],
            "started_at_unix_s": float(time.time()),
        }

    source_ids = list(range(int(cfg.main.split.n_train_centers)))
    completed = set(str(x) for x in info.get("completed_entries", []))
    entry_logs = list(info.get("entry_logs", []))
    total_entries = int(len(A) * len(H_list))
    initial_completed = int(len(completed))
    run_started = float(time.time())
    print(
        f"[SourcePrior:C1] total_entries={total_entries} "
        f"already_completed={initial_completed} remaining={total_entries-initial_completed}",
        flush=True,
    )

    for H in H_list:
        Xpool, ypool = _pooled_source_support(
            cfg, cache, source_ids, H=int(H), K=K0
        )
        n_pool = int(Xpool.shape[0])
        for arch_idx, spec in enumerate(A):
            token = _completed_token(H, arch_idx)
            if token in completed:
                continue

            model_seed = (
                int(mcfg.source_prior_seed)
                + 10000 * int(H)
                + int(arch_idx)
            )
            _set_seed(model_seed)
            model = _build_model_auto(
                spec,
                input_dim=input_dim,
                H=int(H),
                L=L,
                device=device,
            )

            # Phase 1: pooled source pretraining (B0).
            model.train()
            pre_opt = optim.Adam(
                model.parameters(),
                lr=float(mcfg.source_pretrain_lr),
                weight_decay=float(mcfg.source_weight_decay),
            )
            pre_gen = torch.Generator(device="cpu").manual_seed(
                model_seed + 100000
            )
            pre_first = None
            pre_last = None
            pre_updates = 0
            pre_visits = 0
            bs_cfg = int(mcfg.source_pretrain_batch_size)
            for _epoch in range(int(mcfg.source_pretrain_epochs)):
                perm = torch.randperm(n_pool, generator=pre_gen)
                bs = n_pool if bs_cfg <= 0 else max(1, min(bs_cfg, n_pool))
                for start in range(0, n_pool, bs):
                    idx = perm[start : start + bs]
                    Xb = Xpool.index_select(0, idx).to(device)
                    yb = ypool.index_select(0, idx).to(device)
                    pre_opt.zero_grad(set_to_none=True)
                    value = _loss(
                        model(Xb),
                        yb,
                        name=str(mcfg.source_pretrain_loss),
                        huber_delta=float(mcfg.huber_delta),
                    )
                    value.backward()
                    if float(mcfg.max_grad_norm) > 0:
                        torch.nn.utils.clip_grad_norm_(
                            model.parameters(), float(mcfg.max_grad_norm)
                        )
                    pre_opt.step()
                    loss_value = float(value.detach().item())
                    pre_first = loss_value if pre_first is None else pre_first
                    pre_last = loss_value
                    pre_updates += 1
                    pre_visits += int(idx.numel())
                    del Xb, yb, value

            # Phase 2: compute-matched pooled refinement (C1).
            refine_opt = optim.Adam(
                model.parameters(),
                lr=float(mcfg.source_refine_lr),
                weight_decay=float(mcfg.source_weight_decay),
            )
            refine_gen = torch.Generator(device="cpu").manual_seed(
                model_seed + 200000
            )
            schedule = [int(x) for x in mcfg.source_refine_batch_schedule]
            if not schedule:
                raise ValueError("source_refine_batch_schedule must be non-empty")
            refine_first = None
            refine_last = None
            refine_visits = 0
            for step in range(int(mcfg.source_refine_updates)):
                bs = max(1, min(schedule[step % len(schedule)], n_pool))
                idx = torch.randint(
                    0, n_pool, (bs,), generator=refine_gen, device="cpu"
                )
                Xb = Xpool.index_select(0, idx).to(device)
                yb = ypool.index_select(0, idx).to(device)
                refine_opt.zero_grad(set_to_none=True)
                value = _loss(
                    model(Xb),
                    yb,
                    name=str(mcfg.source_refine_loss),
                    huber_delta=float(mcfg.huber_delta),
                )
                value.backward()
                if float(mcfg.max_grad_norm) > 0:
                    torch.nn.utils.clip_grad_norm_(
                        model.parameters(), float(mcfg.max_grad_norm)
                    )
                refine_opt.step()
                loss_value = float(value.detach().item())
                refine_first = (
                    loss_value if refine_first is None else refine_first
                )
                refine_last = loss_value
                refine_visits += int(bs)
                del Xb, yb, value

            _store_shared_state(
                bank,
                H=int(H),
                arch_key=str(spec.arch_key),
                input_dim=input_dim,
                L=L,
                state=model.state_dict(),
            )
            row = {
                "token": token,
                "H": int(H),
                "arch_idx": int(arch_idx),
                "arch_key": str(spec.arch_key),
                "family": str(spec.family),
                "n_pool": n_pool,
                "pretrain_optimizer_updates": int(pre_updates),
                "pretrain_sample_visits": int(pre_visits),
                "pretrain_loss_first": pre_first,
                "pretrain_loss_last": pre_last,
                "refine_optimizer_updates": int(mcfg.source_refine_updates),
                "refine_sample_visits": int(refine_visits),
                "refine_loss_first": refine_first,
                "refine_loss_last": refine_last,
            }
            entry_logs.append(row)
            completed.add(token)
            info["completed_entries"] = sorted(completed)
            info["entry_logs"] = entry_logs
            info["status"] = "building"
            info["last_completed"] = token
            _save_artifact(
                bank_path,
                meta=meta,
                bank=bank,
                training_info=info,
            )
            done_total = int(len(completed))
            done_run = max(0, done_total - initial_completed)
            elapsed = max(0.0, float(time.time()) - run_started)
            avg = elapsed / max(1, done_run)
            remaining = max(0, total_entries - done_total)
            eta_s = avg * remaining if done_run > 0 else float("nan")
            finish = (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + eta_s))
                if done_run > 0 else "unknown"
            )
            print(
                f"[SourcePrior:C1] {done_total}/{total_entries} "
                f"({100.0*done_total/max(1,total_entries):.2f}%) "
                f"{token} {spec.arch_key} "
                f"pre={pre_first:.6f}->{pre_last:.6f} "
                f"refine={refine_first:.6f}->{refine_last:.6f} "
                f"elapsed={elapsed/3600.0:.2f}h avg={avg:.1f}s/entry "
                f"eta={eta_s/3600.0:.2f}h finish={finish}",
                flush=True,
            )
            del model, pre_opt, refine_opt
            _release_cuda()
        del Xpool, ypool
        _release_cuda()

    expected_entries = int(len(A) * len(H_list))
    if len(completed) != expected_entries:
        raise RuntimeError(
            f"Source-prior build incomplete: {len(completed)}/{expected_entries}"
        )
    info["status"] = "complete"
    info["completed_at_unix_s"] = float(time.time())
    info["expected_entries"] = expected_entries
    info["bank_entries"] = int(len(bank))
    _save_artifact(
        bank_path,
        meta=meta,
        bank=bank,
        training_info=info,
    )
    print(
        f"[SourcePrior:C1] complete: {bank_path} "
        f"entries={expected_entries} bank_keys={len(bank)}",
        flush=True,
    )
    return meta, bank, info
