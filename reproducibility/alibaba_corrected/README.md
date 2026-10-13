# Causal-corrected Alibaba evidence

The separately published public corrected-evidence archive contains the G5
protocol, source training/preprocessing code, 14 checkpoints, six-margin
calibration, frozen selector, 160 corrected held-out cases, saved prediction
errors, bootstrap statistics, figures and `README_REPRODUCE.md`. It does not
contain the third-party raw Alibaba `machine_usage.tar.gz`/CSV or the event-
prefix/corrected full arrays. Obtain the source data from the
[official Alibaba ClusterData repository](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-v2018)
under its own terms. Its reproduction README gives the exact expected source
hashes and fresh-root reconstruction commands.

The public archive has a new SHA-256 manifest and a precise redaction record
for ten historical text files with local Windows account paths. Some embedded
historical file-hash references continue to describe the private original;
the new public manifest governs the bytes of this derivative.

The corrected calibration executed all six margins but **none** passed the
five gates. The frozen selector has `tau=None` and deployed the adapted
PT-A57 reference fallback. This is a reconstructed causal correction on a
previously observed evaluation population, not a new blind held-out test.
The earlier leaked-input positive Alibaba result is historical invalid
evidence and is not the current paper's supported conclusion.

The included `audit/rebuild_raw_prefix.py --self-test` passes an artificial
12-row parser fixture without opening the real raw archive. No real raw-
trace reconstruction, model training or new evaluation was run for this
publication.
