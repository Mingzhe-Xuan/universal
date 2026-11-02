# Backbones

All encoders return unpooled `NativeFeatures`. Scalar context is projected into the initial node
embedding, before message passing, for diffusion/conditional tasks. Geometry is computed live.

`CGCNNEncoder`, `MEGNetEncoder`, and `ALIGNNEncoder` implement their respective gated graph,
node/edge/global graph-network, and alternating crystal/line-graph architectures in native Torch.
LayerNorm replaces batch-wide normalization to keep independent structures isolated; smooth
cutoff weights replace abrupt neighbor truncation. These are explicitly recorded implementation
variants, not checkpoint-compatible copies of the original packages. Element embeddings are learned.
`MACEEncoder` uses official MACE interaction/product blocks; `NequIPEncoder` uses the official
embedding/convolution stack before its scalar-only final block. Version/layout mismatch fails.
`EquiformerEncoder` implements the dot-product-attention architecture variant with spherical
tensor-product key/values, invariant attention, equivariant feedforward, a single head and smooth
cutoffs. It is a documented Torch/e3nn reimplementation, not the original OCP checkpoint format.
None of the equivariant backends are substituted with an invariant encoder. All six passed the recorded ten-structure training/inference matrix; this is execution
acceptance and does not imply original-package checkpoint compatibility or benchmark accuracy.

Sources: [MACE](https://github.com/ACEsuit/mace), [NequIP](https://github.com/mir-group/nequip),
[Equiformer dot-product variant](https://github.com/atomicarchitects/equiformer/blob/master/nets/dp_attention_transformer.py),
[CGCNN](https://github.com/txie-93/cgcnn), [MEGNet](https://github.com/materialyzeai/megnet),
[ALIGNN](https://github.com/atomgptlab/alignn).
