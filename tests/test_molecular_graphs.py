"""Closed graph scopes and synthetic row streams; actual native inputs run only in Slurm."""

import ast
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_arxiv_experiment_definitions import registry_fixture
from test_molecular_experiment_definitions import input_fixture
from universal_gnn.benchmarks.experiments.recipes import build_matrix
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.molecular import contracts, definitions, graphs
from universal_gnn.benchmarks.molecular.source import COUNTS, SOURCE_SHA


ROOT = Path(__file__).resolve().parents[1]


class MolecularGraphContractTests(unittest.TestCase):
    def setUp(self):
        self.primary = build_matrix(registry_fixture())
        self.patch = patch.object(definitions, "PRIMARY_SHA", canonical_digest(self.primary))
        self.patch.start();self.addCleanup(self.patch.stop)
        self.definitions = definitions.build_molecular_definitions(self.primary, input_fixture(), repository=ROOT)

    def spec(self, model="cgcnn"):
        return contracts.molecular_group_spec(self.primary, self.definitions, model, repository=ROOT)

    def report(self, model="cgcnn", device="cpu"):
        result = dict(version=1, kind="complete_molecular_native_graph_scan", status="complete", model=model,
            definition_sha256=contracts.DEFINITION_SHA, source_sha256=SOURCE_SHA, counts=dict(COUNTS),
            source_structures=100000, training_structures=900, complete_source_scan=True, complete_training_scan=True,
            no_periodic_images=True, model_forward_executed=False, model_state_unchanged=True,
            numerical_capacity_acceptance=False, formal_training_runs=0, dtype="float32", device=device,
            cuda_input_graph_validation=device.startswith("cuda"),
            native_edge_kind="padded_neighbor_slots" if model=="cgcnn" else "directed_edges")
        result.update({k:"4"*64 for k in ["source_graph_rows_sha256","training_graph_rows_sha256","probe_sha256",
            "graph_definition_sha256","model_state_before_sha256","model_state_after_sha256"]})
        return result

    def test_five_exact_groups_keep_four_pairs_and_single_plugin(self):
        before=copy.deepcopy(self.definitions)
        for model in contracts.MODELS:
            spec=self.spec(model)
            self.assertEqual(spec["model"],model)
            self.assertEqual(spec["counts"],COUNTS)
            self.assertEqual(spec["source_structures"],100000)
            self.assertEqual(set(spec["configs"]),{"scratch"} if model=="custom_knn_gcn" else {"pretrained","scratch"})
            self.assertEqual(spec["reference_mode"],"scratch" if model=="custom_knn_gcn" else "pretrained")
            spec["reference_config"]["seed"]=999
            self.assertEqual(spec["configs"][spec["reference_mode"]]["seed"],123)
        self.assertEqual(before,self.definitions)

    def test_unknown_group_and_any_mixed_definition_change_refused(self):
        with self.assertRaises(ValueError):self.spec("gcn")
        for key,value in [("defined_training_runs",8),("training_seeds",[123,456])]:
            bad=copy.deepcopy(self.definitions);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                contracts.molecular_group_spec(self.primary,bad,"mace",repository=ROOT)
        bad=copy.deepcopy(self.definitions);bad["cases"][-1]["config"]["graph"]["k"]=3
        with self.assertRaises(ValueError):contracts.molecular_group_spec(self.primary,bad,"mace",repository=ROOT)

    def test_old_plugin_source_version_cannot_be_relabelled_as_current(self):
        bad=copy.deepcopy(self.definitions)
        name="examples/custom_knn_gcn/model.py"
        old=subprocess.check_output(["git","show","1e19447:"+name])
        bad["cases"][-1]["plugin"]["source_sha256"][name]=hashlib.sha256(old).hexdigest()
        with self.assertRaises(ValueError):contracts.molecular_group_spec(self.primary,bad,"custom_knn_gcn",repository=ROOT)

    def test_cpu_and_cuda_metadata_remain_distinct_and_neither_is_capacity(self):
        for model in contracts.MODELS:
            spec=self.spec(model)
            contracts.checked_graph_metadata(self.report(model),spec)
            with self.assertRaises(ValueError):contracts.checked_graph_metadata(self.report(model),spec,require_cuda=True)
            contracts.checked_graph_metadata(self.report(model,"cuda:0"),spec,require_cuda=True)

    def test_incomplete_wrong_device_forward_or_changed_model_metadata_refused(self):
        changes=[("status","running"),("source_structures",99999),("source_structures",100000.),("training_structures",899),
            ("complete_source_scan",False),("complete_training_scan",False),("no_periodic_images",False),
            ("model_forward_executed",True),("model_state_unchanged",False),("numerical_capacity_acceptance",True),
            ("formal_training_runs",1),("dtype","float64"),("device","mps"),("cuda_input_graph_validation",True),
            ("native_edge_kind","directed_edges"),("probe_sha256","unknown"),("model_state_after_sha256","5"*64)]
        for key,value in changes:
            report=self.report();report[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):contracts.checked_graph_metadata(report,self.spec())

    def test_no_slurm_refuses_before_definitions_or_torch_import(self):
        environment={k:v for k,v in os.environ.items() if k!="SLURM_JOB_ID"}
        with patch.dict(os.environ,environment,clear=True),patch.object(graphs,"selected_group") as selected:
            with self.assertRaises(RuntimeError):graphs.scan_molecular_graphs("cgcnn","unused-no-slurm")
            selected.assert_not_called()

    def test_module_imports_require_no_numerical_packages(self):
        code="import sys;sys.path.insert(0,'src');import universal_gnn.benchmarks.molecular.graphs;assert 'torch' not in sys.modules and 'numpy' not in sys.modules"
        subprocess.run([sys.executable,"-S","-c",code],cwd=ROOT,check=True)

    def test_plugin_capability_update_changes_no_other_constructor_or_forward_ast(self):
        name="examples/custom_knn_gcn/model.py"
        old=ast.parse(subprocess.check_output(["git","show","1e19447:"+name]).decode())
        new=ast.parse((ROOT/name).read_text(encoding="utf8"))
        found=[]
        for node in ast.walk(new):
            if isinstance(node,ast.Call):
                for kw in list(node.keywords):
                    if kw.arg=="gradient_capabilities":
                        self.assertEqual(ast.literal_eval(kw.value),dict(positions=True,strain=True,mixed=True))
                        node.keywords.remove(kw);found.append(kw)
        self.assertEqual(len(found),1)
        self.assertEqual(ast.dump(old),ast.dump(new))


class MolecularGraphRowsTests(unittest.TestCase):
    def setUp(self):
        self.source=[SimpleNamespace(identifier="frame"+str(i)) for i in range(3)]
        self.records=[dict(id=s.identifier) for s in self.source]

    def counts(self,structure):
        return dict(atoms=9,native_edges=72,native_triplets=0,auxiliary_edges=0,maximum_degree=8,valid_directed_edges=72)

    def test_complete_source_and_noncontiguous_train_indices_preserve_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            result=graphs.write_graph_rows(self.source,self.records,[0,2],self.counts,root/"all.jsonl",root/"train.jsonl")
            self.assertEqual((result["source_structures"],result["training_structures"]),(3,2))
            self.assertEqual(result["source_sums"]["native_edges"],216)
            rows=[json.loads(x) for x in (root/"train.jsonl").read_text().splitlines()]
            self.assertEqual([(r["index"],r["source_index"],r["id"]) for r in rows],[(0,0,"frame0"),(1,2,"frame2")])
            self.assertEqual(len((root/"all.jsonl").read_text().splitlines()),3)

    def test_bad_training_indices_counts_and_identity_keep_no_successful_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for i,indices in enumerate([[],[2,0],[0,0],[True],[3],["0"]]):
                with self.subTest(indices=indices),self.assertRaises(ValueError):
                    graphs.write_graph_rows(self.source,self.records,indices,self.counts,root/(str(i)+"a"),root/(str(i)+"t"))
            for i,(key,value) in enumerate([("atoms",True),("native_edges",1.2),("maximum_degree",0),("valid_directed_edges",73),
                                          ("native_edges",0),("native_triplets",-1)]):
                def counter(structure):
                    result=self.counts(structure);result[key]=value;return result
                with self.subTest(key=key),self.assertRaises(ValueError):
                    graphs.write_graph_rows(self.source,self.records,[0,2],counter,root/("c"+str(i)),root/("t"+str(i)))
            wrong=list(self.source);wrong[1]=SimpleNamespace(identifier="wrong")
            with self.assertRaises(ValueError):graphs.write_graph_rows(wrong,self.records,[0,2],self.counts,root/"prefix",root/"train-prefix")
            self.assertEqual(len((root/"prefix").read_text().splitlines()),1)
            self.assertEqual(len((root/"train-prefix").read_text().splitlines()),1)

    def test_valid_edges_are_distinct_from_padding_and_gzip_is_lossless_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            def counter(structure):
                result=self.counts(structure);result["native_edges"]=108;return result
            graphs.write_graph_rows(self.source,self.records,[0,2],counter,root/"all.jsonl",root/"train.jsonl")
            row=json.loads((root/"all.jsonl").read_text().splitlines()[0])
            self.assertEqual((row["valid_directed_edges"],row["native_edges"]),(72,108))
            original=(root/"all.jsonl").read_bytes();(root/"copy.jsonl").write_bytes(original)
            first=graphs._compress(root/"all.jsonl");second=graphs._compress(root/"copy.jsonl")
            self.assertEqual(first["sha256"],second["sha256"])
            self.assertEqual(gzip.decompress(Path(first["path"]).read_bytes()),original)
            self.assertEqual(first["raw_sha256"],hashlib.sha256(original).hexdigest())
            with self.assertRaises(FileExistsError):graphs._compress(root/"all.jsonl")


if __name__=="__main__":unittest.main()
