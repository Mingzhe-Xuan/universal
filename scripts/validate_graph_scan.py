"""Numerical graph-format/guard checks; requires Slurm and a CUDA allocation."""

import argparse
import os
from pathlib import Path
import unittest


class GraphScanRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get("SLURM_JOB_ID"):
            raise RuntimeError("Graph scan numerical checks must run through Slurm")
        import torch
        from universal_gnn.contracts import Structure, StructureBatch

        if not torch.cuda.is_available():
            raise RuntimeError("Graph-scan numerical acceptance requires CUDA")
        cls.torch = torch
        structure = Structure(torch.tensor([1, 1]), torch.tensor([[0., 0., 0.], [1., 0., 0.]]),
                              torch.eye(3) * 20, torch.tensor([False, False, False]), "graph-scan-fixture")
        cls.batch = StructureBatch.from_structures([structure]).to("cuda", torch.float32)

    def test_four_native_output_formats(self):
        from types import SimpleNamespace
        from universal_gnn.benchmarks.probes.native_scan import count_graphs

        t = self.torch
        edges = t.tensor([[0, 1], [1, 0]], device="cuda")
        graph = SimpleNamespace(num_nodes=2, num_edges=2, src=edges[0], dst=edges[1])
        line = SimpleNamespace(num_nodes=2, num_edges=2, src=edges[0], dst=edges[1])
        native = dict(cgcnn=(t.zeros(2, 4, device="cuda"), t.zeros(2, 3, 5, device="cuda"),
                              t.tensor([[1, 0, 0], [0, 0, 0]], device="cuda"), [t.arange(2, device="cuda")]),
                      alignn=(graph, line, self.batch.cell), mace={"edge_index":edges}, nequip={"edge_index":edges})
        for provider, value in native.items():
            with self.subTest(provider=provider):
                backbone = SimpleNamespace(native_input=lambda batch, value=value: value)
                counts = count_graphs(provider, backbone, [], self.batch)
                self.assertEqual(counts, dict(atoms=2, native_edges=6 if provider == "cgcnn" else 2,
                                             native_triplets=2 if provider == "alignn" else 0,
                                             auxiliary_edges=0, maximum_degree=3 if provider == "cgcnn" else 1))

    def test_real_auxiliary_radius_graph(self):
        from types import SimpleNamespace
        from universal_gnn.benchmarks.probes.native_scan import count_graphs

        backbone = SimpleNamespace(native_input=lambda batch: {"edge_index": self.torch.empty((2, 0), device="cuda", dtype=self.torch.long)})
        counts = count_graphs("mace", backbone, [("response", SimpleNamespace(cutoff=1.5))], self.batch)
        self.assertEqual(counts, dict(atoms=2, native_edges=0, native_triplets=0, auxiliary_edges=2, maximum_degree=1))

    def test_real_active_module_selection(self):
        from universal_gnn.adapters.features import EquivariantAdapter
        from universal_gnn.tasks.generation import DirectionReadout
        from universal_gnn.benchmarks.probes.native_scan import auxiliary_modules

        modules = self.torch.nn.ModuleDict(dict(response=EquivariantAdapter("2x0e", cutoff=3.),
                                               scalar=DirectionReadout("2x0e", "invariant", 4.),
                                               polar=DirectionReadout("1x0e + 1x1o", "equivariant", 5.)))
        self.assertEqual([name for name, _ in auxiliary_modules(modules)], ["response", "scalar"])

    def test_model_forward_guard_and_hook_cleanup(self):
        from universal_gnn.benchmarks.probes.native_scan import forbid_model_forward

        model = self.torch.nn.Sequential(self.torch.nn.Linear(2, 2)).cuda()
        calls=[]
        handle=model[0].register_forward_hook(lambda *args: calls.append(True))
        try:
            with forbid_model_forward(model):
                with self.assertRaisesRegex(RuntimeError, "must not execute"):
                    model(self.torch.zeros(1, 2, device="cuda"))
            self.assertEqual(calls, [])
            from torch.nn.modules.module import _global_forward_pre_hooks
            self.assertFalse(_global_forward_pre_hooks)
        finally:
            handle.remove()

    def test_scripted_child_forward_is_rejected(self):
        from universal_gnn.benchmarks.probes.native_scan import forbid_model_forward

        model=self.torch.nn.Sequential(self.torch.jit.script(self.torch.nn.Linear(2, 2))).cuda()
        with forbid_model_forward(model):
            with self.assertRaisesRegex(RuntimeError, "must not execute"):
                model[0](self.torch.zeros(1, 2, device="cuda"))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Graph scan numerical checks must run through Slurm")
    output=Path(args.output)
    if output.exists():parser.error("Use a new result file")
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(GraphScanRuntimeTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.testsRun!=5 or result.skipped:
        raise RuntimeError("Numerical graph-format/guard checks failed or skipped")
    import hashlib
    import json
    import subprocess
    output.parent.mkdir(parents=True,exist_ok=True)
    value=dict(status="passed",tests=5,slurm_job_id=os.environ['SLURM_JOB_ID'],
               git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
               source_sha256={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in
                              ['scripts/validate_graph_scan.py','src/universal_gnn/benchmarks/probes/native_scan.py']},
               coverage="numerical graph-format fixtures and guard only; original provider full scans remain required")
    output.write_text(json.dumps(value,indent=2))
    print(json.dumps(value))


if __name__=='__main__':main()
