# Periodic generation protocol

`protocol.py` is independent of model libraries. Its versioned rules are shared by
training, checkpoint continuation and independent held-out generation evaluation.
It does not itself train a model or establish generated-structure quality.

- `corruption_seed`: `per_epoch_structure_v2` derives noise from training seed,
  stable structure ID and epoch. Evaluation uses distinct fixed train/validation/test
  namespaces and an explicit draw index. Selection order and minibatch size do not
  change a structure's v2 noise. `per_structure_v1` retains the original index-based
  fixed-noise seed for explicit legacy continuation. Full resume rejects a changed
  or unversioned objective; weights-only initialization can change it.
- `fit_volume_prior`: consume **training records only**, with atomic numbers and
  row-vector angstrom cells. Fit the geometric mean of volume/atom and its log
  population standard deviation. Record the training identity hash and count.
  Sampling starts from a cubic cell of this volume and random fractional positions;
  no held-out positions or cell values enter the prior.
- `condition_indices`: choose fixed held-out condition IDs without replacement,
  using a sampling seed. A requested count larger than the partition fails.
- `wasserstein_1d`: compare scalar structural distributions in explicit input units.
  This does not compare energies or imply thermodynamic stability.

`scripts/prepare_generation_prior.py` verifies a standard JSONL and split manifest,
fits only `train`, and writes an immutable provenance-bound prior receipt. Execute
the [Slurm entry](../../../../scripts/prepare_generation_prior.slurm) on Guqq2.
The prior's partition fingerprint is a canonical hash of source dataset SHA256,
manifest SHA256 and train IDs; it is distinct from the training engine's geometry
fingerprint and must not be silently substituted for it.

The full generation trainer and quality evaluation still require numerical
integration tests before this protocol can be counted as an accepted experiment.
