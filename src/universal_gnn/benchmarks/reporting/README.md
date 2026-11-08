# Evidence-bound result tables

This metadata/file-hash exporter reads the unchanged48-case seed123 scope and
the independent scientific acceptance index. It never trains, loads a model,
re-scores predictions or turns a completed training job into scientific acceptance.

`evidence.py` restricts reads to declared archives, verifies every SHA and chooses
the full matching training report. A historical proof containing both formal and
pilot reports cannot promote a diagnostic. The first MACE968 proof uses an
explicit adapter for its separate993 raw-label/physics and1002 full-inference
evidence; those extra reports are bound in the export's input hash map.

`runtime.py` exports all48 slots, original accepted metrics and real resource
measurements, plus24 pair slots. A complete pair must preserve data, split, head,
optimization and common batch; only initialization/native neighbor statistics
and runtime component annotations are excluded from the protocol comparison.
Differences are pretrained minus scratch. Missing measurements remain null.
Classification tables and paired differences include the metric producer's
`roc_auc` field; the older `auroc` spelling is also supported. Undefined
single-class AUROC stays null in the original metrics and has no numeric paired
difference. Metric values and the classification scorer are preserved.
Process wall time includes train/validation/test/save; combined CPU post time is
not isolated inference throughput. Final artifact bytes are not peak disk usage.
Component effective parameter counts are declared upper bounds, not observed
nonzero-gradient counts. No cross-seed statistics or universal benefit is inferred.

```bash
PYTHONPATH=src python scripts/summarize_arxiv_results.py \
  --index results/paper-completed-20261105/formal-index.json \
  --output results/NEW-primary-summary
```

Run on a machine containing the complete declared acceptance archives. This is a
bounded metadata and checksum operation; bulk remote processing still uses CPU
Slurm. Outputs are a new `summary.json` and `summary.md`; existing output is
refused. Unsupported or incomplete accepted evidence fails instead of being
silently dropped. Unaccepted generation and supplementary experiments remain
uncompleted slots or separate evidence, never inferred results.


Executed CPU controls: source `c2155e2`, Slurm1861/1862 both completed0:0;
30 pure reporting/predictive-assessment tests with zero failures or skips, nine
source Gitblobs and15 control artifacts verified. The accepted23-case snapshot
contains48 rows/24 pair slots/11 complete pairs with891 input hashes and exact
original metrics/costs. Its committed reporter source is bound explicitly; this
software validation adds no scientific training result.

AUROC-field correction: source `fdeee4b`, CPU Slurm1953/1954 both completed0:0;
34 pure controls,11 source Gitblobs and15 archived control artifacts verified.
The new committed24-case snapshot preserves the earlier24 rows,24 pair slots,
12 complete pairs and952 input hashes exactly. These software/metadata controls
add no scientific model result; generation still requires its actual formal
quality schema before export.

## Figure export

`figures.py` presents an existing reporter summary. It checks all48 row and24
pair identities, acceptance counts, selected metrics, original units and signed
paired values. It does not repeat the reporter's scientific archive verification.
The caller must supply the SHA256 of the previously accepted summary bytes.
Missing results stay null; a missing task panel contains no numerical points.
All plots use one training seed, linear axes and original units, with no error
bars, normalization or additional scientific acceptance.

```bash
PYTHONPATH=src python scripts/plot_arxiv_results.py \
  --summary results/ACCEPTED-summary/summary.json \
  --summary-sha256 EXACT_SHA256 \
  --output results/NEW-figures
```

Install the optional `paper` extra for Matplotlib. Outputs are `accepted-metrics.svg`,
`accepted-metrics.png`, `plot-data.json`, `caption.md` and the original `summary.json`.
Existing output directories are refused. `plot-data.json` retains exact original
point values, missing slots, signed differences, input/renderer hashes and versions.
Defaults select energy per atom, forces, dielectric components and phonon spectrum.
Dielectric component errors retain their recorded coordinate frame; spectrum units
remain dataset-defined. No electronic grid, symmetry projection or spectral
renormalization is inferred. The global accepted count describes the full48-row
summary; the image shows only its selected metrics.

`--panels FILE.json` can select other metrics already present in an accepted
summary. Each object has `task`, `path`, `unit`, `title`, for example
`{"task":"bandgap","path":"bandgap.mae","unit":"eV","title":"Band gap"}`.
Units must agree with the reported target or metric units; the standard
classification scores are dimensionless. This exporter cannot create missing
generation results or replace its still-required full formal quality schema.
Render and verify figures through CPU Slurm when working on Guqq2; no GPU or
model execution is needed.
