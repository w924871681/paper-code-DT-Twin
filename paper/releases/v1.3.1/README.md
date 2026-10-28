# MSA-DTI paper and figure materials — v1.3.1

This release contains the current 15-page manuscript and 5-page supplement,
their LaTeX sources, all figures and the plot-ready records associated with
the Bitbrains-based MSA-DTI paper. The paper studies selection and adaptation
of source-trained digital-twin models under operation and parameter limits.

- `main.tex`, `main.pdf`: manuscript source and compiled document.
- `supplementary.tex`, `supplementary.pdf`: supplement and compiled document.
- `figures/`, `tables/`: assets needed to compile the two documents.
- `data/`: plot-ready values, task-level summaries, calibration and resource
  records, normalisation information and selection inputs.
- `plotting/plot_figures.py`: portable code to regenerate the experimental
  Figures 5–9. The 15-page paper's Fig. 5/6 functions and Fig. 7/9
  style-restoration functions were retained; Fig. 8 uses its reviewed
  source-sensitivity plotting code. Outputs are written separately and do
  not overwrite the manuscript figures.
- `plotting/plot_supplement.py`: code to regenerate supplementary Figure S1.
- `selection/frozen_policy.py`: the frozen selection gate and rank functions
  used by the evaluation pipeline; `selection/replay_selection.py` checks the
  published 360 evaluation decisions using saved post-adaptation validation
  scores and resource counts.
- `reproduction/`: verified paper-model checkpoints and a provenance-labelled
  snapshot of the experiment, preselection, source-training and baseline code.
  Additional source weights are provided as separate v1.3.0 release assets; see
  `reproduction/README.md` for their identities and limitations.
- `verify_results.py`: recomputes selected summary statistics and checks the
  provided task-level records; `build.ps1` compiles both LaTeX documents twice.

## Run

Python 3.13.5 and the versions in `requirements.txt` were used for verification.

```bash
python -m pip install -r requirements.txt
python verify_results.py
python selection/replay_selection.py
python plotting/plot_figures.py --output generated_figures
python plotting/plot_supplement.py --output generated_figures
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error supplementary.tex
pdflatex -interaction=nonstopmode -halt-on-error supplementary.tex
```

On the reference environment, reconstructed Figures 5–9 and S1 match the manuscript
figures in extracted text, page dimensions and rendered pixels. Differences in
fonts or library versions may affect rendering on another machine.

## Evidence and reproduction scope

The source, development, calibration and evaluation roles are disjoint by VM
identity. The evaluation is a retrospective, non-blind comparison from one
workload trace; independence of historical use is not established. A bootstrap
interval over VMs does not turn it into independent blind confirmation.

The release allows verification of the reported aggregate data, replay of the
saved-score selection decisions, figure regeneration and LaTeX compilation.
The release now also provides the 14 paper-model source checkpoints, the
baseline source weights and the frozen preliminary synthetic initialization
bank. The archived execution scripts retain their original environment and
path assumptions; a clean raw-data-to-results rerun has not been verified.
The original per-case C3-0 preselection evidence has not yet been located in
the checked archives. See `reproduction/README.md` for the exact scope. The trace is available from
the [Grid Workloads Archive](https://atlarge-research.com/gwa-t-12/); follow
its attribution conditions when using it.

Version v1.3.1 retains the v1.3.0 experiments and uses the development-selected A55 reference. The repository's
older v1.2.7 records have a different reference and evaluation design; do not
combine them without checking the protocol. The figure-source adaptation is
reporting code, not a new experiment or a change to the paper's method.
