# Data and differentiable geometry

Geometry uses `r_ij = positions[src] + image @ cell - positions[dst]` with row-vector cells.
`radius_graph` enumerates all periodic images within cutoff, including self images and multiple
images of the same pair in small cells. It does not silently impose a neighbor cap or minimum-image
approximation. Topology is discrete; displacements, distances, angles and strain are computed from
live tensors. Downloaded datasets and manifests belong in ignored `data/`, never Git.
`dfpt.py` reads matched final VASP geometry, electronic free energy, raw forces, tensile-positive
ASE stress, Born charges and electronic dielectric tensors. Born axes are retained, with no ASR
or space-group projection. Stress stays in ASE eV/angstrom^3 until an explicit GPa binding. The
batch preparation script runs through Slurm and verifies each published raw archive's SHA256.

## User dataset directories

Set `dataset.path` to `plugin:/absolute/directory` and optional `dataset.options` to a JSON object.
Implement `plugin.py:build_dataset(**options)` yielding nonempty `Structure` objects, with
atomic numbers, Cartesian angstrom coordinates, row-vector cell, PBC, ID, labels and provenance.
Relative imports inside the directory are supported. Standard target bindings still apply.
No edge features are required. Inference accepts the same `plugin:` path.

`prepare_raman_data.py` derives peak-normalized curves from CRD original tensors/frequencies
on 200 points from 50 to 1000 cm^-1, Lorentzian HWHM 5 cm^-1. It retains signed frequencies
and tensor provenance. This explicit preprocessing is not asserted identical to the paper.
`prepare_optical_data.py` uses the same published material XML for structure and TBmBJ
trace-average epsilon2, interpolated on 0.05 to 10 eV without extrapolation or sign clipping.
Run numerical data preparation through Slurm on Guqq2.

## Graph and dataset standard

`formats.save_structures` writes versioned canonical JSON; the reader supports it and legacy inputs.
Molecule JSON may omit cell only with explicit nonperiodic flags. GraphRecord supports imported local
indices/shifts and optional node/edge features. `graphs.py` independently selects KNN, radius, stored
or a BaseGraphBuilder directory plugin; stored graphs are offset without changing atom order.
The authoritative input/output and file specification is [docs/standards.md](../../../docs/standards.md).

The newly agreed default for non-official graph profiles is a 6-angstrom radius
graph, with periodic images determined per structure and axis by its PBC flags.
Molecules use all-false PBC and zero shifts; no neighbor cap or KNN fallback is
implicit. Official preprocessing retains its original defaults. This is a planned
default change: current omitted-graph assembly still selects KNN, and the radius
class default remains 4 angstrom. Set `graph: {name: radius, cutoff: 6.0}` explicitly
for standard wrapped GNNs until the versioned default transition is implemented.

## Indexed large inputs

`indexed.open_structures` selects `JSONLStructures` for JSONL files. It scans bytes for offsets,
source hash and standard-record ID uniqueness, then parses individual records using the same
validator as JSON. `SelectedStructures` lazily applies subsets and target bindings. JSON/ASE and
legacy iterable dataset plugins currently use their existing eager path. See engine/README.md
for full-data defaults, deterministic selection and batch memory limits.
