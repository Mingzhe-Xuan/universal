# Tasks

`SupervisedModel` selects a direct or response readout from the explicit property spec.
`ForceFieldModel` predicts per-node scalar energies and differentiates their sum with respect to
live Cartesian positions and a common affine strain of positions/cell. Stress is tensile-positive
`dE/dstrain / volume`, returned in GPa; source labels must be converted explicitly by data bindings.
Inference must retain input autograd for derivative tasks, even in evaluation mode.
