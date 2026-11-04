# Published material-ID overlap

`read_reference_splits(archive, expected_sha256)` verifies the exact published ZIP,
then reads its `ids_train_val_test.json` and `config.json` without deserializing
weights. It requires unique/disjoint published partitions and matching counts.

The default `policy='strict'` still rejects cross-partition IDs. For an audited
published roster with known overlaps, explicit `policy='report_ambiguity'` retains
the conflicting memberships and marks `mutually_disjoint=false`; it does not
certify the roster as disjoint. Duplicate IDs within a partition, bad hashes,
invalid IDs and config/count mismatches remain errors under both policies.

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

The audit's explicit `reference_policy='report_ambiguity'` (CLI
`--reference-policy report_ambiguity`) adds a `multiple_roles` bin and records
every published role for each ID. Independent `parameter_training_id_matches`
and `model_selection_id_matches` include overlapping memberships, so an ID in
both published train/test remains training-exposed. No role is silently chosen,
removed or reassigned. This mode reports ambiguity, not a clean held-out set.

Use `scripts/audit_pretraining_ids.py` inside Slurm for complete-data work.
Outputs are a new directory with `id-overlap.jsonl` and `report.json`, retaining
reference/config/source SHA and explicit interpretation limits. Existing outputs
are never overwritten. Incomplete or invalid inputs cannot publish a passed
report; failed partial files remain for inspection. No model runs, label changes
or split changes occur. Reusing this audit does not count as training or accuracy
evaluation. Models without a complete published roster must be recorded as
unknown in the [experiment audit](../../../../docs/plan/arxiv_v1_experiments.md).
