# MSA-DTI paper and reproducibility materials — v1.3.4

This version retains the original Bitbrains experiment, figures and models and adds 30-VM Materna and 29-VM later-Bitbrains workload evaluations. `main.tex`/`main.pdf` and `supplementary.tex`/`supplementary.pdf` are the corresponding manuscript and supplement. `figures/` and `tables/` contain their compilation inputs; `plotting/` contains the experimental figure scripts. The unchanged original per-case records, policies and checkpoint provenance are in `data/`, `selection/` and `reproduction/`.

`external_validation/` provides the new experiment's 236 case records, validation selection inputs, three-budget results, protocol, source code snapshots and a verifier. It also provides an inference-replay script that uses the separately published adapted-state ZIP and the two publicly obtained trace archives. See its README for commands, data attribution, the GPU retry chronology and exact verification boundary.

Run `python verify_results.py`, `python selection/replay_selection.py` and `python external_validation/verify_external.py` for saved-record checks. On Windows, `build.ps1` compiles both documents. Saved-score and adapted-state inference replays are not source or target retraining. The historical source and baseline training code retains prior path assumptions; a clean end-to-end retraining has not been verified.

The Materna and Bitbrains traces are supplied by their respective data providers via the Grid Workloads Archive. Respect the archive's attribution conditions. The original experiments, new cross-source evaluation and later-time analysis have distinct data roles; review the protocol before interpreting any holdout or deployment claims.
