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
