# Method mapping

1. `source_prior_bank/`: architecture-indexed source priors for A1, A6, A13, A55, A56, and A57.
2. `main_evaluation/`: hard feasibility, fixed 50-step SGD/MSE adaptation, and PT-A57 anchor-safe selection.
3. `anchor_safe_selector/`: development calibration of the frozen 10% validation margin.
4. `experiments/`: locked main, robustness, and supplementary protocols.

Prediction is an evaluation task; the output of the method is a target-specific digital-twin model instance.
