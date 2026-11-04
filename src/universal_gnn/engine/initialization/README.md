# Original-backbone preparation

This module prepares training-only neighbor normalization for original MACE/NequIP scratch
construction. `policy.py` checks complete train membership, source/manifest/input fingerprints and
precision. `neighbors.prepare_native_neighbors(config)` returns a copy with
`backbone.neighbor_statistics`, using each provider's original `native_input` one structure at a time.
It never calls the GNN forward and does not fit atomic energies or target scales. Original cutoff and
element vocabulary remain in force. The original artifact, graph adapter source and dependency
versions are recorded; incompatible cached receipts fail explicitly. Construction/scanning preserves
the caller's RNG state.

Run the preparation CLI through `scripts/prepare_native_neighbors.slurm`, providing `UGNN_CONFIG`
and `UGNN_RESOLVED_CONFIG`. Its output is a full configuration suitable for the same task's capacity
preflight and training. Complete train JSONL and a split manifest are required; partial selections,
validation/test records, plugin sources and graph overrides are rejected. Existing output files are
never overwritten.

The explicit preparation CLI resolves statistics before original MACE/NequIP scratch construction.
Training, generation and capacity workers now invoke the same preparation before construction;
this automatic route awaits its own Slurm integration acceptance. Full resume inherits omitted
saved statistics and then validates their complete binding. The explicit CLI remains available.
Other providers and pretrained initialization retain their existing paths. Cached receipts must
match input precision, native cutoff, complete training membership, artifact and graph provenance.
An invalid receipt is a configuration failure and must never trigger batch halving.

Status: Slurm911 passed five actual original graph/calibration/fresh/RNG tests per provider.
The complete64-record band-gap pilot training partitions were then calibrated and used by
MACE916 and NequIP915 for both original-architecture initialization modes on CUDA.
This proves the explicit preparation route for these inputs; automatic training/capacity
integration remains separate. See [evidence](../../../../docs/agents/arxiv-pilots.md).
Full-dataset preparation must scan that dataset's complete training partition anew.
