# Readouts

`PropertyReadout` consumes only `NativeFeatures` and `PropertySpec`. Scalar, class and spectrum
outputs use invariant channels and declared node/graph reduction. `ResponseReadout` constructs a
response linear in a live auxiliary field, then obtains the Cartesian target by autograd Jacobian.
It uses tensor-product coupling for equivariant features and explicit fixed-frame coefficients for
invariant features; these guarantees are not interchangeable. Jacobian training retains parameter
gradients. No crystal symmetry masks or extra tensor index symmetries are imposed.
