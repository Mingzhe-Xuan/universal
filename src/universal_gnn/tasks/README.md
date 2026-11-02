# Tasks

`SupervisedModel` selects a direct or response readout from the explicit property spec.
`ForceFieldModel` predicts per-node scalar energies and differentiates their sum with respect to
live Cartesian positions and a common affine strain of positions/cell. Stress is tensile-positive
`dE/dstrain / volume`, returned in GPa; source labels must be converted explicitly by data bindings.
Inference must retain input autograd for derivative tasks, even in evaluation mode.
# Fixed-composition generation

`PeriodicDenoiser` accepts a backbone with `context_dim=22`: sixteen time channels plus six
rotation-invariant log-Cholesky cell coordinates. It predicts a scaled periodic fractional score
and six Gaussian cell scores. Invariant encoders use geometry-weighted directional messages;
equivariant encoders use native polar-vector channels. Coordinate scores transform as covectors.
The shared annealed Langevin sampler preserves species/counts and wraps fractional positions.
Cell bounds are explicit numerical sampling constraints, not symmetry constraints. Generated
samples discard template physical labels. This implementation is not yet trained or accepted.
