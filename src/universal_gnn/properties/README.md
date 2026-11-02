# Property catalog

The catalog describes output scope, units, dimensions, index order and response variables.
Responses default to Jacobian readout; fixed-frame components and equivariant backends are explicit.
Dataset column binding and target normalization are separate from the property definition. Unknown
names and incompatible labels fail, rather than silently selecting a different mathematical target.

## Per-configuration properties

`task.spec` defines a custom property with `scope`, `shape`, `unit`, `kind`, `reduction`,
and `construction`. The `task.property` string names its target; the engine selects
classification by `kind`, independently of this name. Example: `{"scope":"graph",
"shape":[3],"unit":"class","kind":"classification"}`. The full definition is saved
in checkpoints. A derivative response also declares `response_indices` and
`auxiliary_indices`, with full Cartesian shape `(3,)*rank`. No space-group mask is added.
Spectral tasks may explicitly request a finite-window Kramers-Kronig postprocess with
a positive increasing grid; derived epsilon1 is never treated as another training label.
