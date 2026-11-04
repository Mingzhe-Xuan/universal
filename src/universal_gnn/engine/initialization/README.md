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
Automatic preparation in training, generation and capacity workers is a separate integration unit;
until it is published and accepted, pass the CLI's resolved configuration to these entry points.
Other providers and pretrained initialization retain their existing paths. Cached receipts must
match input precision, native cutoff, complete training membership, artifact and graph provenance.
An invalid receipt is a configuration failure and must never trigger batch halving.

Status: runtime prototype pending actual MACE/NequIP graph, RNG and training tests on Slurm.
Pure policy tests do not establish numerical acceptance. The independent preparation CLI remains
available for preparing a reusable resolved configuration after runtime acceptance.
