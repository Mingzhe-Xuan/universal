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
