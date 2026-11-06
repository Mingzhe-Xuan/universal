"""Actual full-size mixed training diagnostic on real900train; CPU is not CUDA."""

import json
import os
from pathlib import Path

import pytest

from universal_gnn.benchmarks.molecular.contracts import selected_group
from universal_gnn.benchmarks.molecular.mixed import run_mixed_capacity
from universal_gnn.benchmarks.molecular.schedule import checked_mixed_capacity


pytestmark=pytest.mark.skipif(not os.environ.get("SLURM_JOB_ID"),reason="Real mixed optimizer diagnostic requires Slurm")


@pytest.mark.parametrize("batch",[1,2,4])
def test_actual_plugin102_full_batches_update_both_components_and_preserve_cpu_scope(batch,tmp_path):
    spec=selected_group("custom_knn_gcn");config=spec["reference_config"]
    config.update(device="cpu",batch_size=batch)
    directory=Path("runs/molecular-native-graphs-72000aa-cpu-custom_knn_gcn")
    probe=json.loads((directory/"probe.json").read_bytes())
    report=run_mixed_capacity(config,probe,tmp_path/("mixed-"+str(batch)+".json"))
    assert report["actual_device"]=="cpu" and report["cuda_capacity"] is False
    assert report["measured_batches"]>=100 and report["measured_structures"]==report["measured_batches"]*batch
    assert report["model_state_changed"]==dict(backbone=True,readout=True)
    assert all(value>1e-10 for value in report["minimum_parameter_gradient_norms"].values())
    checked_mixed_capacity(report,probe,batch,require_cuda=False)
    with pytest.raises(ValueError):checked_mixed_capacity(report,probe,batch,require_cuda=True)
