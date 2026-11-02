"""abTEM multislice STEM from model-generated MD snapshots."""

import importlib.metadata

import numpy as np


def frozen_phonon_stem(frames, *, gpts=64, scan_gpts=8, energy_eV=200000.,
                       semiangle_mrad=20., inner_mrad=25., outer_mrad=60.):
    """Finite clusters in one common orthogonal vacuum box; no implicit lattice strain.

    Frames are correlated MD samples. This short execution preset is not a converged
    thermal ensemble or a periodic slab calculation.
    """
    import abtem

    if not frames or gpts < 16 or scan_gpts < 2:
        raise ValueError("Need snapshots and valid potential/scan grid sizes")
    if any(not np.array_equal(a.numbers, frames[0].numbers) for a in frames):
        raise ValueError("Frozen-phonon snapshots must preserve atom mapping")
    positions = np.concatenate([a.positions for a in frames])
    lower, upper = positions.min(0) - 3., positions.max(0) + 3.
    box = upper - lower
    wavelength_A = 12.2643 / np.sqrt(energy_eV * (1 + .97845e-6 * energy_eV))
    needed = 3 * max(box[:2]) * outer_mrad * 1e-3 / wavelength_A
    gpts = max(gpts, int(np.ceil(1.1 * needed / 32)) * 32)
    if gpts > 1024:
        raise ValueError("Requested detector requires a grid larger than this execution preset permits")
    images = []
    for frame in frames:
        atoms = frame.copy()
        atoms.positions -= lower
        atoms.set_cell(np.diag(box))
        atoms.pbc = False
        potential = abtem.Potential(atoms, gpts=gpts, slice_thickness=1., periodic=False,
                                    projection="finite", device="cpu")
        probe = abtem.Probe(energy=energy_eV, semiangle_cutoff=semiangle_mrad, device="cpu")
        probe.grid.match(potential)
        scan = abtem.GridScan(start=(0., 0.), end=tuple(box[:2]), gpts=scan_gpts, endpoint=False)
        detector = abtem.AnnularDetector(inner=inner_mrad, outer=outer_mrad)
        # Demand that requested angles are resolved by this potential grid.
        image = probe.scan(potential, scan=scan, detectors=detector, lazy=False).array
        image = np.asarray(image)
        if image.shape != (scan_gpts, scan_gpts) or not np.isfinite(image).all():
            raise FloatingPointError("Invalid multislice image")
        images.append(image)
    return np.mean(images, axis=0), {"backend": "abTEM", "backend_version": importlib.metadata.version("abtem"),
                                    "frames": len(frames),
                                    "specimen": "finite cluster with 3 angstrom vacuum",
                                    "box_A": box.tolist(), "potential_gpts": gpts,
                                    "scan_gpts": scan_gpts, "energy_eV": energy_eV,
                                    "semiangle_mrad": semiangle_mrad,
                                    "detector_mrad": [inner_mrad, outer_mrad],
                                    "ensemble": "correlated MLFF-MD snapshots, execution preset"}
