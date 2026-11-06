"""Real disposable mixed-batch optimization; CPU emits diagnostics only."""

import os
from pathlib import Path
import time

from ..preflight import write_json
from ..probes.schedule import schedule_settings
from .schedule import mixed_probe_batches, checked_mixed_capacity


def run_mixed_capacity(config, probe, progress):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Mixed numerical capacity must run through Slurm")
    if (config.get("task", {}).get("kind") != "forcefield" or config.get("structures") != "all"
            or config.get("max_atoms") is not None or config.get("dtype") != "float32"
            or config.get("seed") != 123):
        raise ValueError("Require the complete seed123 float32 molecular forcefield recipe")
    import torch
    from universal_gnn.contracts import StructureBatch
    from universal_gnn.engine.training import build_model, dataset, predict
    from universal_gnn.engine.metrics import dataset_scales, loss_parts, weighted_loss
    from universal_gnn.engine.optimization import components, make_optimizer
    from ..native_heads.evaluation import state_digest

    torch.set_num_threads(1)
    device = torch.device(config["device"])
    if device.type not in {"cpu", "cuda"}:
        raise ValueError("Explicit CPU diagnostic or CUDA device required")
    cuda = device.type == "cuda"
    if cuda:
        if not torch.cuda.is_available():
            raise RuntimeError("Actual CUDA allocation is unavailable")
        torch.cuda.set_device(device)
        device = torch.device("cuda", torch.cuda.current_device())
    torch.manual_seed(123)
    structures = dataset(config)
    if len(structures) != 900 or len(structures.source) != 100000:
        raise ValueError("Mixed capacity requires all900 molecular training structures")
    model = build_model(config).to(device=device, dtype=torch.float32).train()
    modules = components(model)
    if set(modules) != {"backbone", "readout"} or any(not model._component_policy["train_" + key] for key in modules):
        raise ValueError("Molecular capacity must exercise both trainable components")
    before = {key: state_digest(module) for key, module in modules.items()}
    optimizer = make_optimizer(model, config)
    scales = dataset_scales(structures, config)
    batch_size = config["batch_size"]
    settings = schedule_settings(probe, batch_size)
    report = dict(version=1, status="running", policy="full_batch_mixed_extremes_v1", actual_device=str(device),
        cuda_capacity=cuda, batch_size=batch_size, complete_training_structures=900,
        warmup_batches=settings["warmup_batches"], measured_batches=0, measured_structures=0,
        within_batch_mixing=batch_size > 1, formal_training_runs=0, covered_worst_indices=[])
    progress = Path(progress)
    write_json(progress, report)
    minimum = {key: float("inf") for key in modules}
    worst = probe.get("worst_indices", probe["indices"])
    started = None
    for step, item in enumerate(mixed_probe_batches(probe, batch_size)):
        if item["phase"] == "measure" and started is None:
            if cuda:
                torch.cuda.synchronize(device)
                torch.cuda.reset_peak_memory_stats(device)
            started = time.perf_counter()
        report.update(step=step, batch_indices=item["indices"], batch_phase=item["phase"])
        write_json(progress, report)
        batch = StructureBatch.from_structures([structures[i] for i in item["indices"]]).to(device, torch.float32)
        optimizer.zero_grad(set_to_none=True)
        predicted = predict(model, batch, config, training=True)
        loss = weighted_loss(loss_parts(predicted, batch, config, scales), config)
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError("Nonfinite molecular mixed-batch loss")
        loss.backward()
        for key, module in modules.items():
            grads = [p.grad for p in module.parameters() if p.grad is not None]
            if not grads or any(not bool(torch.isfinite(value).all()) for value in grads):
                raise FloatingPointError("Missing/nonfinite molecular component gradients: " + key)
            norm = sum(float(value.detach().double().square().sum()) for value in grads) ** .5
            if norm <= 1e-10:
                raise FloatingPointError("Molecular mixed batch did not differentiate " + key)
            minimum[key] = min(minimum[key], norm)
        torch.nn.utils.clip_grad_norm_(model.parameters(), config.get("clip_grad_norm", 10.))
        optimizer.step()
        if cuda:
            torch.cuda.synchronize(device)
        if item["phase"] == "measure":
            report["measured_batches"] += 1
            report["measured_structures"] += batch_size
            first = item["indices"][0]
            if first in worst and first not in report["covered_worst_indices"]:
                report["covered_worst_indices"].append(first)
        del predicted, loss, batch
    elapsed = time.perf_counter() - started
    report.update(status="passed", elapsed_seconds=elapsed, minimum_parameter_gradient_norms=minimum,
        model_state_changed={key: before[key] != state_digest(module) for key, module in modules.items()},
        peak_allocated_bytes=torch.cuda.max_memory_allocated(device) if cuda else None,
        peak_reserved_bytes=torch.cuda.max_memory_reserved(device) if cuda else None)
    checked_mixed_capacity(report, probe, batch_size, require_cuda=cuda)
    write_json(progress, report)
    return report
