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
These checks do not replace all-training-graph scans or CUDA capacity preflights.

Use `scripts/validate_task_derivatives.py --config CONFIG --output NEW_JSON`
inside a Slurm allocation with the provider's environment. The CLI fits native
scratch neighbor statistics only on the selected training partition when needed,
builds the actual configured model and writes a separate receipt. Pipeline callers
can prepare those statistics once and pass their model/data directly.
