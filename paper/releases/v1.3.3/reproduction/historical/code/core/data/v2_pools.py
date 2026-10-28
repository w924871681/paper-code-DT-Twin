# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Iterable, Optional, Sequence, Tuple

from core.data.center_api import MetaDatasetCache, _centerdata_to_record
from core.data.sim import simulate_centers


def _build_blocks(cfg, blocks: Sequence[Tuple[int, int, int]], *, allowed_types=None) -> MetaDatasetCache:
    n_train = int(cfg.main.split.n_train_centers)
    max_source_pool = max(n_train, max(int(x) for x in tuple(cfg.main.split.scale_centers_list)))
    source_master = simulate_centers(
        main_cfg=cfg.main,
        n_centers=max_source_pool,
        seed_offset=int(cfg.main.sim.source_seed_offset),
        allowed_types=allowed_types,
        start_center_id=0,
    )
    records: Dict[int, object] = {}
    for cd in source_master[:n_train]:
        rec = _centerdata_to_record(cfg, cd, device=str(cfg.main.device))
        records[int(rec.center_id)] = rec
    for start, count, seed_offset in blocks:
        centers = simulate_centers(
            main_cfg=cfg.main,
            n_centers=int(count),
            seed_offset=int(seed_offset),
            allowed_types=allowed_types,
            start_center_id=int(start),
        )
        for cd in centers:
            rec = _centerdata_to_record(cfg, cd, device=str(cfg.main.device))
            records[int(rec.center_id)] = rec
    expected = set(range(n_train))
    for start, count, _seed in blocks:
        expected.update(range(int(start), int(start) + int(count)))
    if set(records) != expected:
        missing = sorted(expected - set(records))
        extra = sorted(set(records) - expected)
        raise RuntimeError(f"V2 pool IDs mismatch: missing={missing[:5]} extra={extra[:5]}")
    return MetaDatasetCache(centers=records)  # type: ignore[arg-type]


def build_v2_development_cache(cfg, *, blocks, allowed_types: Optional[Sequence[str]] = None):
    return _build_blocks(cfg, blocks, allowed_types=allowed_types)


def build_v2_final_cache(cfg, *, pool: str, allowed_types: Optional[Sequence[str]] = None):
    from configs.methods.candidate_space_cfg import CFG
    key = str(pool).strip().upper()
    if key == "A":
        blocks = ((CFG.final_pool_a_start, CFG.final_pool_a_count, CFG.final_pool_a_seed_offset),)
    elif key == "B":
        blocks = ((CFG.final_pool_b_start, CFG.final_pool_b_count, CFG.final_pool_b_seed_offset),)
    elif key == "AB":
        blocks = (
            (CFG.final_pool_a_start, CFG.final_pool_a_count, CFG.final_pool_a_seed_offset),
            (CFG.final_pool_b_start, CFG.final_pool_b_count, CFG.final_pool_b_seed_offset),
        )
    else:
        raise ValueError("pool must be A, B or AB")
    return _build_blocks(cfg, blocks, allowed_types=allowed_types)
