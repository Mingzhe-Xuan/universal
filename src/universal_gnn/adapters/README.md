# Feature adapters

`ScalarAdapter` projects even scalar channels and invariant norms to a fixed node width. It does
not promise rotation-covariant Cartesian component predictions. `EquivariantAdapter` retains
native irreps and adds learned geometric moments/couplings where requested; output irreps are
fixed by the profile. Node pooling is reserved for readouts.

Geometry lifting uses independent moment channels: a vector crossed with itself is not an axial
feature. Model/adapter/head weights train separately by default, and equal dimensions do not imply
cross-backbone checkpoint alignment. No crystal point-group masks or component projections apply.

Geometry basis v2 adds `2e x 2e -> 1e/3e`, `2e x 3o -> 2o`, and `2e x 2o -> 0o` paths.
Polar moments vanish at nonpolar sites even when axial or odd tensor modes are allowed. Independent
quadrupoles and octupoles retain such modes; just crossing polar moments can remove them. Tests
cover a centrosymmetric axial Born response and a nonpolar D2d odd quadrupole, as well as O(3)
transformation and geometric gradients. These checks do not prove universal expressivity for every
finite-cutoff environment. They impose no site/crystal symmetry masks.

New training uses basis v2. Checkpoint format 2 records the reconstruction convention; checkpoints
without a format marker retain basis v1. `task.adapter_version=1` explicitly selects the old basis.
Native profile dimensions stay the same; checkpoint replay, rather than shape alone, verifies
compatibility. Historical acceptance records retain their original source version.
