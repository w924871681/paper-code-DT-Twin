# -*- coding: utf-8 -*-
"""Center-cluster bootstrap width analysis for the harmful-selection rate.

Review-round diagnostic. It reuses the frozen 80 held-out cases and resamples
centers with replacement to estimate how many centers would be needed to bring
the upper 95% bound of the harmful-selection rate to 5%.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "results" / "figure_data" / "fig6_paired_instantiation_data.csv"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=2904)
    args = ap.parse_args()

    df = pd.read_csv(DATA)
    harmful = (df.selection_category == "harmful alternative").astype(int)
    centers = np.sort(df.center_id.unique())
    by_center = {int(c): harmful[df.center_id == c].to_numpy() for c in centers}
    rng = np.random.default_rng(args.seed)

    def upper_for(m: int) -> float:
        vals = np.empty(args.reps)
        for r in range(args.reps):
            ids = rng.integers(0, len(centers), size=m)
            sample = np.concatenate([by_center[int(centers[i])] for i in ids])
            vals[r] = sample.mean()
        return float(np.quantile(vals, 0.975))

    observed = float(harmful.mean())
    upper_20 = upper_for(20)
    print(f"observed harmful rate: {observed:.4f}")
    print(f"upper 95% bound at 20 centers: {upper_20:.4f}")
    for m in (20, 40, 80, 150, 200, 250, 300):
        print(f"upper 95% bound at {m} centers: {upper_for(m):.4f}")

    first = None
    for m in range(20, 401, 10):
        if upper_for(m) <= 0.05:
            first = m
            break
    print(f"first center count with upper bound <= 5%: {first}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
