# Feature adapters

`ScalarAdapter` projects even scalar channels and invariant norms to a fixed node width. It does
not promise rotation-covariant Cartesian component predictions. `EquivariantAdapter` retains
native irreps and adds learned geometric moments/couplings where requested; output irreps are
fixed by the profile. Node pooling is reserved for readouts.

Geometry lifting uses independent moment channels: a vector crossed with itself is not an axial
feature. Model/adapter/head weights train separately by default, and equal dimensions do not imply
cross-backbone checkpoint alignment. No crystal point-group masks or component projections apply.
