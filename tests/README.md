# Verification

Unit tests use small analytic structures and targets to verify geometry and derivatives. They are
not the real-data acceptance matrix. Model training/inference, integration evaluation and resource
work on Guqq2 run through Slurm. Every final acceptance result must identify 10 real structures,
target provenance, optimization, checkpoint reload and inference.
