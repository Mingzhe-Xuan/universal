# Full primary experiment definitions

The current campaign uses **one training seed, 123**, for all primary and supplemental
experiments. The primary scope is48 full-data trainings, with the active and excluded
IDs listed in [the execution scope](../../../../configs/arxiv_v1_scope.json).
The earlier144-case revision2 matrix stays immutable to preserve submitted-job and
result provenance. Its seed456/789 configurations are historical definitions and
must not be scheduled for this campaign. Their pending preparation/launch requests
were canceled with retained Slurm terminal evidence. Generation keeps one fixed
quality sampling RNG seed456; this is not another training replicate.

`registry.inspect_registry(repository)` scans all five registered JSONL sources and source-ordered
IDs, validates released/frozen split counts, pins canonical manifest SHA values and verifies the
four original model artifacts plus the NequIP author blueprint. Run this full-data operation on Slurm.
It does not import Torch, fit labels, construct a GNN or certify runtime readiness.

`recipes.build_matrix(registry)` returns 144 cases: four original backbones, six tasks, two whole-model
initializations and seeds 123/456/789. Definitions retain the original graph/architecture, all training
records, float32/CUDA and full body/head training. Defaults are a declared baseline budget of up to
300 epochs, learning rate 0.0003, patience 30, and task-dependent initial batches. Capacity results
must replace those initial batches; paired modes use their common accepted batch. These defaults
are not tuned results. No legacy ten-structure matrix is reused.

Prediction heads are reset; generation has its own fresh-noise/held-out protocol and separate
1000-sample quality evaluation. Scalar readouts use scalar invariants for equivariant bodies;
dielectric uses the explicit small-response profile for equivariant bodies and fixed-frame response
components for invariant bodies. MLearn supervises total energy and forces only. Original native
head comparisons, molecular/plugin and other additional experiments remain separate requirements.

Definition revision2 names the force-field output/loss `total_energy` and binds it
to the unchanged source label `energy` in eV. Earlier frozen definitions used the
unsupported output name `energy`; they must remain immutable as preparation
history and cannot launch force-field training. Prepare a new matrix rather than
overwriting them. The tests call the real runtime supervision contract for every
force-field case, independently of the recipe's expected names.

`write_matrix(matrix, output)` creates a new definition directory and writes each configuration plus
the final manifest; existing outputs are refused. `prepared_not_launched` is deliberate: source
identity checks and configuration preparation cannot substitute for original-model, derivative,
full-graph coverage, paired capacity and storage gates. No training or Slurm submission occurs here.
Use `scripts/prepare_arxiv_matrix.slurm`; runtime readout normalization still requires separate
acceptance in the restored provider environments.

## Diagnostic pilots

`pilots.prepare_pilots(parent_matrix, output)` derives five 96-record diagnostic datasets and
48 configurations from seed123 of the frozen full matrix. Each original role contributes
64 train, 16 validation and 16 test records, chosen by deterministic ID hash and retained in
source order. Selection uses no labels, atom-count filter or first-N truncation. Classification
and bandgap share the same selected source. The full parent source is hashed and every ID
checked before the new JSONL/split is published. Source or manifest changes prevent publication.

Pilot configs retain original backbones, both entire-model initializations, readouts, precision,
optimizer settings and task semantics. Their declared budget is three epochs at batch two,
with independent validation/test and no early stopping. Sampling step counts stay unchanged;
eight generated structures are declared only as a shape/path diagnostic. Whole-model scratch
and original-model derivative acceptance remain gates, and OOM may still require a smaller
common batch for each pair. Fitted full-data neighbor statistics/priors cannot be reused.

Run `scripts/prepare_arxiv_pilot.py --matrix runs/arxiv-v1/definition-872/matrix.json --output NEW_DIRECTORY`
through Slurm with `PYTHONPATH=src`. It writes `data/`, `configs/` and a manifest whose kind is
`arxiv_v1_diagnostic_pilots`. Status is `prepared_not_launched`; no model or training is executed.
Pilot definitions/results do not count toward the separate48 formal full-data runs.
