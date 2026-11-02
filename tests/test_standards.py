from dataclasses import replace
import json
import os
import py_compile

import pytest
import torch

from universal_gnn.contracts import GraphRecord
from universal_gnn.contracts.plugins import load_plugin
from universal_gnn.data.formats import save_structures
from universal_gnn.data.structures import load_structures
from universal_gnn.engine.configuration import load_config, resolve_config
from universal_gnn.engine.training import build_model

from test_graph_extensions import molecules


def test_canonical_dataset_import_roundtrip_and_bounding_cell(tmp_path):
    structures = molecules()
    structures[0] = replace(structures[0], graph=GraphRecord(torch.tensor([[0, 1], [1, 0]]),
                                     node_features=torch.ones(3, 2, dtype=torch.float64)))
    path = tmp_path / "molecules.json"
    save_structures(path, structures, metadata={"unit": "angstrom"})
    records = load_structures(path)
    torch.testing.assert_close(records[0].graph.edge_index, structures[0].graph.edge_index)
    torch.testing.assert_close(records[0].graph.node_features, structures[0].graph.node_features)
    payload = json.loads(path.read_text())
    del payload["structures"][0]["cell"]
    path.write_text(json.dumps(payload))
    records = load_structures(path)
    torch.testing.assert_close(records[0].positions, structures[0].positions)
    assert float(torch.linalg.det(records[0].cell)) > 0
    payload["structures"][1]["id"] = payload["structures"][0]["id"]
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="unique ids"):
        load_structures(path)


def test_empty_imported_graph_roundtrip_preserves_feature_width(tmp_path):
    structure = molecules()[1]
    graph = GraphRecord(torch.empty(2, 0, dtype=torch.long), torch.empty(0, 3, dtype=torch.long),
                        edge_features=torch.empty(0, 4, dtype=torch.float64))
    path = tmp_path / "empty-edges.json"
    save_structures(path, [replace(structure, graph=graph)])
    restored = load_structures(path)[0].graph
    assert restored.edge_index.shape == (2, 0) and restored.cell_shifts.shape == (0, 3)
    assert restored.edge_features.shape == (0, 4)


def test_standard_fields_do_not_silently_apply_legacy_aliases(tmp_path):
    path = tmp_path / "standard.json"
    save_structures(path, molecules())
    payload = json.loads(path.read_text())
    del payload["structures"][0]["targets"]
    path.write_text(json.dumps(payload))
    assert load_structures(path)[0].targets == {}
    payload["structures"][0]["cartesian"] = False
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="legacy geometry aliases"):
        load_structures(path)
    del payload["structures"][0]["cartesian"]
    payload["structures"][0]["graph"] = {"edge_index": [[0], [1]], "edge_attr": [[1.]]}
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="Unknown graph fields"):
        load_structures(path)
    path.write_text(json.dumps([{"id":"legacy", "atoms":{"elements":["H"],"coords":[[.1,.2,.3]],
                      "cartesian":False,"lattice_mat":[[2.,0.,0.],[0.,2.,0.],[0.,0.,2.]]}}]))
    torch.testing.assert_close(load_structures(path)[0].positions,
                               torch.tensor([[.2,.4,.6]], dtype=torch.float64))


@pytest.mark.parametrize("version", [2, None, True])
def test_unknown_dataset_and_config_versions_fail_closed(tmp_path, version):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"schema_version": version, "structures": []}))
    with pytest.raises(ValueError, match="schema version"):
        load_structures(path)
    path.write_text(json.dumps({"schema_version": version}))
    with pytest.raises(ValueError, match="schema version"):
        load_config(path)


def test_graph_configuration_not_silently_ignored():
    config = {"backbone": {"name": "alignn"}, "graph": {"name": "knn"},
              "task": {"kind": "supervised", "property": "bandgap"}}
    with pytest.raises(ValueError, match="original graph preprocessing"):
        build_model(config)
    result = resolve_config({"backbone": {"name": "gcn"}, "graph": {"name": "knn", "k": 2},
                             "dataset": {"path": "data.json"}, "task": {"kind": "supervised", "property": "bandgap"}},
                            graph="stored")
    assert result["graph"] == {"name": "stored"}


def test_plugin_source_matches_fingerprint_despite_stale_bytecode(tmp_path):
    helper = tmp_path / "helper.py"
    helper.write_text("VALUE=1\n")
    (tmp_path / "plugin.py").write_text("from .helper import VALUE\n")
    py_compile.compile(str(helper), doraise=True)
    timestamp = helper.stat()
    first = load_plugin(tmp_path)
    helper.write_text("VALUE=2\n")
    os.utime(helper, ns=(timestamp.st_atime_ns, timestamp.st_mtime_ns))
    second = load_plugin(tmp_path)
    assert first.VALUE == 1 and second.VALUE == 2
    assert first.__ugnn_provenance__["source_sha256"] != second.__ugnn_provenance__["source_sha256"]
