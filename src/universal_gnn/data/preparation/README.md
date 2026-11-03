# Full fixed-release preparation

This module streams every record from the fixed JARVIS 2022 bandgap archive
(Figshare 38521619) or interpolated DOS archive (29216859). Run through Slurm:

```bash
python -m universal_gnn.data.preparation data/downloads/jarvis-dft3d-38521619.zip \
  --kind bandgap --output data/arxiv-v1/jarvis-gap --split-seed 0 --metal-threshold 0.01
python -m universal_gnn.data.preparation data/downloads/jarvis-edos-pdos-29216859.zip \
  --kind phonon_dos --output data/arxiv-v1/jarvis-phonon-dos --split-seed 0
```

The JARVIS writer requires only Python's standard library. Source atoms become dataset-v1
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

## GMTNet dielectric release

`gmtnet.py` reads the complete author-released `jarvis_diele_piezo.pkl`, with a
restricted collections/NumPy unpickler and a required SHA256 from the recorded
download receipt. NumPy is needed for the actual released pickle; importing the
metadata/writer and testing plain collection fixtures does not import NumPy or Torch.
Use only the pinned author dataset, rather than arbitrary uploaded pickles.

```bash
UGNN_GMTNET_SHA256=<recorded-source-sha256> sbatch scripts/prepare_arxiv_gmtnet.slurm
```

Every source record is visited. The `dielectric` field is retained as a finite,
dimensionless Cartesian 3x3 tensor in its released component order. The separate
`dielectric_ionic` field is not added. There is no symmetrization, eigenvalue
filter, atom-count cap or nonzero filter. Missing/malformed labels and geometry
are audited by source index/ID. The writer shares JARVIS's JSONL, duplicate-ID,
geometry/reference group, source/data hash and fixed split protocols. The audit
records the tensor convention, both preparation source hashes and measured full
counts; it does not substitute the paper's reported 4713 for a measured count.
The complete pickle is loaded in memory inside Slurm before record-wise writing.

## MLearn energy/force release

`mlearn.py` streams all twelve author JSON files for Cu/Ge/Li/Mo/Ni/Si from a
pinned download receipt. Each entry requires `repo`, `commit`, `upstream_path`,
`filename`, `bytes`, `sha256` and `git_blob_sha1`; the receipt uses the same schema
as `data/downloads/arxiv-matrix-raw/download-receipt.json`. Put the twelve raw
files in its sibling `mlearn/` directory using their receipt filenames.
All raw sizes, SHA256 and Git blob hashes are verified before reading their records.

```bash
sbatch scripts/prepare_arxiv_mlearn.slurm
```

The writer preserves ordered Cartesian sites, row-vector angstrom cells, 3D PBC,
total structure energy in eV and ordered N-by-3 forces in eV/angstrom. Zero forces
and energies are valid. Disordered/malformed sites or nonfinite/misaligned labels
are audited by a stable `mlearn:<element>:<released-role>:<source-index>` ID.
No first-N or atom-count cap is applied. Raw `virial_stress` is not supervised.
The [author data protocol](https://github.com/materialyzeai/mlearn/blob/10c427a5480c6281c15c64efaf869b03be04818f/mlearn/data.py)
specifies total energy and the N-by-3 force array; its
[LAMMPS E/F protocol](https://github.com/materialyzeai/mlearn/blob/10c427a5480c6281c15c64efaf869b03be04818f/mlearn/potentials/lammps/templates/efs/in.efs)
uses metal units. Energy/atom scaling is not silently introduced.

All valid released test records remain test. Only released training groups are
split into train/validation, by deterministic seed/hash order within each element
(default 10% of groups for validation, with both nonempty). Training snapshots
sharing their `Snapshot N of M of ...` description family are joined, transitively
with exact-geometry groups. There is no random-frame fallback for insufficient groups.
An exact geometry crossing released training/test stops preparation for review.

The released train/test files **already share AIMD description families**. This
is disclosed in the audit; only train-versus-validation family separation is
enforced. These results must be described as evaluation on the author's released
test frames, rather than trajectory-independent generalization. Description
families can merge distinct simulations with identical descriptions; they are not
a claim of uniquely identified trajectories. Exclusion and full source/partition
counts, per-file hashes and actual element coverage remain mandatory evidence.

## Perov-5 generation structures

`perov5.py` consumes the three pinned CDVAE `data/perov_5/{train,val,test}.csv`
resources. Use the same per-file receipt fields as MLearn, with repository
`txie-93/cdvae`, and place their original files under sibling `perov5/`.
The receipt can include other repositories; only these three resources are used.
Each CSV's original size, SHA256 and Git blob are verified before reading.

```bash
sbatch scripts/prepare_arxiv_perov5.slurm
```

ASE 3.27 parses each CIF, retaining the released conventional cell and atom order.
There is no primitive reduction, standardization or supercell construction. Exactly
one periodic 3D five-atom structure with full occupancy is required; invalid CIFs,
disorder and malformed geometry are audited by source row and material ID.
The writer visits every row. It neither reads nor filters on scalar property
columns. Output `targets` is empty; clean positions/cell are the generation data.
The intended task is conditioned on composition and atom count.

The author's train/val/test assignments remain immutable (`val` becomes
`validation`). Duplicate material IDs and exact geometries crossing partitions
stop preparation for review, rather than being silently reassigned. Exact Cartesian
grouping is not a crystallographic equivalence check. Source and data hashes,
exclusions, actual counts, element coverage and the parser preparation source hash
are recorded in the audit. A dataset audit alone does not validate the subsequent
generation training or independent held-out sampling evaluation.
