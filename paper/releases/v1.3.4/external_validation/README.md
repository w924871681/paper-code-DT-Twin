# Additional workload evaluation records

The CSV/JSON records cover 236 cases: 30 Materna VMs and 29 Bitbrains VMs, each with H=1,4 and K=10,20. `case_records.jsonl` contains validation scores, budget actions, state hashes and test metrics; `cases.csv` contains the three reported methods; `summary.json` contains VM-aggregated results. `protocol.json` binds sample membership, original archive hashes, and the selection/evaluation rules. Historical code is retained with its original paths and is not a one-command runner.

Run `python external_validation/verify_external.py` from this release folder to verify the 708 saved-score decisions and six MSE summaries. This does not train models or open trace labels. The `inference_replay_audit.json` records replay of every one of the 236 x 7 saved adapted states in the original environment, comparing MSE, MAE, Worst10 and valid counts. It is not independent retraining.

To repeat inference, download the separately provided `MSA_DTI_v134_adapted_states.zip` release asset, and obtain the original Materna and Bitbrains fastStorage archives from the Grid Workloads Archive. The script checks their exact recorded SHA-256 identities. The replay was checked with Python 3.13.5, NumPy 2.1.3 and PyTorch 2.13.0+cu126 on CUDA. With PyTorch, NumPy, and a compatible CUDA environment installed, run:

```
python external_validation/replay_inference.py --materna PATH_TO_MATERNA_ZIP --bitbrains PATH_TO_FASTSTORAGE_ZIP --states PATH_TO_ADAPTED_STATES_ZIP --device cuda
```

Add `--smoke` to check one case per source. The script uses a temporary directory under this folder. It verifies each adapted-state hash and recomputes all three metrics and valid counts; no training is performed. Different numerical environments may fail the documented tolerance. `portable_inference_core.py` changes the historical runner's absolute repository path to a path relative to this release; all scientific functions are retained. A clean retraining from the raw trace to all source and adapted weights has not been validated.

Original selection ran before testing for 225 cases. Eleven Bitbrains cases failed with GPU errors and were reselected in fresh processes after the original test phase opened; their retry decisions were sealed before their own tests. A CSV parser in the historical selection runner fetched and parsed the first subsequent row as text but did not convert or use its CPU label for selection; physical read isolation is not claimed. User-provided knowledge indicates Materna was not previously used in method design, but complete historical independence cannot be established solely from this statement.

Source archives: https://atlarge-research.com/gwa-t-12/ and https://atlarge-research.com/gwa-t-13/. Follow their attribution requirements.
