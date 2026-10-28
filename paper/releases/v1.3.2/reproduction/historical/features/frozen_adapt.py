import torch
from torch import nn,optim
from types import SimpleNamespace
from frozen_seed import seed_all
CFG=SimpleNamespace(fixed_target_lr=.01,fixed_target_steps=50,fixed_target_grad_clip=1.)

def _fixed_target_adapt(
    model: nn.Module,
    Xs: torch.Tensor,
    ys: torch.Tensor,
    *,
    seed: int,
) -> None:
    dev = next(model.parameters()).device
    seed_all(seed, dev)
    model.train()
    opt = optim.SGD(model.parameters(), lr=CFG.fixed_target_lr)
    Xd, yd = Xs.to(dev).contiguous(), ys.to(dev).contiguous()
    for _ in range(CFG.fixed_target_steps):
        opt.zero_grad(set_to_none=True)
        loss = ((model(Xd) - yd) ** 2).mean()
        if not torch.isfinite(loss):
            raise RuntimeError("Non-finite SGD/MSE target loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            model.parameters(), CFG.fixed_target_grad_clip
        )
        opt.step()
