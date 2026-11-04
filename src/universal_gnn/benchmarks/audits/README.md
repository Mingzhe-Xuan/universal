# Published material-ID overlap

`read_reference_splits(archive, expected_sha256)` verifies the exact published ZIP,
then reads its `ids_train_val_test.json` and `config.json` without deserializing
weights. It requires unique/disjoint published partitions and matching counts.

`audit_id_overlap(config, output, reference_archive=..., reference_sha256=...,
id_prefix='JVASP-', reference_label_field='optb88vdw_bandgap',
target_relation='same_target')` verifies the entire current source SHA, source
order and frozen split SHA, then compares every ID in the same declared namespace.
The target relation must be explicit: `same_target`, `derived_target`,
`different_target` or `unknown`. Known relations are checked against the normalized
source's raw `metadata.label_field`; this does not establish identical numerical
label versions across releases.

For each current train/validation/test partition, outputs count published
`train`, `validation`, `test` and `not_listed` IDs. Published validation exposure
is reported separately because its labels may have influenced model selection.
`not_listed` never means unseen geometry: this ID audit does not reconstruct
pretraining geometries, compare equivalent crystals or prove no target leakage.
Cross-namespace IDs are refused rather than reported as zero overlap.

Use `scripts/audit_pretraining_ids.py` inside Slurm for complete-data work.
Outputs are a new directory with `id-overlap.jsonl` and `report.json`, retaining
reference/config/source SHA and explicit interpretation limits. Existing outputs
are never overwritten. Incomplete or invalid inputs cannot publish a passed
report; failed partial files remain for inspection. No model runs, label changes
or split changes occur. Reusing this audit does not count as training or accuracy
evaluation. Models without a complete published roster must be recorded as
unknown in the [experiment audit](../../../../docs/plan/arxiv_v1_experiments.md).
