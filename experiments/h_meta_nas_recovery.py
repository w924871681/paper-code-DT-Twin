# -*- coding: utf-8 -*-
"""Recover and audit the H-Meta-NAS baseline under the released DT protocol.

The source stage is first-order MAML (support inner update, validation outer
gradient) over source centers.  The target stage follows the H-Meta-NAS
population-and-mutation search idea, with hard feasibility applied before any
candidate is evaluated.  The script never reads a held-out target test label
until the selected architecture and its adapted parameters are fixed.
"""
from __future__ import annotations

import argparse
import copy
import csv
import gc
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.methods.h_meta_nas_cfg import CFG, config_dict
from core.space import build_model, profile_arch
from core.methods.ours.stage2_runtime import (
    candidate_backend_context,
    candidate_device,
    synchronize_if_cuda,
)
from shared.data_access import get_support_validation_check, get_test_only
from shared.evaluation.common import (
    atomic_json,
    build_runtime,
    eval_metrics,
    feasible_indices,
    file_sha256,
    seed_all,
)


def _sha256(path: Path) -> str:
    return file_sha256(str(path))


def _save_torch(obj: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(obj, tmp)
    os.replace(tmp, path)


def _load_torch(path: Path) -> object:
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


def _state_key(H: int, idx: int) -> str:
    return f"h{int(H)}_a{int(idx)}"


def _mse(model: torch.nn.Module, X: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    return ((model(X) - y) ** 2).mean()


def _initial_state(spec: Any, *, H: int, input_dim: int, L: int, seed: int) -> Dict[str, torch.Tensor]:
    seed_all(seed, torch.device("cpu"))
    model = build_model(spec, input_dim=input_dim, H=H, L=L, device="cpu")
    return {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}


def _build_meta_bank(
    *, root: Path, cfg: Any, cache: Any, A: Sequence[Any], input_dim: int,
    L: int, device: torch.device, artifact: Path, smoke: bool,
) -> Mapping[str, Any]:
    target_iterations = 4 if smoke else CFG.source_outer_iterations
    archs_per_task = min(3 if smoke else CFG.source_architectures_per_task, len(A))
    if artifact.exists():
        saved = _load_torch(artifact)
        if saved.get("protocol") != config_dict():
            raise RuntimeError("H-Meta-NAS source artifact protocol mismatch")
        if int(saved.get("target_iterations", -1)) != int(target_iterations):
            raise RuntimeError("H-Meta-NAS smoke/formal source artifacts cannot be shared")
    else:
        states: Dict[str, Dict[str, torch.Tensor]] = {}
        for H in CFG.H_list:
            for idx, spec in enumerate(A):
                states[_state_key(H, idx)] = _initial_state(
                    spec, H=H, input_dim=input_dim, L=L,
                    seed=CFG.train_seed + 100000 * H + idx,
                )
        saved = {
            "study": "h_meta_nas_source_first_order_maml",
            "protocol": config_dict(),
            "target_iterations": target_iterations,
            "completed_iterations": 0,
            "states": states,
            "source_center_ids": list(range(CFG.source_centers)),
            "test_used": False,
            "target_pool_used": False,
        }
        _save_torch(saved, artifact)

    states = saved["states"]
    generator = random.Random(CFG.train_seed + 451)
    # Reconstruct the deterministic episode sequence, then skip completed ones.
    episodes = []
    for _ in range(target_iterations):
        episodes.append((
            generator.randrange(CFG.source_centers),
            generator.choice(CFG.H_list),
            generator.choice(CFG.K_list),
            generator.sample(range(len(A)), archs_per_task),
        ))
    begin = int(saved.get("completed_iterations", 0))
    for outer, (cid, H, K, indices) in enumerate(episodes[begin:], begin):
        Xs, ys, Xv, yv, _Xc, _yc, _tier, _ctype = get_support_validation_check(
            cfg, cache, cid, H, K
        )
        for idx in indices:
            spec = A[idx]
            actual = candidate_device(spec, device, "gru-native")
            with candidate_backend_context(spec, actual, "gru-native"):
                meta = build_model(spec, input_dim=input_dim, H=H, L=L, device=str(actual))
                meta.load_state_dict(states[_state_key(H, idx)], strict=True)
                inner = copy.deepcopy(meta)
                inner.train()
                optimizer = torch.optim.SGD(inner.parameters(), lr=CFG.source_inner_lr)
                xs, ys_dev = Xs.to(actual), ys.to(actual)
                xv, yv_dev = Xv.to(actual), yv.to(actual)
                for _ in range(CFG.source_inner_steps):
                    optimizer.zero_grad(set_to_none=True)
                    loss = _mse(inner, xs, ys_dev)
                    if not torch.isfinite(loss):
                        raise RuntimeError("non-finite H-Meta-NAS source inner loss")
                    loss.backward(); optimizer.step()
                query = _mse(inner, xv, yv_dev)
                gradients = torch.autograd.grad(query, tuple(inner.parameters()))
                updated = meta.state_dict()
                for (name, _param), gradient in zip(inner.named_parameters(), gradients):
                    updated[name] = (updated[name] - CFG.source_meta_lr * gradient.detach()).cpu()
                states[_state_key(H, idx)] = {
                    name: value.detach().cpu().clone() for name, value in updated.items()
                }
                del meta, inner, optimizer
                synchronize_if_cuda(actual)
        saved["completed_iterations"] = outer + 1
        _save_torch(saved, artifact)
        print(f"[H-Meta-NAS] source episode {outer + 1}/{target_iterations}", flush=True)
    saved["complete"] = True
    _save_torch(saved, artifact)
    return saved


def _mutants(
    parent: int, feasible: Sequence[int], visited: set[int], A: Sequence[Any], rng: random.Random,
) -> List[int]:
    p = A[parent]
    def distance(idx: int) -> tuple[int, int]:
        spec = A[idx]
        family_penalty = 0 if spec.family == p.family else 10
        keys = set(spec.hparams) | set(p.hparams)
        changed = sum(spec.hparams.get(k) != p.hparams.get(k) for k in keys)
        return family_penalty + changed, idx
    candidates = [idx for idx in feasible if idx not in visited and idx != parent]
    candidates.sort(key=distance)
    if not candidates:
        return []
    best = [idx for idx in candidates if distance(idx)[0] == distance(candidates[0])[0]]
    rng.shuffle(best)
    return best + [idx for idx in candidates if idx not in best]


def _adapt_and_validate(
    *, spec: Any, state: Mapping[str, torch.Tensor], Xs: torch.Tensor, ys: torch.Tensor,
    Xv: torch.Tensor, yv: torch.Tensor, H: int, L: int, input_dim: int,
    device: torch.device, seed: int,
) -> tuple[torch.nn.Module, Dict[str, float]]:
    actual = candidate_device(spec, device, "gru-native")
    with candidate_backend_context(spec, actual, "gru-native"):
        seed_all(seed, actual)
        model = build_model(spec, input_dim=input_dim, H=H, L=L, device=str(actual))
        model.load_state_dict(state, strict=True)
        optimizer = torch.optim.SGD(model.parameters(), lr=CFG.target_lr)
        xs, ys_dev = Xs.to(actual), ys.to(actual)
        for _ in range(CFG.target_steps):
            optimizer.zero_grad(set_to_none=True)
            loss = _mse(model, xs, ys_dev)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite H-Meta-NAS target loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), CFG.target_grad_clip)
            optimizer.step()
        validation = eval_metrics(model, Xv, yv)
        synchronize_if_cuda(actual)
        return model, validation


def _mean(values: Iterable[float]) -> float:
    vals = list(values)
    return float(sum(vals) / len(vals)) if vals else float("nan")


def _run(*, root: Path, output: Path, device: str, smoke: bool) -> None:
    output.mkdir(parents=True, exist_ok=True)
    cfg, cache, A, requested, _safe = build_runtime(device, "gru-native", (CFG.locked_pool,))
    X0, *_ = get_support_validation_check(cfg, cache, 0, CFG.H_list[0], CFG.K_list[0])
    input_dim, L = int(X0.shape[-1]), int(cfg.main.task.L)
    bank_path = output / ("source_meta_bank_smoke.pt" if smoke else "source_meta_bank.pt")
    bank = _build_meta_bank(root=root, cfg=cfg, cache=cache, A=A, input_dim=input_dim, L=L, device=requested, artifact=bank_path, smoke=smoke)
    result_path = output / ("h_meta_nas_smoke.json" if smoke else "h_meta_nas_formal.json")
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {
        "study": "h_meta_nas_recovered_comparison", "method": "h_meta_nas",
        "protocol": config_dict(), "run_mode": "smoke" if smoke else "formal",
        "source_bank_sha256": _sha256(bank_path), "records": {},
        "selection_uses_check": False, "selection_uses_test": False,
        "test_opened_only_after_final_model_fixed": True,
    }
    jobs = [
        (cid, H, K) for cid in range(CFG.locked_pool[0], CFG.locked_pool[0] + CFG.locked_pool[1])
        for H in CFG.H_list for K in CFG.K_list
    ]
    if smoke: jobs = jobs[:2]
    for cid, H, K in jobs:
        Xs, ys, Xv, yv, Xc, yc, tier, ctype = get_support_validation_check(cfg, cache, cid, H, K)
        key = f"c{cid}_h{H}_k{K}_b{tier}"
        if result["records"].get(key, {}).get("complete"): continue
        seed = CFG.train_seed + 1009 * cid + 37 * H + 53 * K
        rng = random.Random(seed)
        feasible = feasible_indices(cfg, A, tier, L, input_dim, H)
        if not feasible: raise RuntimeError("no feasible H-Meta-NAS candidate")
        visited: set[int] = set(); population = rng.sample(feasible, min(CFG.population_size, len(feasible)))
        evaluated: List[Dict[str, Any]] = []; best_state = None; best = None
        started = time.perf_counter()
        for generation in range(CFG.generations):
            generation_rows = []
            for idx in population:
                if idx in visited: continue
                model, val = _adapt_and_validate(spec=A[idx], state=bank["states"][_state_key(H, idx)], Xs=Xs, ys=ys, Xv=Xv, yv=yv, H=H, L=L, input_dim=input_dim, device=requested, seed=seed + idx + 10000 * generation)
                params, flops = profile_arch(A[idx], L=L, input_dim=input_dim, H=H)
                row = {"generation": generation, "arch_idx": idx, "arch_key": A[idx].arch_key, "family": A[idx].family, "params": float(params), "flops": float(flops), "validation": val}
                evaluated.append(row); generation_rows.append(row); visited.add(idx)
                score = (float(val["weighted_mse"]), float(params), float(flops), idx)
                if best is None or score < best[0]:
                    best = (score, row)
                    # Keep only a CPU copy of the incumbent; retaining a CUDA
                    # module across candidates causes fragmentation on 6 GB GPUs.
                    best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                del model
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            if generation + 1 < CFG.generations:
                parents = sorted(generation_rows, key=lambda r: (r["validation"]["weighted_mse"], r["arch_idx"]))[:CFG.parent_count]
                population = []
                for parent in parents:
                    for candidate in _mutants(parent["arch_idx"], feasible, visited | set(population), A, rng):
                        if candidate not in population:
                            population.append(candidate); break
                remaining = [idx for idx in feasible if idx not in visited and idx not in population]
                rng.shuffle(remaining); population += remaining[:max(0, CFG.population_size - len(population))]
        if best is None or best_state is None: raise RuntimeError("H-Meta-NAS did not select a candidate")
        # Reconstruct only the selected model for check/test evaluation.
        best_spec = A[best[1]["arch_idx"]]
        best_actual = candidate_device(best_spec, requested, "gru-native")
        best_model = build_model(best_spec, input_dim=input_dim, H=H, L=L, device=str(best_actual))
        best_model.load_state_dict(best_state, strict=True)
        check = eval_metrics(best_model, Xc, yc)
        Xt, yt = get_test_only(cfg, cache, cid, H, K)
        test = eval_metrics(best_model, Xt, yt)
        result["records"][key] = {
            "complete": True, "method": "h_meta_nas", "case_key": key, "center_id": cid,
            "center_type": ctype, "budget_tier": tier, "H": H, "K": K,
            "hard_feasible": True, "feasible": True, "candidate_count": len(evaluated),
            "adapted_candidate_count": len(evaluated), "arch_idx": best[1]["arch_idx"],
            "arch_key": best[1]["arch_key"], "family": best[1]["family"],
            "params": best[1]["params"], "flops": best[1]["flops"],
            "validation": best[1]["validation"], "selector": {"selector": "h_meta_nas_population_mutation_valbest", "population_size": CFG.population_size, "generations": CFG.generations, "evaluated_candidates": evaluated, "selection_uses_check": False, "selection_uses_test": False},
            "check": check, "test": test, "online_seconds": float(time.perf_counter() - started),
            "target_seed": seed, "selection_uses_check": False, "selection_uses_test": False,
            "test_opened_after_selection": True,
        }
        del best_model, best_state
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        atomic_json(result, str(result_path))
        print(f"[H-Meta-NAS] completed {key} ({len(result['records'])}/{len(jobs)})", flush=True)
    result["complete"] = len(result["records"]) == len(jobs)
    result["decision"] = "H_META_NAS_COMPLETE" if result["complete"] else "H_META_NAS_INCOMPLETE"
    atomic_json(result, str(result_path))
    if result["complete"] and not smoke:
        values = result["records"].values()
        summary = {"Method": "H-Meta-NAS", "MAE": _mean(r["test"]["mae"] for r in values), "WMSE": _mean(r["test"]["weighted_mse"] for r in values), "Worst10": _mean(r["test"]["worst10"] for r in values), "FeasibleRate": _mean(float(r["feasible"]) for r in values), "OnlineSeconds": _mean(r["online_seconds"] for r in values), "AdaptedCandidates": _mean(r["adapted_candidate_count"] for r in values)}
        with (output / "overall_comparison_h_meta_nas.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary)); writer.writeheader(); writer.writerow(summary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--output-root", default=CFG.output_root)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if not args.smoke and (not str(args.device).lower().startswith("cuda") or not torch.cuda.is_available()):
        parser.error("formal H-Meta-NAS evaluation requires an available CUDA device; use --smoke for a CPU protocol check")
    _run(root=ROOT, output=Path(args.output_root), device=args.device, smoke=args.smoke)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
