from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]


class TinyRegressor(nn.Module):
    def __init__(self, hidden: int) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(12, hidden), nn.Tanh(), nn.Linear(hidden, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def _parameters(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def _operations(hidden: int) -> int:
    return 12 * hidden + hidden + hidden + 1


def run_smoke(output_dir: Path) -> dict[str, object]:
    torch.manual_seed(2904)
    rng = np.random.default_rng(2904)
    steps = 180
    t = np.arange(steps, dtype=np.float32)
    series = (0.45 + 0.2 * np.sin(t / 9.0) + 0.03 * rng.standard_normal(steps)).astype(np.float32)
    x = np.stack([np.roll(series, offset) for offset in range(1, 13)], axis=1)[12:]
    y = series[12:, None]
    support_x = torch.from_numpy(x[:12])
    support_y = torch.from_numpy(y[:12])
    validation_x = torch.from_numpy(x[12:58])
    validation_y = torch.from_numpy(y[12:58])

    specs = [("SMOKE_REFERENCE", 8), ("SMOKE_ALTERNATIVE", 12), ("SMOKE_FILTERED", 32)]
    parameter_limit = 313
    operation_limit = 600
    rows = []
    feasible_models: list[tuple[str, nn.Module, float]] = []
    for token, hidden in specs:
        model = TinyRegressor(hidden)
        params = _parameters(model)
        ops = _operations(hidden)
        feasible = params <= parameter_limit and ops <= operation_limit
        if feasible:
            optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
            for _ in range(2):
                optimizer.zero_grad(set_to_none=True)
                loss = (model(support_x) - support_y).square().mean()
                loss.backward()
                optimizer.step()
            with torch.no_grad():
                val = float((model(validation_x) - validation_y).square().mean())
            feasible_models.append((token, model, val))
        else:
            val = float("nan")
        rows.append({"candidate": token, "parameters": params, "estimated_operations": ops, "feasible": feasible, "validation_loss": val})

    reference = next(item for item in feasible_models if item[0] == "SMOKE_REFERENCE")
    alternatives = [item for item in feasible_models if item[0] != "SMOKE_REFERENCE"]
    best = min(alternatives, key=lambda item: item[2]) if alternatives else None
    margin = 0.01
    selected = best if best is not None and best[2] <= reference[2] * (1.0 - margin) else reference
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "smoke_candidates.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    result = {
        "decision": "PASS_CPU_SMOKE_TEST",
        "synthetic_center_steps": steps,
        "support_windows": len(support_x),
        "validation_windows": len(validation_x),
        "parameter_limit": parameter_limit,
        "estimated_operation_limit": operation_limit,
        "reference_candidate": reference[0],
        "best_alternative": best[0] if best else None,
        "minimum_relative_improvement": margin,
        "selected_candidate": selected[0],
        "selected_is_feasible": True,
        "candidate_csv": str(csv_path),
    }
    (output_dir / "smoke_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the CPU-only two-candidate smoke pipeline.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/smoke_test")
    args = parser.parse_args()
    result = run_smoke(args.output_dir.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("PASS_CPU_SMOKE_TEST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
