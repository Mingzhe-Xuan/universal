# Complete rMD17 ethanol preparation

`source.py` pins the four author files from Figshare article12672038 version4,
including the complete67,201,791-byte ethanol NPZ. It verifies size, SHA256 and
MD5 before and after conversion. Full array inspection imports NumPy inside
Slurm and requires all seven original arrays,100000 unique original frame
indices, finite coordinates/labels and the original nine-atom composition.

`conversion.py` writes dataset-v1 `structures.jsonl`, `split.json`, `audit.json`
and a stage/status `report.json`. A failed or partial run has no successful
audit. Existing output files are never overwritten. All100000 frames remain,
including finite zero labels; there is no atom, magnitude, first-N or geometry
selection. Coordinates remain Cartesian angstroms, unwrapped and uncentered.
PBC is explicitly false on all axes. The identity cell is only a nonsingular
schema placeholder and must not be used for periodic neighbors or wrapping.

Energy and force labels use the revised `energies` and `forces` arrays only.
Old MD17 labels are inspected as source fields but never become targets.
Thermochemical kcal/mol becomes total eV per structure; kcal/mol/angstrom
becomes eV/angstrom with the same positive factor, without changing the force
sign or dividing energy by atom count. The factor uses4184 J/kcal and the exact
SI2019 elementary charge and Avogadro constant. See the
[NIST SI definitions](https://www.nist.gov/si-redefinition/definitions-si-base-units)
and [thermochemical calorie convention](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8).
There are no stress labels or supervised stress claim.

`partitions.py` keeps the first author1000-frame development pool. Exactly100
validation frames are selected by the fixed namespace/ID SHA256 order; the
other900 are training. Training RNG and labels do not participate in selection.
All99000 remaining frames form the full heldout pool. The original1000 author
test indices also remain a separately identified `evaluation_cohorts.official_test_01`
within that pool, with their released order. Report both cohorts explicitly.
This900/100/99000 protocol is UGNN's declared supplement, not the author's1000
training benchmark. Exact Cartesian duplicate geometries across assigned roles
stop preparation rather than being silently moved or dropped.

The source is a correlated MD trajectory. The
[authors warn against fitting more than1000 frames](https://figshare.com/articles/dataset/Revised_MD17_dataset_rMD17_/12672038).
The manifest therefore does not claim independent trajectories, new-molecule
generalization, or removal of time correlation. Different training seeds would
not change this frozen data split; this campaign trains only seed123.

Run on a clean pinned checkout, using an environment with NumPy:

```bash
python scripts/prepare_rmd17.py \
  --raw data/arxiv-v1/molecular-rmd17-v4/raw \
  --output data/arxiv-v1/rmd17-ethanol-prepared-NEW
```

The CLI and full preparation API require `SLURM_JOB_ID`. The pure record and
partition helpers can be tested without NumPy, Torch or any original GNN package.
Data conversion does not certify a molecular model profile, graph, gradients,
capacity, training or scientific evaluation. CGCNN/ALIGNN still need explicit
nonperiodic input profiles and their own numerical acceptance.
