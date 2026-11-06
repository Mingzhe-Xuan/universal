"""Retain the original CUDA probe and add a separate full mixed-extreme phase."""

import json
import os
from pathlib import Path
import sys

from ..preflight import write_json


def execute(request, result, result_path):
    if not os.environ.get("SLURM_JOB_ID") or not str(request["config"].get("device", "")).startswith("cuda"):
        raise RuntimeError("Molecular production capacity requires Slurm and actual CUDA")
    if request.get("phase") != "train":
        raise ValueError("Molecular mixed capacity describes forcefield training")
    from ..probe_worker import execute as original_execute
    from ..resolution import resolved_candidate
    from .mixed import run_mixed_capacity

    original_execute(request, result, result_path)
    core = {key: result[key] for key in ["measured_batches", "measured_structures", "elapsed_seconds",
                                       "peak_allocated_bytes", "peak_reserved_bytes"]}
    import gc
    import torch
    gc.collect()
    torch.cuda.synchronize()
    torch.cuda.empty_cache()
    config = resolved_candidate(request["config"], result)
    result.update(status="running", stage="mixed_extreme_capacity", base_capacity=core)
    write_json(result_path, result)
    mixed = run_mixed_capacity(config, request["probe"], Path(result_path).with_name("mixed-progress.json"))
    elapsed = core["elapsed_seconds"] + mixed["elapsed_seconds"]
    structures = core["measured_structures"] + mixed["measured_structures"]
    result.update(status="passed", stage="complete", worker_kind="molecular_homogeneous_and_mixed_v1", mixed_capacity=mixed,
        elapsed_seconds=elapsed, measured_structures=structures, structures_per_second=structures / elapsed,
        measured_batches=core["measured_batches"] + mixed["measured_batches"],
        planned_measured_batches=core["measured_batches"] + mixed["measured_batches"],
        peak_allocated_bytes=max(core["peak_allocated_bytes"], mixed["peak_allocated_bytes"]),
        peak_reserved_bytes=max(core["peak_reserved_bytes"], mixed["peak_reserved_bytes"]))


def main():
    request_path, result_path = sys.argv[1:]
    request = json.loads(Path(request_path).read_text(encoding="utf8"))
    result = dict(version=1, status="running", stage="startup", phase=request["phase"], batch_size=request["config"]["batch_size"])
    write_json(result_path, result)
    code = 1
    try:
        execute(request, result, result_path)
        code = 0
    except Exception as error:
        import traceback
        traceback.print_exc()
        torch = sys.modules.get("torch")
        oom = (torch is not None and isinstance(error, torch.cuda.OutOfMemoryError)
               and "cuda" in str(error).lower() and "out of memory" in str(error).lower())
        result.update(status="cuda_oom" if oom else "failed", error=str(error),
                      error_type="cuda_out_of_memory" if oom else type(error).__name__)
        code = 42 if oom else 1
    write_json(result_path, result)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
