# Paired capacity checks

`run_paired_capacity(configs, output, probe=...)` takes exactly `pretrained` and `scratch`
configurations for the same original backbone, task, seed, source/partition, precision, graph,
head and optimization. Inputs require `structures: all` and an explicit `train` split manifest. Initial batch sizes may differ;
MACE/NequIP scratch can carry its separately bound native neighbor statistics. All other
settings must match. Both configurations must explicitly select the official implementation.

Each mode first runs the existing disposable-process preflight. The smaller successful batch
then starts a new check for each mode. If OOM recurs during this common check, both modes are
checked again at the new smaller size. A pass requires both final checks at the same batch.
Only typed CUDA OOM halves batch; any other error or batch-one OOM fails the pair. No weights
or optimizer updates from these checks are retained for training.

Run with the matching provider environment inside a Slurm GPU allocation:

```bash
python -m universal_gnn.benchmarks.pairing.capacity \
  runs/arxiv-v1/definition-947/matrix.json \
  --pair seed-123--bandgap--cgcnn --probe runs/probes/cgcnn-bandgap.json \
  --output runs/paired-capacity/seed-123--bandgap--cgcnn
```

Output must be new. Every independent and common check retains its requests, worker logs,
attempts and resolved config in separate directories. Final top-level configs are written only
after both modes pass together. The original input matrix is unchanged. Use `--phase sample`
separately for generation; its steps and conditions stay fixed and its batch can differ from
training. Matrix selection verifies the frozen registry and selected configuration digests.

This controller does not certify a caller's full-training-graph coverage claim. A capacity pass
alone never proves derivative correctness, held-out quality, full-data coverage or readiness
to launch formal training. The graph scan, original-model and other experiment gates remain
required. Pure subprocess tests cover controller behavior; actual GPU acceptance is separate.

`evidence.verify_capacity_evidence(directory, probe)` verifies saved trial hashes,
request/result identity, typed OOM exit42 and exact batch halving, complete measured
workers and worst-case coverage, and both final modes at the same common batch.
It returns accepted workers plus retry/trial counts and the capacity digest. It
does no numerical work and never retries anything. Consumers must count accepted
trials rather than assume exactly four worker result files: legitimate OOM retries
and repeated common rounds retain additional files. Unknown errors, incomplete
measurements and altered evidence remain fatal. This proves only the supplied
capacity probe; all other scientific and full-data gates still apply.
