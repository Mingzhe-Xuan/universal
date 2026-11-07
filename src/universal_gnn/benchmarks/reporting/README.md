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
