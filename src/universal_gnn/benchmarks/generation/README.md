# Complete generation pair preparation

Input is one corrected, frozen full experiment matrix and a generation pair ID.
The public entry checks both initializations and the full Perov-5 split
11356/3787/3785. All numerical work requires a Slurm GPU allocation.

From a clean fixed source checkout with existing data/models/runs links:

```bash
UGNN_PYTHON=/home/xmz/.venvs/universal-mace/bin/python \
UGNN_MATRIX=runs/arxiv-v1/definition-947/matrix.json \
UGNN_MATRIX_SHA256=b792524e098298500c75785eaf06051824f66d27cfcbae794bb55f5cfe1a2651 \
UGNN_PAIR=seed-123--generation--mace \
UGNN_OUTPUT=runs/arxiv-v1/new-mace-generation-preparation \
sbatch scripts/prepare_generation_pair.slurm
```

Use `universal-official` for CGCNN/ALIGNN and `universal` for NequIP.
Create `runs` before submission so Slurm can open logs. Use a new output path.
The surrounding launcher must verify original initialization, generation protocol
regressions and diagnostic acceptance before running this preparation. A preparation
pass does not launch or authorize formal training on its own.

The implementation compares original unconditioned body features and native
predictions, constructs every clean training native/auxiliary graph, and fits the
volume prior from the full actual training geometry. CGCNN's reference CIF reader
receives an unused temporary CSV scalar; scientific labels/configs are untouched.
It runs independent paired capacity checks for training (initial batch16,
2 warmup/at least100 measured batches) and sampling (initial batch4,
1 warmup/at least5 measured batches). Every declared worst case receives a full
batch; measured counts grow if necessary. Only typed CUDA OOM halves batch.
Unknown errors, numerical failures and timeouts stop the preparation.

`train-capacity/config.*.resolved.json` are the formal training candidates.
`sample-capacity/config.*.resolved.json` retain a separate sampling batch and must
never overwrite the training candidates. Both phases preserve100 noise levels
and2 inner steps, train-only prior, full partition and precision. Scratch native
neighbor statistics, where required, cover the entire training partition.
`report.json` retains both receipt chains, source-bound prior and probe timing.

Clean graph extrema cannot bound every evolving noisy graph. Actual training
probes corrupt inputs and sampling probes traverse the configured diffusion, but
they do not establish trained-model sample quality or all-run memory safety.
The separate quality evaluator currently samples singly: its formal budget remains
1000 attempted samples,5 draws per condition, seed456 from validation-best weights.
Probe throughput at a different batch is not a measured1000-sample runtime.
No DFT thermodynamic stability claim is made.
