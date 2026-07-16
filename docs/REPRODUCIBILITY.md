# Reproducibility

The repository exposes three deliberately separate levels.

## Level A: repository verification

```powershell
python .\scripts\verify_repository.py
```

This checks imports, required CSV/JSON and metadata files, frozen configuration
fields, immutable and sanitized-copy checksums, narrow numerical-correction
hashes, model-asset manifest syntax, numerical consistency, public terminology,
and privacy-sensitive paths. Model weights are not required.

## Level B: rebuild released tables and figures

```powershell
python .\scripts\generate_paper_outputs.py
```

This reads only released repository sources and writes:

- five code-generated revised figures and their QA artifacts;
- seven checksum-pinned unchanged paper PDFs;
- the exact structured data for revised-manuscript Tables 1--6 under
  `tables/paper_csv/` and `tables/paper_latex/`;
- the broader checked public table layer;
- companion figure-data CSV files and a provenance manifest.

It does not train a model and requires no weights. The runtime source of truth
is `results/supplementary/repeated_runtime_summary.csv`; target-side times use
the repeated synchronized measurements.

## Level C: full training and evaluation

```powershell
python .\scripts\verify_assets.py --asset-dir <path>
python .\scripts\run_full_reproduction.py --asset-dir <path> --plan-only
```

Level C requires a CUDA-capable GPU, the complete archived model-asset bundle,
and substantial runtime. Alibaba evaluation additionally requires the original
`machine_usage` archive and a real source-initialization bank built from the
processed source machines. Because the permanent model archive and public
end-to-end driver are pending, the wrapper validates prerequisites and records
the stage order but returns an explicit blocked status for execution.

Do not tune the frozen candidate bank, source-training seeds, target split,
common adaptation procedure, preset selection margin, or locked evaluation
pools. See `results/README.md` for the boundary between frozen legacy schemas
and the public presentation layer.

