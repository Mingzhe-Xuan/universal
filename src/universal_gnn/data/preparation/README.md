# Full fixed-release preparation

This module streams every record from the fixed JARVIS 2022 bandgap archive
(Figshare 38521619) or interpolated DOS archive (29216859). Run through Slurm:

```bash
python -m universal_gnn.data.preparation data/downloads/jarvis-dft3d-38521619.zip \
  --kind bandgap --output data/arxiv-v1/jarvis-gap --split-seed 0 --metal-threshold 0.01
python -m universal_gnn.data.preparation data/downloads/jarvis-edos-pdos-29216859.zip \
  --kind phonon_dos --output data/arxiv-v1/jarvis-phonon-dos --split-seed 0
```

The module requires only Python's standard library. Source atoms become dataset-v1
JSONL with atomic numbers, Cartesian angstrom positions, row-vector cells and 3D PBC.
Fractional input coordinates are converted using the supplied cell. Invalid geometry
or missing/nonfinite labels are audited by source index/ID; no first-N or atom-count
filter is applied. Finite bandgaps, including zero, are retained. Bandgap and derived
binary classification share **one dataset and one frozen split**: class 0 is gap at
or below the configured eV threshold; class 1 is above it. Select the target with a
normal dataset binding in the task config.

Phonon DOS uses all finite `pdos_elast` vectors of length 200; optional electronic DOS
uses `edos_up` length 300. Arrays retain their released order and scale. No frequency
grid, units, interpolation or normalization are invented when absent from this archive.
Use `task.property: spectrum`, with 200/300 channels and the release-defined vector
convention. Shape/label coverage is validated; spectral physical conclusions require
the source's axis convention to be documented separately.

Output must be fresh: `structures.jsonl`, `exclusions.jsonl`, `split.json`, `audit.json`.
The audit records full counts, source/data SHA256, excluded IDs/reasons, maximum atoms,
actual split sizes and class convention.
The element vocabulary and atom occurrences are recorded for later backbone coverage
checks; preparation never drops structures based on a pretrained model's element list.
Exact duplicate IDs are excluded only if
geometry/labels match; conflicting duplicate IDs stop preparation. Equal exact
Cartesian geometries with distinct IDs are retained in a common split group.
Explicit shared `mp-NNN` reference IDs also join groups, transitively with geometry matches.
Grouping does not claim crystallographic equivalence or solve pretrained label overlap;
the audit explicitly leaves that later check pending. Reference IDs are retained.

The split seed is independent of model/training seeds. Geometry/label validation and
the fixed group protocol must complete before the audit is written; a partial directory
without a successful audit is not a complete dataset. Full archive counts and timings
must be measured on Slurm, not inferred from tiny fixtures or the advertised release size.
