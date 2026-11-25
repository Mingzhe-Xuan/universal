# Original QM9 four scalar labels

`prepare_qm9(raw_directory, output)` runs in CPU Slurm. It checks the author's
Figshare archive, readme and 3054-item exclusion list against released byte sizes
and MD5 values, retaining their SHA256 identities. It reads XYZ members directly
without extracting paths or requiring RDKit. All 133885 source IDs must appear
exactly once; all 130831 characterized molecules are retained, including zeros.

Output is standard `structures.jsonl`, `split.json` and `report.json`. Positions
remain angstroms, PBC is false, and the identity cell is a placeholder. Targets:
`homo`/`lumo` in eV (27.211386245988 eV/Hartree), `dipole_magnitude` in Debye,
`isotropic_polarizability` in Bohr^3. These are four direct invariant scalars,
not dipole vectors, polarizability tensors, orbital wavefunctions or derivatives.

The fixed seed0 original-SMILES grouped hash split uses all clean molecules and
requested 80/10/10 group proportions. Its actual counts are recorded. It is a new
UGNN split, not an author split; training seed123 never selects the partitions.
Every task/model uses the same source and split. No new DFT is performed.

Author data: <https://doi.org/10.6084/m9.figshare.c.978904.v5>.
Run `PYTHONPATH=src python scripts/run_qm9.py prepare --raw data/qm9/raw
--data data/qm9/prepared-v1` in a CPU Slurm allocation.

## Frozen HOMO/LUMO 12k subset

`subset.py:prepare_subset(parent_directory, output)` selects exactly10000train,
1000validation and1000test from their respective already-separated parent pools.
It orders whole original-SMILES groups by a fixed namespace hash, never by labels
or training RNG. Original row bytes, IDs, coordinates, labels and memberships are
retained; unused parent rows stay in the immutable complete source. A count that
cannot be reached without splitting groups fails. Output retains parent source,
manifest and report SHA, selected original indices, new source/split SHA and a
clear subset interpretation. Run via `run_qm9.py subset` in CPU Slurm.
