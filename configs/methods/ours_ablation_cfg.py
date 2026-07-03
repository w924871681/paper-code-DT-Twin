# cfg/methods/ours_ablation_cfg.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from configs.methods.ours_cfg import OursCfg


@dataclass
class OursAblationCfg(OursCfg):
    name: str = "OursPaperAlignedAblation"
    ablation_tag: str = "full"


CFG = OursAblationCfg()
