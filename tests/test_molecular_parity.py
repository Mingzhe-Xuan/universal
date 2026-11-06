"""Pure adversarial metadata/recipe controls; never numerical parity evidence."""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.molecular.parity import contracts, runtime
from universal_gnn.benchmarks.molecular.source import COUNTS, SOURCE_SHA


def records():
    return [dict(id=f"ethanol-{i}", source_index=i) for i in range(900)]


def comparison(model):
    return dict(max_absolute_error=0., shape=[9,16], actual_sha256="a"*64, reference_sha256="a"*64,
                rtol=2e-5 if model=="mace" else 3e-5, atol=2e-6 if model=="mace" else 3e-6)


def rows(model):
    return [dict(index=i, **r, passed=True, no_periodic_images=True,
        comparisons={key:comparison(model) for key in contracts.expected_comparisons(model)}) for i,r in enumerate(records())]


def report(model="cgcnn"):
    official=model!="custom_knn_gcn"
    spec=dict(model=model,official=official,definition_sha256="d"*64)
    result=dict(version=1,kind="complete_molecular_same_state_reference",status="passed",stage="all_initializations_complete",model=model,
        definition_sha256=spec["definition_sha256"],source_sha256=SOURCE_SHA,counts=dict(COUNTS),
        source_structures=100000,training_structures=900,partition="train",device="cpu",dtype="float32",seed=123,
        formal_training_runs=0,formal_training_ready=False,cuda_capacity_acceptance=False,parameter_updates=0,
        original_package_parity_verified=official,direct_plugin_parity_verified=not official,initializations={})
    for mode in (["pretrained","scratch"] if official else ["scratch"]):
        item=dict(initialization=mode,structures=900,state_unchanged=True,reference_state_unchanged=True,
            maximum_absolute_errors={key:0. for key in contracts.expected_comparisons(model)},
            official=dict(initialization=mode,parameter_coverage=1. if mode=="pretrained" else 0.,
                buffer_coverage=1. if mode=="pretrained" else 0.,state_layout_verified=True) if official else None)
        item.update({key:"b"*64 for key in ["model_state_before_sha256","model_state_after_sha256",
            "reference_state_before_sha256","reference_state_after_sha256","native_reference_state_sha256","rows_sha256","config_sha256"]})
        result["initializations"][mode]=item
    return result,spec


class MolecularParityTests(unittest.TestCase):
    def test_native_energy_accumulation_preserves_float64_but_features_stay_float32(self):
        for name in ["native_head","native_energy","native_forces"]:
            for left,right in [("torch.float32","torch.float32"),("torch.float64","torch.float64"),("torch.float32","torch.float64")]:
                contracts.comparison_dtypes(name,left,right)
        contracts.comparison_dtypes("node_features","torch.float32","torch.float32")
        for name,left,right in [("node_features","torch.float64","torch.float32"),
                                ("node_features","torch.float32","torch.float64"),
                                ("native_energy","torch.float16","torch.float32"),
                                ("native_energy","torch.float32",None),("unknown","torch.float32","torch.float32")]:
            with self.assertRaises(ValueError):contracts.comparison_dtypes(name,left,right)
        values=rows("nequip");values[0]["comparisons"]["native_energy"].update(actual_dtype="torch.float64",reference_dtype="torch.float64")
        contracts.checked_rows(values,records(),"nequip")
        values[0]["comparisons"]["node_features"].update(actual_dtype="torch.float64",reference_dtype="torch.float32")
        with self.assertRaises(ValueError):contracts.checked_rows(values,records(),"nequip")

    def test_independent_edge_order_reconciliation_never_changes_or_duplicates_pairs(self):
        original=[[0,1],[1,0],[0,2],[2,0]]
        native=list(reversed(original))
        permutation=contracts.edge_permutation(original,native,3)
        self.assertEqual([original[i] for i in permutation],native)
        for left,right in [(original,original[:-1]),(original,original[:-1]+[[1,2]]),
                           (original,original[:-1]+[original[0]]),([[False,1]],[[0,1]]),
                           ([[0,0]],[[0,0]]),([[0,3]],[[0,3]])]:
            with self.assertRaises(ValueError):contracts.edge_permutation(left,right,3)

    def test_plugin_cache_relocation_preserves_exact_source_files_factory_and_origin(self):
        previous="a"*40;current="b"*40
        old="/task/runs/source-checkouts/"+previous;new="/task/runs/source-checkouts/"+current
        expected={role:dict(path=old+"/examples/custom_knn_gcn",source_sha256="c"*64,
            files=["graph.py","model.py","plugin.py"],factory=factory) for role,factory in [("gnn","build_gnn"),("graph","build_graph_builder")]}
        observed=copy.deepcopy(expected)
        for role in observed:observed[role]["path"]=new+"/examples/custom_knn_gcn"
        canonical=contracts.plugin_identity(observed,expected,current_checkout=new,reference_checkout=old,reference_commit=previous)
        self.assertEqual(canonical["gnn"]["path"],"examples/custom_knn_gcn")
        for field,value in [("source_sha256","d"*64),("files",["other.py"]),("factory","different"),("path",new+"/other")]:
            changed=copy.deepcopy(observed);changed["gnn"][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                contracts.plugin_identity(changed,expected,current_checkout=new,reference_checkout=old,reference_commit=previous)
        with self.assertRaises(ValueError):
            contracts.plugin_identity(observed,expected,current_checkout=new,reference_checkout=old,reference_commit=current)
        with self.assertRaises(ValueError):
            contracts.plugin_identity(observed,expected,current_checkout=new,reference_checkout="/other/"+previous,reference_commit=previous)

    def test_import_and_cli_help_need_no_torch_numpy_or_slurm(self):
        repository=Path(__file__).resolve().parents[1]
        environment={**os.environ,"PYTHONPATH":str(repository/"src")}
        code="import sys; from universal_gnn.benchmarks.molecular.parity import contracts,runtime,references; assert 'torch' not in sys.modules and 'numpy' not in sys.modules"
        subprocess.run([sys.executable,"-S","-c",code],cwd=repository,env=environment,check=True)
        result=subprocess.run([sys.executable,"-S","scripts/verify_molecular_parity.py","--help"],cwd=repository,
            env=environment,capture_output=True,text=True,check=True)
        self.assertIn("--graph-report-sha256",result.stdout)
        self.assertIn("custom_knn_gcn",result.stdout)
        with patch.dict(os.environ,{},clear=True),self.assertRaisesRegex(RuntimeError,"Slurm"):
            runtime.verify_molecular_parity("cgcnn","unused","x","unused")

    def test_source_ordered_train_selection_preserves_all900(self):
        source=[dict(id="unused")]*100000
        for r in records():source[r["source_index"]]=dict(id=r["id"])
        manifest=dict(records=source,counts=dict(COUNTS),partitions=dict(train=list(range(900))))
        self.assertEqual(contracts.training_records(manifest),records())
        for indices in [list(range(899)),list(range(899))+[898],list(reversed(range(900))),
                        [False]+list(range(1,900)),[-1]+list(range(1,900)),[100000]+list(range(1,900)),
                        [[0]]+list(range(1,900))]:
            with self.subTest(indices=indices[:2]),self.assertRaises(ValueError):
                contracts.training_records({**manifest,"partitions":dict(train=indices)})
        for wrong in [dict(COUNTS,train=899),dict(COUNTS,test=1000)]:
            with self.assertRaises(ValueError):contracts.training_records({**manifest,"counts":wrong})
        duplicate=list(source);duplicate[1]=duplicate[0]
        with self.assertRaises(ValueError):contracts.training_records({**manifest,"records":duplicate})

    def test_full_rows_cover_each_provider_and_all_native_outputs(self):
        for model in runtime.ENVIRONMENTS:
            with self.subTest(model=model):
                checked=contracts.checked_rows(iter(rows(model)),records(),model)
                self.assertEqual(checked["structures"],900)
                self.assertEqual(set(checked["maximum_absolute_errors"]),contracts.expected_comparisons(model))
        with self.assertRaises(ValueError):contracts.expected_comparisons("unregistered")

    def test_short_extra_duplicate_wrong_order_and_missing_output_rows_fail(self):
        original=rows("nequip")
        for value in [original[:-1],original+[original[-1]],[original[1],original[0]]+original[2:]]:
            with self.assertRaises(ValueError):contracts.checked_rows(value,records(),"nequip")
        for field,value in [("index",False),("id","other"),("source_index",1),("passed",False),("no_periodic_images",False)]:
            changed=copy.deepcopy(original);changed[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):contracts.checked_rows(changed,records(),"nequip")
        changed=copy.deepcopy(original);del changed[0]["comparisons"]["native_forces"]
        with self.assertRaises(ValueError):contracts.checked_rows(changed,records(),"nequip")

    def test_nonfinite_errors_changed_tolerances_shapes_and_hashes_fail(self):
        for field,value in [("max_absolute_error",float("nan")),("max_absolute_error",float("inf")),
                            ("max_absolute_error",-1.),("max_absolute_error",False),
                            ("shape",[]),("shape",[True]),("rtol",.1),("atol",.1),("actual_sha256","missing")]:
            value_rows=rows("mace");value_rows[-1]["comparisons"]["node_features"][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                contracts.checked_rows(value_rows,records(),"mace")

    def test_official_pairs_and_single_direct_plugin_scope(self):
        for model in runtime.ENVIRONMENTS:
            value,spec=report(model)
            self.assertIs(contracts.checked_report(value,spec),value)
            if spec["official"]:
                del value["initializations"]["scratch"]
                with self.assertRaises(ValueError):contracts.checked_report(value,spec)
            else:
                value["initializations"]["pretrained"]=copy.deepcopy(value["initializations"]["scratch"])
                with self.assertRaises(ValueError):contracts.checked_report(value,spec)

    def test_partial_wrong_identity_cuda_and_formal_claims_fail(self):
        changes=[("version",True),("status","running"),("stage","running"),("model","mace"),("source_sha256","x"),
                 ("definition_sha256","x"),("training_structures",899),("source_structures",900),
                 ("partition","test"),("device","cuda:0"),("dtype","float64"),("seed",456),
                 ("formal_training_runs",1),("formal_training_runs",False),("formal_training_ready",True),
                 ("cuda_capacity_acceptance",True),("parameter_updates",1),("original_package_parity_verified",False),
                 ("direct_plugin_parity_verified",None)]
        for field,new in changes:
            value,spec=report();value[field]=new
            with self.subTest(field=field),self.assertRaises(ValueError):contracts.checked_report(value,spec)

    def test_changed_state_reference_state_loading_coverage_and_nonfinite_summary_fail(self):
        for field,new in [("structures",899),("state_unchanged",False),("reference_state_unchanged",False),
                          ("model_state_after_sha256","c"*64),("reference_state_after_sha256","c"*64),
                          ("native_reference_state_sha256","c"*64),("rows_sha256","missing"),
                          ("maximum_absolute_errors",dict(node_features=float("nan"),native_head=0.))]:
            value,spec=report();value["initializations"]["scratch"][field]=new
            with self.subTest(field=field),self.assertRaises(ValueError):contracts.checked_report(value,spec)
        for field,new in [("parameter_coverage",1.),("buffer_coverage",1.),("state_layout_verified",False)]:
            value,spec=report();value["initializations"]["scratch"]["official"][field]=new
            with self.assertRaises(ValueError):contracts.checked_report(value,spec)

    def test_reviewed_graph_bytes_and_resolved_recipe_cannot_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            config=dict(backbone=dict(name="cgcnn",initialization="pretrained"),batch_size=4,dtype="float32",seed=123)
            spec=dict(official=True,configs=dict(pretrained=config),counts=dict(COUNTS))
            graph=dict(final_config_sha256=dict(pretrained=canonical_digest(config)))
            def write():
                (root/"config.pretrained.json").write_text(json.dumps(config),encoding="utf8")
                raw=json.dumps(graph).encode();(root/"report.json").write_bytes(raw)
                return hashlib.sha256(raw).hexdigest()
            digest=write()
            with patch.object(runtime,"checked_graph_metadata") as checked:
                self.assertEqual(runtime.verified_configs(spec,root,digest)[1]["pretrained"],config)
                checked.assert_called_once_with(graph,spec)
                with self.assertRaises(ValueError):runtime.verified_configs(spec,root,"0"*64)
                config["dtype"]="float64"
                (root/"config.pretrained.json").write_text(json.dumps(config),encoding="utf8")
                with self.assertRaises(ValueError):runtime.verified_configs(spec,root,digest)
                graph["final_config_sha256"]["pretrained"]=canonical_digest(config)
                fixed=copy.deepcopy(spec);fixed["configs"]["pretrained"]["dtype"]="float32"
                digest=write()
                with self.assertRaises(ValueError):runtime.verified_configs(fixed,root,digest)


if __name__=="__main__":unittest.main()
