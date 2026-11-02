# Custom extensions

`custom_knn_gcn/` is an executable directory plugin containing an independent molecular KNN
builder and a minimal GCN. Copy the directory to implement another graph builder/GNN.
Both are wrapped by `StandardBackbone`; downstream readouts remain framework-owned.
See [the single format/interface standard](../docs/standards.md).
