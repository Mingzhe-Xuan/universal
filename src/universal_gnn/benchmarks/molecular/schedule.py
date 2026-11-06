"""Full-size mixed extreme batches, explicitly distinguishing batch-one replay."""

import math

from ..probes.schedule import schedule_settings


def mixed_probe_batches(probe, batch_size):
    settings = schedule_settings(probe, batch_size)
    if batch_size > 1 and len(probe["indices"]) < 2:
        raise ValueError("Within-batch mixing requires two distinct training structures")
    worst = probe.get("worst_indices", probe["indices"])
    ordinary = [i for i in probe["indices"] if i not in set(worst)] or probe["indices"]
    for step in range(settings["warmup_batches"]):
        yield dict(phase="warmup", indices=[ordinary[(step * batch_size + j) % len(ordinary)] for j in range(batch_size)])
    for step in range(settings["measure_batches"]):
        selected = [worst[step % len(worst)]]
        if batch_size > 1:
            selected.append(worst[(step + 1) % len(worst)] if len(worst) > 1 else ordinary[step % len(ordinary)])
        selected.extend(ordinary[(step * batch_size + j) % len(ordinary)] for j in range(batch_size - len(selected)))
        yield dict(phase="measure", indices=selected)


def checked_mixed_capacity(value, probe, batch_size, *, require_cuda=True):
    settings = schedule_settings(probe, batch_size)
    worst = probe.get("worst_indices", probe["indices"])
    integers = ["version", "batch_size", "measured_batches", "warmup_batches", "measured_structures",
                "complete_training_structures", "formal_training_runs"]
    if (not isinstance(value, dict) or value.get("status") != "passed" or value.get("version") != 1
            or any(type(value.get(key)) is not int for key in integers)
            or value.get("policy") != "full_batch_mixed_extremes_v1" or value.get("batch_size") != batch_size
            or value.get("measured_batches") != settings["measure_batches"]
            or value.get("warmup_batches") != settings["warmup_batches"]
            or value.get("measured_structures") != batch_size * settings["measure_batches"]
            or value.get("covered_worst_indices") != worst or value.get("complete_training_structures") != 900
            or value.get("within_batch_mixing") is not (batch_size > 1)
            or value.get("model_state_changed") != {"backbone": True, "readout": True}
            or value.get("formal_training_runs") != 0):
        raise ValueError("Incomplete molecular full-batch mixed capacity")
    device = value.get("actual_device")
    cuda = isinstance(device, str) and (device == "cuda" or (device.startswith("cuda:") and device[5:].isdigit()))
    if (not cuda and device != "cpu") or value.get("cuda_capacity") is not cuda or (require_cuda and not cuda):
        raise ValueError("Actual CUDA mixed capacity is required; CPU diagnostics cannot substitute")
    for key in ["elapsed_seconds", *(["peak_allocated_bytes", "peak_reserved_bytes"] if cuda else [])]:
        number = value.get(key)
        if type(number) not in (int, float) or not math.isfinite(number) or number <= 0:
            raise ValueError("Mixed capacity lacks measured timing/memory")
    norms = value.get("minimum_parameter_gradient_norms")
    if (not isinstance(norms, dict) or set(norms) != {"backbone", "readout"}
            or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 1e-10 for x in norms.values())):
        raise ValueError("Both molecular components require finite nonzero mixed-batch gradients")
    return value
