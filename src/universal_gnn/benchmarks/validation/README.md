# Derivative and geometry acceptance

`validate_derivatives(model, structures, config)` checks the configured response
or force-field model on two real records at its actual dtype/device. It trains
nothing and changes no capability metadata. Run numerical work through Slurm.

It returns `passed`, per-check tolerances/errors, mixed parameter-gradient norms
and finite-difference observations. Force fields check energy derivatives for
positions/strain, net force, translations/rotations and separate/batched evaluation
in both actual training and evaluation modes. Response tensors compare the actual
auxiliary-field derivative against independent central differences, with no
symmetry projection. Equivariant Cartesian outputs must transform as declared;
fixed-frame invariant baselines record covariance error without promising it.
Graph responses may have rank2,3 or4 with full Cartesian3x3,3x3x3 or3x3x3x3
outputs. Rotation acts separately on every Cartesian slot; O(3) inversion is
even for ranks2/4 and odd for rank3. These checks never average, symmetrize or
project a tensor. Existing rank2 rotation arithmetic and check names are retained.
`cartesian.py` defines the shape/rank and independent-axis contraction protocol
without importing Torch. Live high-rank checks and deliberately wrong symmetry,
parity and derivative cases are in `tests/test_high_rank_task_validation.py`.
Force/strain finite differences use the predeclared decreasing steps
0.002,0.001,0.0005,0.00025,0.000125. Each requires two adjacent estimates to match
the analytic result and each other at the original rtol0.02/atol0.002; the largest
convergent pair is retained, with all attempts recorded. This tests local behavior
when large steps can cross a discrete neighbor-selection boundary; a single
accidental agreement is rejected. Force and strain can require different steps. Nothing
changes the original graph, weights or training precision. Analytic/mixed derivatives
and all geometry/batch checks use the live model's dtype. Independent force/strain
energy differences use a float64 deep copy with the exact same parameter values
and the already selected input coordinates promoted to float64; existing float64
models need no copy. This prevents cancellation of small energy increments while
still checking the actual float32 analytic forces/stress against the original
tolerances and adjacent-step convergence. Both dtypes are recorded. The live
model's parameters, buffers and dtype are preserved. `precision.py` also synchronizes
the reference copy's explicit output dtype for the three known official NequIP
embedding classes; their ordinary `.double()` leaves that Python attribute unchanged.
This is confined to the reference copy and recorded per module, with no original
backbone, live dtype, graph or normalization changes. Other providers' attributes
are left alone. The pure control is
in `finite_difference.py`. These checks do not replace all-training-graph scans
or CUDA capacity preflights.

Use `scripts/validate_task_derivatives.py --config CONFIG --output NEW_JSON`
inside a Slurm allocation with the provider's environment. The CLI fits native
scratch neighbor statistics only on the selected training partition when needed,
builds the actual configured model and writes a separate receipt. Pipeline callers
can prepare those statistics once and pass their model/data directly.


Rank3/4 source d6f2ddb passed actual CPU1229:105 main tests/509 JUnit counts,
no failures/errors/skips, eight live higher-tensor reports covering fixed-frame
and equivariant processing at float32/float64, and eight executed Git blobs.
The suite includes independent explicit Cartesian-index rotation oracles and
wrong covariance/parity/derivative injections, plus original physical, finite
difference, energy and heldout regressions. CPU1230 retained the exact successful
control terminal/request/source binding. Evidence is under ignored
`results/paper-high-rank-validation-20261105/1229/`. These are small-model
validator checks; official full-data graph/capacity/physical gates remain separate.
