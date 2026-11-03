# Readouts

`PropertyReadout` consumes only `NativeFeatures` and `PropertySpec`. Scalar, class and spectrum
outputs use invariant channels and declared node/graph reduction. `ResponseReadout` constructs a
response linear in a live auxiliary field, then obtains the Cartesian target by autograd Jacobian.
It uses tensor-product coupling for equivariant features and explicit fixed-frame coefficients for
invariant features; these guarantees are not interchangeable. Jacobian training retains parameter
gradients. No crystal symmetry masks or extra tensor index symmetries are imposed.

## Explicit native-feature readouts

`configuration.py` validates prediction.version1 and resolves defaults; `factory.py` owns registry,
optional feature processing and output contracts. `linear` and `graph_mlp` pool native nodes before
their network; `node_mlp` applies the network first. Native F is the first Linear input width.
`response` retains auxiliary-variable derivatives and requires explicit equivariant small_response
processing for Cartesian covariance; scalar inputs without it produce fixed-frame components.
No implicit choice depends on backbone.kind. Internal processing belongs to the readout component.
Register a custom factory `(settings, FeatureSpec, PropertySpec) -> nn.Module` through
`register_readout(name, factory, requirement=ReadoutRequirement(...), fields=(...))`; forward accepts
NativeFeatures and returns the declared property shape/dtype/device. Derivative factories also
accept create_graph. Register before config loading in every process. See docs/standards.md.
