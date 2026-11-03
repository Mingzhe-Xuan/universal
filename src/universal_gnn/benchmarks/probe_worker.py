"""Disposable worker: no checkpoints or optimizer updates escape this process."""

import json
import sys
import time

from .preflight import write_json


def execute(request, result, result_path):
    import torch

    from universal_gnn.contracts import StructureBatch
    from universal_gnn.engine.batching import model_dtype
    from universal_gnn.engine.training import build_model, dataset, predict, version_record, execution_record
    from universal_gnn.engine.optimization import make_optimizer
    from universal_gnn.engine.metrics import dataset_scales, loss_parts, weighted_loss

    config, probe = request["config"], request["probe"]
    device = torch.device(config["device"])
    torch.cuda.set_device(device)
    torch.manual_seed(config.get("seed", 123))
    torch.cuda.manual_seed_all(config.get("seed", 123))
    result.update(stage="model_initialization", versions=version_record(),
                  device={"name": torch.cuda.get_device_name(device),
                          "total_memory": torch.cuda.get_device_properties(device).total_memory})
    write_json(result_path, result)
    model = build_model(config).to(device=device, dtype=model_dtype(config))
    result["execution"] = execution_record(model)
    optimizer = make_optimizer(model, config)
    structures = dataset(config)
    indices = probe["indices"]
    if max(indices) >= len(structures):
        raise ValueError("Probe index exceeds selected training dataset")
    worst = probe.get("worst_indices", indices)
    if not worst or any(index not in indices for index in worst):
        raise ValueError("worst_indices must be a nonempty subset of probe.indices")
    result["samples"] = [{"index": i, "id": structures[i].identifier, "atoms": len(structures[i].numbers)}
                         for i in indices]
    result["coverage"] = probe.get("coverage", {"verified_full_training_scan": False})
    result["stage"] = "label_scales"
    write_json(result_path, result)
    generation = config["task"]["kind"] == "generation"
    scales = None if generation else dataset_scales(structures, config)
    if request["phase"] == "sample" and not generation:
        raise ValueError("Sampling capacity applies only to generation")
    batch_size = config["batch_size"]
    warmup, measured = probe.get("warmup_batches", 2), probe.get("measure_batches", 100)
    measured_structures = 0
    model.train(request["phase"] == "train")
    start = None
    for step in range(warmup + measured):
        if step == warmup:
            torch.cuda.synchronize(device)
            torch.cuda.reset_peak_memory_stats(device)
            start = time.perf_counter()
        # The first batch stresses the supplied worst cases, repeating when B exceeds
        # their count. Remaining batches cycle real training records without labels from val/test.
        pool = worst if step in (0, warmup) else indices
        selected = [pool[(step * batch_size + offset) % len(pool)] for offset in range(batch_size)]
        result.update(stage="batch", step=step, batch_indices=selected)
        write_json(result_path, result)
        if generation and request["phase"] == "train":
            from universal_gnn.engine.generation import generation_batches, score_loss

            chosen = [structures[i] for i in selected]
            _, batch, times, targets = next(generation_batches(chosen, config, epoch=step))
        else:
            batch = StructureBatch.from_structures([structures[i] for i in selected]).to(device, model_dtype(config))
        optimizer.zero_grad(set_to_none=True)
        if request["phase"] == "sample":
            result["stage"] = "sample"
            write_json(result_path, result)
            settings = dict(config["task"].get("sampling", {}))
            settings.setdefault("seed", config.get("seed", 123) + step)
            generated = model.sample(batch, **settings)
            if not bool(torch.isfinite(generated.positions).all() and torch.isfinite(generated.cell).all()):
                raise FloatingPointError("Nonfinite generated geometry")
            del generated
        else:
            result["stage"] = "forward_loss"
            write_json(result_path, result)
            if generation:
                prediction = model(batch, times)
                loss = score_loss(prediction, targets)
            else:
                prediction = predict(model, batch, config, training=True)
                loss = weighted_loss(loss_parts(prediction, batch, config, scales), config)
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError("Nonfinite preflight loss")
            result["stage"] = "backward"
            write_json(result_path, result)
            loss.backward()
            gradients = [parameter.grad for parameter in model.parameters() if parameter.grad is not None]
            if not gradients or not all(bool(torch.isfinite(grad).all()) for grad in gradients):
                raise FloatingPointError("Missing/nonfinite preflight gradients")
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.get("clip_grad_norm", 10.))
            result["stage"] = "optimizer_step"
            write_json(result_path, result)
            optimizer.step()
            del prediction, loss, gradients
        torch.cuda.synchronize(device)
        if step >= warmup:
            measured_structures += batch.num_graphs
        del batch
    elapsed = time.perf_counter() - start
    result.update(status="passed", stage="complete", measured_batches=measured,
                  measured_structures=measured_structures, elapsed_seconds=elapsed,
                  structures_per_second=measured_structures / elapsed,
                  peak_allocated_bytes=torch.cuda.max_memory_allocated(device),
                  peak_reserved_bytes=torch.cuda.max_memory_reserved(device))


def main():
    request_path, result_path = sys.argv[1:]
    with open(request_path, encoding="utf-8") as stream:
        request = json.load(stream)
    result = {"version": 1, "batch_size": request["config"]["batch_size"],
              "phase": request["phase"], "status": "running", "stage": "startup"}
    write_json(result_path, result)
    exit_code = 1
    try:
        execute(request, result, result_path)
        exit_code = 0
    except Exception as error:
        import traceback

        traceback.print_exc()
        torch = sys.modules.get("torch")
        cuda_oom = (torch is not None and isinstance(error, torch.cuda.OutOfMemoryError)
                    and "cuda" in str(error).lower() and "out of memory" in str(error).lower())
        result.update(status="cuda_oom" if cuda_oom else "failed", error=str(error),
                      error_type="cuda_out_of_memory" if cuda_oom else type(error).__name__)
        if torch is not None and torch.cuda.is_initialized():
            result["peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
            result["peak_reserved_bytes"] = torch.cuda.max_memory_reserved()
        exit_code = 42 if cuda_oom else 1
    write_json(result_path, result)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
