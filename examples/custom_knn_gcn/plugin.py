from .graph import MolecularKNN
from .model import MolecularGCN


def build_gnn(**options):
    return MolecularGCN(**options)


def build_graph_builder(**options):
    return MolecularKNN(**options)
