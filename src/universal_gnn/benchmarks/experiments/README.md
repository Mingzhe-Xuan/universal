# Full primary experiment definitions

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

`write_matrix(matrix, output)` creates a new definition directory and writes each configuration plus
the final manifest; existing outputs are refused. `prepared_not_launched` is deliberate: source
identity checks and configuration preparation cannot substitute for original-model, derivative,
full-graph coverage, paired capacity and storage gates. No training or Slurm submission occurs here.
Use `scripts/prepare_arxiv_matrix.slurm`; runtime readout normalization still requires separate
acceptance in the restored provider environments.
