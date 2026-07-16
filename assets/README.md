# Model assets

Large model weights are not stored in ordinary Git history. The required
filenames, purposes, horizons, architecture indices, and SHA-256 digests are
listed in `model_assets.csv`.

## Publication status

The permanent model-asset archive URL is **pending**. No GitHub Release,
Zenodo, or Figshare location is claimed until the archive has actually been
uploaded and independently checked. This means Level C is not currently
available from a fresh clone alone. Level A verification and Level B paper
output reconstruction do not need these files.

When the archive is published, record its permanent URL and release checksum
in this document and in the release notes. Do not commit the weight files to
ordinary Git history.

## Expected directory tree

Pass the directory that directly contains the files below as `--asset-dir`:

```text
<asset-dir>/
|-- strong_h1_a1.pt
|-- strong_h1_a6.pt
|-- strong_h1_a13.pt
|-- strong_h1_a55.pt
|-- strong_h1_a56.pt
|-- strong_h1_a57.pt
|-- strong_h4_a1.pt
|-- strong_h4_a6.pt
|-- strong_h4_a13.pt
|-- strong_h4_a55.pt
|-- strong_h4_a56.pt
|-- strong_h4_a57.pt
`-- ours_weight_bank_source_pooled_c1_v1_src20.pt
```

The filenames are historical archive identifiers. Public paper text refers to
the source-initialization bank and reference candidate.

## Verification

```powershell
python .\scripts\verify_assets.py --asset-dir <asset-dir>
```

The command reports each expected filename as `OK`, `MISSING`, or `MISMATCH`.
It exits nonzero if a required file is absent or if its SHA-256 digest differs
from `model_assets.csv`. Extra files are reported but do not invalidate the
archive.

