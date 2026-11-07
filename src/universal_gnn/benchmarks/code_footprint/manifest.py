"""Disjoint, explicit boundaries for the paper's adapter source inventory."""

GROUPS = {
    "shared_contracts": ("src/universal_gnn/contracts/",),
    "shared_feature_adapters": ("src/universal_gnn/adapters/",),
    "shared_readouts": ("src/universal_gnn/readouts/",),
    "shared_property_definitions": ("src/universal_gnn/properties/",),
    "shared_task_wrappers": ("src/universal_gnn/tasks/",),
    "shared_training_inference_generation": ("src/universal_gnn/engine/",),
    "shared_backbone_infrastructure": (
        "src/universal_gnn/backbones/__init__.py",
        "src/universal_gnn/backbones/factory.py",
        "src/universal_gnn/backbones/standard.py",
        "src/universal_gnn/backbones/blueprints.py",
        "src/universal_gnn/backbones/initialization.py",
        "src/universal_gnn/backbones/native.py",
        "src/universal_gnn/backbones/official/__init__.py",
        "src/universal_gnn/backbones/official/base.py",
        "src/universal_gnn/backbones/official/profiles.py",
        "src/universal_gnn/backbones/official/reference.py",
        "src/universal_gnn/backbones/official/native_heads.py",
        "src/universal_gnn/backbones/official/checkpoint_graph.py",
        "src/universal_gnn/backbones/official/molecular/__init__.py",
        "src/universal_gnn/backbones/official/molecular/profiles.py",
        "src/universal_gnn/backbones/official/molecular/geometry.py",
    ),
    "cgcnn_adapter": (
        "src/universal_gnn/backbones/official/cgcnn.py",
        "src/universal_gnn/backbones/official/molecular/cgcnn.py",
    ),
    "alignn_adapter": (
        "src/universal_gnn/backbones/official/alignn.py",
        "src/universal_gnn/backbones/official/molecular/alignn.py",
    ),
    "mace_adapter": ("src/universal_gnn/backbones/official/mace.py",),
    "nequip_adapter": ("src/universal_gnn/backbones/official/nequip.py",),
    "custom_knn_gcn_plugin": ("examples/custom_knn_gcn/",),
    "custom_knn_gcn_configuration": ("configs/custom_knn_gcn.yaml",),
}

POLICY = {
    "version": 1,
    "directory_selection": "Recursive tracked .py files only; exact file selectors also allow JSON/YAML configuration.",
    "bytes": "Exact committed Git blob bytes, independent of working-tree line endings or edits.",
    "physical_lines": "UTF-8 decoded splitlines count; includes blank lines, comments and docstrings.",
    "nonblank_lines": "Physical lines whose stripped text is nonempty; includes comments and docstrings.",
    "python_statement_nodes": "Number of ast.stmt nodes, including compound statements, definitions and docstring expression statements; configuration files contribute zero.",
    "aggregation": "Groups must be disjoint; totals count each selected path once. Identical contents at distinct paths remain separate files.",
    "exclusions": "Upstream installed model packages, nonselected model adapters, graph/data services, experiment machinery, tests, docs and generated data/results are outside this inventory; every unselected tracked path is listed.",
    "interpretation": "A source-size snapshot of declared implementation boundaries, not marginal/minimum code to add a property, developer effort, a whole-project total or a performance measure. Shared infrastructure is not allocated repeatedly to individual tasks. The plugin includes its model, graph builder and registration; its configuration is separate.",
}
