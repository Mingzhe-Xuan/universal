# Official pretrained backbones

This module is under implementation; implemented wrappers are not declared verified until the
published checkpoint and ten-real-structure Slurm fine-tuning evidence have been recorded.

Providers load the original architecture and all its parameters and buffers, and call the original
forward. No normalization, element encoding, interaction block, cutoff envelope or graph rule is
replaced to fit UGNN. Node features are exposed before native pooling/readout. Optional conditioning
is appended at the output adapter, outside the original backbone. Feature extraction retains the
input autograd graph, including when parameter training is disabled.

`OfficialBackbone` supplies NativeFeatures, provenance and exact source artifact hashes. Original
artifact bytes are embedded in UGNN checkpoints so reconstructing the model does not require the
original download path. Official serialization may require the corresponding pinned package/source
version. An unsupported provider fails explicitly and never falls back to a native architecture variant.

`ReferenceValue` preserves the original NumPy preprocessing values while differentiating a
mathematically equivalent Torch expression. It is only for differentiable geometry reconstruction;
official model layers and forward values remain unchanged. Topology remains the official discrete
topology, so derivatives are piecewise on a fixed neighbor list; global cutoff smoothness is not
silently changed. Providers must verify original input/feature/prediction parity and first/second
derivatives separately.
