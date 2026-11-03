# Fixed experiment partitions

`create_manifest(records, source_sha256=..., seed=...)` accepts source-ordered
`{"id": "material-id", "group": "material-or-trajectory-group"}` entries. It returns
a versioned JSON-serializable manifest with train/validation/test indices, actual
counts, source SHA256, all IDs/groups and the partition protocol. Save once and reuse
across every backbone, initialization and training seed. Fractions default to
80/10/10 **of groups**; actual record counts are recorded and can differ.

When released author partitions exist, pass a complete ID-to-partition mapping as
`official` to preserve it. All three partitions must be nonempty. Duplicate IDs,
group overlap, missing/duplicate indices and changed dataset fingerprints fail
`validate_manifest(manifest, source_sha256=..., source_count=...)`.

Group definition is a scientific protocol choice: related material calculations,
duplicate structures or trajectory frames require appropriate common groups.
This utility cannot infer physical equivalence from an ID. Deduplication and
pretraining overlap audits remain explicit data-preparation steps. Official splits
with group leakage are rejected and require a documented protocol decision.

Only split metadata are copied, never structures or labels. Indexed JSONL sources
also retain source-ordered IDs, so loading verifies both bytes and manifest IDs.

```yaml
dataset:
  path: data/experiment/structures.jsonl
  split_manifest: data/experiment/split.json
  partition: train
evaluation:
  patience: 30
  min_delta: 0.0
```

Supervised/force-field training with a manifest requires `partition: train`, selects
only those records (and applies an explicit `structures` subset within that role),
and automatically evaluates full validation/test partitions. Inference on the same
source honors its configured partition; select `partition: test` explicitly to
score held-out inputs. Overriding the input source clears inherited split metadata.
See [evaluation](../../engine/evaluation/README.md). This integration is pending
numerical Slurm validation; generation needs its dedicated workflow and fails
explicitly rather than treating training metrics as held-out results.
