# -*- coding: utf-8 -*-
"""Concurrency stress test for the MSA-DTI target-side workload.

Review-round diagnostic, not the frozen 5.676 s protocol. It loads frozen
source initializations at H=4, runs 50 SGD/MSE updates on one synthetic case
per job, and measures per-case wall-time scaling with 1/2/4/8 concurrent jobs.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from configs.main_cfg import CFG
from core.space import build_model, enumerate_A_base


H = 4
INPUT_DIM = 25
L = 96
STEPS = 50
LR = 0.01
SUPPORT_WINDOWS = 20
VALIDATION_WINDOWS = 80
MARGIN = 0.10

STRONG_BANK_DIR = ROOT / "outputs" / "c31_compact_d2904_t2904" / "strong_bank"
PT_FT_DIR = ROOT / "outputs" / "final_e2e_c23_external_d2904_t2904" / "source_assets"

CANDIDATE_WEIGHTS = [
    (1, STRONG_BANK_DIR / "strong_h4_a1.pt", False),
    (6, STRONG_BANK_DIR / "strong_h4_a6.pt", False),
    (13, STRONG_BANK_DIR / "strong_h4_a13.pt", False),
    (55, STRONG_BANK_DIR / "strong_h4_a55.pt", False),
    (56, STRONG_BANK_DIR / "strong_h4_a56.pt", False),
    (57, STRONG_BANK_DIR / "strong_h4_a57.pt", False),
    (57, PT_FT_DIR / "pt_ft_h4_a57.pt", True),
]


def _one_case(seed: int) -> dict:
    dev = torch.device("cuda:0")
    torch.manual_seed(int(seed))
    all_specs = enumerate_A_base(CFG.arch)
    Xs = torch.randn(SUPPORT_WINDOWS, L, INPUT_DIM, device=dev)
    ys = torch.randn(SUPPORT_WINDOWS, H, device=dev)
    Xv = torch.randn(VALIDATION_WINDOWS, L, INPUT_DIM, device=dev)
    yv = torch.randn(VALIDATION_WINDOWS, H, device=dev)

    t0 = time.perf_counter()
    losses = []
    for idx, weight_path, _is_ref in CANDIDATE_WEIGHTS:
        model = build_model(all_specs[idx], INPUT_DIM, H, L=L, device="cuda:0")
        model.load_state_dict(torch.load(str(weight_path), map_location="cuda:0"), strict=True)
        opt = torch.optim.SGD(model.parameters(), lr=LR)
        model.train()
        for _ in range(STEPS):
            opt.zero_grad(set_to_none=True)
            loss = ((model(Xs) - ys) ** 2).mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        model.eval()
        with torch.no_grad():
            losses.append(float(((model(Xv) - yv) ** 2).mean().item()))
        del model, opt
    torch.cuda.synchronize()
    seconds = time.perf_counter() - t0

    ref = losses[-1]
    best_alt = min(losses[:-1])
    selected_alt = best_alt <= (1.0 - MARGIN) * ref
    peak_mib = torch.cuda.max_memory_allocated(dev) / (1024.0**2)
    torch.cuda.reset_peak_memory_stats(dev)
    return {
        "seconds": float(seconds),
        "selected_alternative": bool(selected_alt),
        "peak_gpu_mib": float(peak_mib),
    }


def _worker(seed: int, jobs: int, out: "mp.Queue") -> None:
    _one_case(seed)
    rows = [_one_case(seed + 1000 + j) for j in range(jobs)]
    out.put(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--jobs-per-worker", type=int, default=4)
    ap.add_argument("--base-seed", type=int, default=2904)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    procs = [
        ctx.Process(target=_worker, args=(args.base_seed + 10000 * i, args.jobs_per_worker, queue))
        for i in range(args.workers)
    ]
    t0 = time.perf_counter()
    for p in procs:
        p.start()
    rows = []
    for _ in procs:
        rows.extend(queue.get())
    for p in procs:
        p.join()
    makespan = time.perf_counter() - t0

    seconds = [r["seconds"] for r in rows]
    payload = {
        "workers": args.workers,
        "jobs_per_worker": args.jobs_per_worker,
        "total_jobs": len(rows),
        "makespan_seconds": makespan,
        "per_job_mean_seconds": float(np.mean(seconds)),
        "per_job_sd_seconds": float(np.std(seconds)),
        "per_job_median_seconds": float(np.median(seconds)),
        "throughput_jobs_per_second": float(len(rows) / makespan),
        "peak_gpu_mib_max": float(max(r["peak_gpu_mib"] for r in rows)),
        "selected_alternative_count": int(sum(r["selected_alternative"] for r in rows)),
        "note": "Frozen source initializations at H=4; review-round scaling probe.",
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
