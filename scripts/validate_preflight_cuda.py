"""Synthetic integration only; execute inside a Slurm GPU allocation."""

import argparse
import json
import os
from pathlib import Path

from universal_gnn.benchmarks.preflight import run_preflight, write_json


OOM_PLUGIN = '''
import torch
from torch import nn
from universal_gnn.contracts import BaseGNN, GNNOutput

class AllocationProbe(BaseGNN):
    def __init__(self, always_oom=False, context_dim=0):
        super().__init__("8x0e", "invariant", context_dim)
        self.embedding = nn.Embedding(119, 8)
        self.always_oom = always_oom
    def forward(self, graph, context=None):
        batch = graph.geometry
        if self.always_oom or batch.num_graphs > 2:
            size = torch.cuda.get_device_properties(batch.positions.device).total_memory * 2
            torch.empty(size, dtype=torch.uint8, device=batch.positions.device)
            raise AssertionError("An allocation larger than physical device memory unexpectedly succeeded")
        return GNNOutput(self.embedding(batch.numbers))

def build_gnn(**options):
    return AllocationProbe(**options)
'''


def main():
    import torch

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID") or not torch.cuda.is_available():
        raise RuntimeError("CUDA integration must run in a Slurm GPU allocation")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "synthetic.jsonl"
    records = [{"schema_version": 1, "id": f"fixture-{i}", "numbers": [14, 14],
                "positions": [[0., 0., 0.], [1.3 + .05 * i, .4, .2]],
                "cell": [[8., 0., 0.], [0., 8., 0.], [0., 0., 8.]], "pbc": [True] * 3,
                "targets": {"bandgap": 1. + i, "classification": i % 2,
                            "dielectric": [[1., 0., 0.], [0., 2., 0.], [0., 0., 3.]],
                            "spectrum": [.1 * (i + j) for j in range(8)],
                            "forces": [[.1, .2, .3], [-.1, -.2, -.3]]}} for i in range(3)]
    source.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    probe = {"indices": [0, 1, 2], "worst_indices": [2], "warmup_batches": 1, "measure_batches": 2,
             "coverage": {"verified_full_training_scan": False, "purpose": "synthetic integration only"}}
    base = {"seed": 123, "device": "cuda:0", "batch_size": 3, "dtype": "float32",
            "backbone": {"name": "gcn", "width": 8, "layers": 1, "cutoff": 2.},
            "graph": {"name": "radius", "cutoff": 2.}, "dataset": {"path": str(source)},
            "learning_rate": 1e-3}
    summaries = {}
    for name in ("bandgap", "classification", "spectrum", "dielectric", "forces", "generation"):
        config = json.loads(json.dumps(base))
        config["task"] = {"kind": "supervised", "property": name}
        if name == "spectrum":
            config["task"]["channels"] = 8
        if name == "dielectric":
            config["prediction"] = {"version": 1, "readout": {"name": "response", "pooling": "mean"}}
        if name == "forces":
            config["task"] = {"kind": "forcefield", "supervised_outputs": ["forces"]}
            config["prediction"] = {"version": 1, "readout": {"name": "node_mlp", "pooling": "sum", "hidden_features": [8]}}
        if name == "generation":
            config["task"] = {"kind": "generation", "sampling": {"steps": 2, "inner_steps": 1, "seed": 456}}
        report = run_preflight(config, output / name, probe=probe, timeout=600)
        if not report["passed"]:
            raise AssertionError(f"Full training step failed: {name}; inspect {output / name}")
        summaries[name] = {"batch_size": report["final_batch_size"], "phase": "train"}
        if name == "generation":
            sampling = run_preflight(config, output / "generation-sample", probe=probe, phase="sample", timeout=600)
            if not sampling["passed"]:
                raise AssertionError("Generation sampling probe failed")
            summaries["generation_sample"] = {"batch_size": sampling["final_batch_size"], "phase": "sample"}
    plugin = output / "allocation-plugin"
    plugin.mkdir()
    (plugin / "plugin.py").write_text(OOM_PLUGIN, encoding="utf-8")
    for always in (False, True):
        config = json.loads(json.dumps(base))
        config["batch_size"] = 5
        config["backbone"] = {"name": "plugin:" + str(plugin), "always_oom": always}
        config["task"] = {"kind": "supervised", "property": "bandgap"}
        name = "batch-one-oom" if always else "actual-cuda-oom-backoff"
        report = run_preflight(config, output / name, probe=probe, timeout=600)
        expected = [5, 2, 1] if always else [5, 2]
        assert [attempt["batch_size"] for attempt in report["attempts"]] == expected
        assert report["passed"] is not always
        assert report["final_batch_size"] == (None if always else 2)
        summaries[name] = {"attempts": expected, "passed": report["passed"]}
    write_json(output / "acceptance.json", {"passed": True, "cases": summaries,
               "slurm_job_id": os.environ["SLURM_JOB_ID"], "scope": "synthetic integration; not a full-data resource precheck"})
    print(json.dumps(summaries))


if __name__ == "__main__":
    main()
