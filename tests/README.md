# Verification

Unit tests use small analytic structures and targets to verify geometry and derivatives. They are
not the real-data acceptance matrix. Model training/inference, integration evaluation and resource
work on Guqq2 run through Slurm. Every final acceptance result must identify 10 real structures,
target provenance, optimization, checkpoint reload and inference.

Graph extension tests check local/global mappings, invalid edges, optional attributes, isolated atoms,
PBC/cell gradients, GCN finite-difference forces and second derivatives, custom directory reconstruction,
file-version rejection and source fingerprints (including stale bytecode). Real molecular acceptance
is a separate Slurm run; analytic unit fixtures are not treated as real-data validation.
