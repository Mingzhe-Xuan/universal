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
