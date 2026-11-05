# Supplemental Cartesian tensor datasets

This benchmark module prepares the complete released GMTNet piezoelectric and
elastic labels separately from the frozen144 primary cases. It reuses the
existing restricted pickle reader, geometry converter and standard JSONL writer;
their source files stay unchanged so queued primary preparations retain their
source compatibility. Full conversion belongs in CPU Slurm.

`targets.py` validates finite numeric3x6/6x6 labels. The released contracted pair
order is `xx,yy,zz,xy,yz,xz`; symmetric entries of the encoded minor pair map to
the same stored component. Piezoelectric outputs have shape3x3x3 in C/m^2.
Elastic outputs have shape3x3x3x3, converting kbar to GPa by multiplication0.1.
There is no engineering-shear factor2, major-index averaging, symmetry projection
or source magnitude/whole-zero/atom-count filter. The source convention follows
[GMTNet piezo code](https://raw.githubusercontent.com/YKQ98/GMTNet/main/GMTNet_piezo/data.py)
and [elastic code](https://raw.githubusercontent.com/YKQ98/GMTNet/main/GMTNet_elast/data.py).
Duplicating an encoded label component does not constrain the framework's free
Cartesian27/81 model outputs. Derivative readout and its physical checks remain
separate downstream requirements.
Full Cartesian component losses/metrics include repeated encoded minor entries;
state their27/81-component convention when comparing with published3x6/6x6
contracted-label metrics, which weight those entries differently.

`partitions.py` jointly groups all valid candidates and every immutable primary
dielectric record by shared material ID, exact Cartesian geometry, explicit
`mp-N` references and original primary groups. This includes transitive paths
between supplemental tasks. A group inherits any primary anchor role; two
conflicting roles raise `AnchorConflict`, with a complete conflict report. No
anchor is moved and no conflicting sample is silently removed. Unanchored groups
use the fixed seed0 global group-hash base split, then primary roles override
anchored groups. Actual per-task counts are reported; exact80/10/10 fractions
are not promised. This grouping does not prove crystallographic equivalence or
absence of pretraining exposure. Training seeds123/456/789 do not alter it.

`preparation.py` pins both raw source hashes and the complete primary dielectric
data/canonical split hashes. It visits all raw records to establish candidates,
then converts all records with identical accounting. Invalid labels/geometries
and identical duplicate IDs are recorded by the existing standard writer;
conflicting duplicate records abort. Inputs are hashed again after conversion.
All failed attempts and original primary datasets are retained.

From a clean pinned repository, submit:

```bash
export UGNN_PYTHON=/home/xmz/.venvs/universal-official/bin/python
export UGNN_ELASTIC_SOURCE=runs/full-rank34-source-audit-1048/verified-elastic.pkl
export UGNN_OUTPUT=data/arxiv-v1/supplemental-rank34-NEW_ATTEMPT
sbatch scripts/prepare_supplemental_tensors.slurm
```

For explicit paths, run `scripts/prepare_supplemental_tensors.py` in CPU Slurm
with `--piezo-source`, `--elastic-source`, `--dielectric-data`,
`--dielectric-split` and a fresh `--output`. Public CLI defaults are the frozen
released sources, never a first-N subset. It refuses login execution and dirty
source checkouts. The wrapper requests1CPU/4GiB/30min/noGPU/no-requeue; this is
an initial resource allocation, not measured capacity for model training.

Outputs are `report.json`, full `cross-task-partitions.json` and, for each
`piezoelectric/` and `elastic/`, standard `structures.jsonl`, `split.json`,
`audit.json` and `exclusions.jsonl`. Audits bind source fields/units/conversion,
all IDs/groups/roles, source hashes, exclusions, maximum size and species. No
checkpoint or model is created. Source conversion is not graph, capacity,
derivative, training or scientific accuracy acceptance. Independent complete
source-to-Cartesian and cross-source partition re-scoring is required before
these datasets are used for supplemental model comparisons.

Source86aa7eb completed actual CPU1074/1075 acceptance:39 main tests/205 JUnit
records with no failures, errors or skips; all19500 raw records visited and
19499 valid Cartesian records independently re-scored. Piezoelectric retains
5000 records including2297 whole-zero labels (3998/502/500 split); elastic
retains14499 (11587/1442/1470), with the sole invalid source row explicitly
excluded. An independent bipartite BFS replay confirms15904 material groups,
4976 anchored groups and all4999 immutable primary roles without cross-role
group conflicts. Nine source hashes match Git blobs. Original full outputs are
`data/arxiv-v1/supplemental-rank34-1074/`; evidence is under ignored
`results/paper-rank34-data-20261105/prepared-1074/`. This acceptance covers data
only and counts zero model trainings.

`experiments.py` defines16 separate seed123 comparisons: both full tensor datasets,
all four official providers, and pretrained/scratch. Architecture, response head,
feature processing, full-body optimization and300/patience30 are inherited from
the original seed123 dielectric recipes. Only the property, source/label units and
the separate supplemental output namespace change. No symmetry projection,
normalization/filtering of tensor targets or primary48 mutation is introduced.

Run `scripts/prepare_tensor_experiment_definitions.py --output NEW_DIRECTORY`
in CPU Slurm from a clean pinned checkout. It requires the original947 matrix,
the exact1074 conversion and1075 independent proof, then streams every record
of both datasets to check data/split hashes, ordered IDs and all27/81 finite
Cartesian label components. Zeros and tails are retained. It writes
`definitions.json` and16 ordinary training configs under `configs/`.
The output kind is `arxiv_v1_supplemental_tensor_definitions`, deliberately
separate from the primary matrix and its case execution guard. Graph scanning,
paired CUDA capacity/OOM resolution, both official model physical validations,
formal training and independent raw-label/test/full-inference acceptance remain
required. Defining these cases does not launch training or increase primary counts.


Definition source90a5836 passed actual CPU1231/1232:85 main tests/509 JUnit
counts without failure/error/skip,19499 ordered records/1309419 finite Cartesian
components,16 emitted configs,5 executed Git blobs and retained successful
control terminal/request binding. Saved files are under ignored
`results/paper-tensor-definition-20261105/1231/`; server configs are under
`runs/tensor-definition-control-1231/definitions/`. Eight low-priority full GPU
preparers1233/1235/.../1247 and eight afterany CPU terminal recorders are armed.
These exact request receipts are not completed numerical preparation or training.
Even a passed preparer requires the separate independent complete gate before
formal supplementary training. The primary campaign remains48 seed123 cases.

`gate.py` is the separate independent preparation gate. It selects exactly one
of the frozen16 cases, replays the complete source audit, and shares the primary
gate's original graph-row/probe, both-mode capacity/typed-OOM, calibrated config,
official artifact/initialization and installed-version checks. The primary
`case_spec` still accepts only the original144 definitions. Higher-tensor gates
also require the original two/100-batch schedule, exact worst-input IDs, finite
27/81-component auxiliary derivatives, rank parity, unchanged geometry tolerances,
both mixed parameter gradients and the four accepted validator source hashes.
Invariant CGCNN/ALIGNN retain fixed-frame guarantees; MACE/NequIP require O(3)
covariance and the appropriate odd/even inversion, without symmetry projection.

The original preparation request and its exact retained successful terminal,
owner/source/resources/report hashes must agree. The preparer's own
`independent_full_gate_pending` flag remains true; this gate writes separate
evidence and does not edit that immutable report. Missing/running/failed evidence
cannot pass. A producer's status or number of scanned graphs alone is insufficient.

Run `scripts/check_tensor_preparation.py --pair PAIR --preparation PREP_DIR
--receipt PREP_JOB_JSON --output NEW_GATE_DIR` in CPU Slurm and the provider's
Python environment. The wrapper `scripts/check_tensor_preparation.slurm` accepts
`UGNN_PYTHON`, `UGNN_PAIR`, `UGNN_PREPARATION`, `UGNN_RECEIPT`, `UGNN_OUTPUT` and
optional `UGNN_DEFINITIONS`/`UGNN_PRIMARY_MATRIX`. Use `afterok` on both the
original GPU preparer and its CPU terminal recorder. The wrapper requests
1CPU/4GiB/20minutes with CUDA hidden. It validates both modes, preserves partial
failed attempts, and writes `gate-pretrained.json`, `gate-scratch.json` and
`report.json`. Training wall-time is a finite reserved budget from measured
workers, not a runtime guarantee. This module imports no Torch, loads no model
and submits no jobs. A passed gate is still not training or heldout accuracy.


Gate source3483500 passed actual CPU1252/1253 acceptance:119 main tests/825
JUnit counts without failure/error/skip,7 executed Git blobs, seven real complete
primary preparation/training gates replayed without model execution, full tensor
source/spec audit, and actual CPU/unfinished evidence rejection. Proof is under
ignored `results/paper-tensor-gate-20261105/1252/`. Eight independent CPU gates
1254-1261 are armed after both their original GPU preparer and terminal recorder;
their request/resource/source/dependency identities are saved under
`results/paper-tensor-gate-20261105/armed-3483500/`. These pending requests
count zero supplemental trainings; the separate tensor training/post execution
path below requires successful independent preparation; pending gates do not
authorize or count as training.

`execution.py` provides the separate full supplemental training and assessment
entry. `selected_case` checks the exact accepted definition bytes and rebuilds
the closed16-case list. `checked_pair_gate` requires the successful independent
pair report, both hashed mode gates, unchanged case/source/budget and provider
environment, then rebuilds the complete original preparation gate before any
training. It records those original gate/report/request inputs for subsequent
assessment. Existing output directories are refused; no resume or automatic
retry is implied. The original primary144 selector remains separate.

The shared training executor keeps all samples, float32, both whole-backbone
initializations, the accepted common batch,300epoch cap and patience30. Full
epoch/validation coverage, exact validation-best reload and all ordered test
IDs are checked using native Cartesian shapes27/81. Saved raw label assessment
requires original C/m^2 or GPa, untransformed float32 source labels, every test
component and zero/nonzero/component groups; no symmetrization or tail filtering.

Run the following commands in the original provider environment, from an
immutable source checkout, through Slurm:

```bash
python scripts/run_tensor_case.py train --case CASE \
  --preparation PREP --independent-gate INDEPENDENT_PAIR_GATE \
  --budget-seconds MEASURED_RESERVED_BUDGET
python scripts/run_tensor_case.py post --case CASE --output NEW_POST_DIRECTORY
python scripts/run_tensor_case.py verify --case CASE \
  --postprocessing NEW_POST_DIRECTORY --output NEW_VERIFICATION_DIRECTORY
```

The optional `--definitions`/`--primary-matrix` paths default to the original
accepted files. Training optionally accepts the original `--receipt` path;
assessment recovers the exact inputs from `execution-gate.json`. Train output
is fixed by the case, not supplied by the caller. `post` recomputes raw-label
metrics, runs CPU trained-best finite differences/covariance/rank parity/mixed
gradients on the original worst two inputs, and streams the complete source.
`verify` reloads the full context, forbids model loads/forwards, independently
recomputes raw metrics and validates every output ID/shape/finite component,
source/best/validator/input hashes and retained trained-best physical evidence.
The CPU physics contract has the same tolerances as CUDA preparation while
explicitly requiring CPU provenance; CPU reports cannot certify CUDA readiness.

The wrappers [run_tensor_case.slurm](../../../../scripts/run_tensor_case.slurm)
and [assess_tensor_case.slurm](../../../../scripts/assess_tensor_case.slurm)
use `UGNN_PYTHON`/`UGNN_CASE`; train additionally requires `UGNN_PREPARATION`,
`UGNN_INDEPENDENT_GATE`, `UGNN_BUDGET_SECONDS`, while CPU stages require
`UGNN_STAGE`/`UGNN_OUTPUT` and verify requires `UGNN_POSTPROCESSING`.
Train is GPU1/2CPU/64GiB, CPU post2CPU/32GiB/72h; override train time from the
independently measured reserved budget and verify to1CPU/8GiB/4h when submitting.
Use afterok independent preparation for train, afterok train for post, and
afterok post for verify. CPU stages hide CUDA. These entries submit no jobs;
an external managed launcher still must retain exact requests/terminal receipts
and prevent duplicate submissions. Pending preparations and passing protocol
fixtures remain zero completed supplemental trainings.
