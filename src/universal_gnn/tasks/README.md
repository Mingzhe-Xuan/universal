# Tasks

`SupervisedModel` selects a direct or response readout from the explicit property spec.
`ForceFieldModel` predicts per-node scalar energies and differentiates their sum with respect to
live Cartesian positions and a common affine strain of positions/cell. Stress is tensile-positive
`dE/dstrain / volume`, returned in GPa; source labels must be converted explicitly by data bindings.
Inference must retain input autograd for derivative tasks, even in evaluation mode.

`supervision.py` separates training labels from computed outputs. Set
`task.supervised_outputs: [forces]` for force-only supervision, or select any nonempty subset of
total_energy/forces/stress. Omission retains the old E/F/S default. Only selected bindings, scales
and losses require labels; unknown/duplicate/empty selections fail configuration validation.
The model still derives forces from scalar energy, with mixed coordinate/parameter gradients.
Force-only labels do not determine energy constants or elemental reference energies; predicted
stress has no direct supervision. Inference still returns computed E/F/S. A complete optimizer
resume requires the same selected supervision, with list order ignored.
# Fixed-composition generation

`PeriodicDenoiser` accepts a backbone with `context_dim=22`: sixteen time channels plus six
rotation-invariant log-Cholesky cell coordinates. It predicts a scaled periodic fractional score
and six Gaussian cell scores. Invariant encoders use geometry-weighted directional messages;
equivariant encoders use native polar-vector channels. Coordinate scores transform as covectors.
The shared annealed Langevin sampler preserves species/counts and wraps fractional positions.
Cell bounds are explicit numerical sampling constraints, not symmetry constraints. Generated
samples discard template physical labels. Six built-in backbones passed ten-real-structure denoising training, checkpoint replay and sampling;
this verifies execution, not generative quality. See docs/agents/acceptance.md for evidence.

For higher geometric derivatives, pass a batch whose positions require gradients and set
create_graph=True. ForceFieldModel retains that external graph; evaluation defaults avoid
retaining the force Hessian unless explicitly requested.

## Prediction v1 composition

With prediction.version1, SupervisedModel composes native FeatureSpec, an explicitly selected
independent adapter (otherwise None), and a registered readout. ForceFieldModel requires node_mlp
with sum pooling and verified position/strain/mixed derivatives; it derives forces and stress from
atomic energy summation, preserving task.supervised_outputs selection. Legacy task.route and
adapter_version cannot be mixed with prediction. Omitting prediction keeps historical assembly.
