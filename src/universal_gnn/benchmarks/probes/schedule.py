"""Cover each declared worst case at the full candidate batch size after warmup."""


def _positive(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def schedule_settings(probe, batch_size):
    _positive(batch_size, "batch_size")
    if not isinstance(probe, dict):
        raise ValueError("Probe must be a mapping")
    indices = probe.get("indices")
    if (not isinstance(indices, list) or not indices or
            any(type(index) is not int or index < 0 for index in indices) or len(set(indices)) != len(indices)):
        raise ValueError("Probe indices must be nonempty, unique nonnegative integers")
    worst = probe.get("worst_indices", indices)
    if (not isinstance(worst, list) or not worst or any(type(index) is not int for index in worst) or
            len(set(worst)) != len(worst) or any(index not in indices for index in worst)):
        raise ValueError("Worst indices must be a nonempty unique subset of probe indices")
    warmup = _positive(probe.get("warmup_batches", 2), "warmup_batches")
    requested = _positive(probe.get("measure_batches", 100), "measure_batches")
    return dict(batch_size=batch_size, warmup_batches=warmup, requested_measure_batches=requested,
                measure_batches=max(requested, len(worst)), worst_stress_batches=len(worst))


def iter_probe_batches(probe, batch_size):
    settings = schedule_settings(probe, batch_size)
    indices, worst = probe["indices"], probe.get("worst_indices", probe["indices"])
    for index in range(settings["warmup_batches"]):
        selected = [indices[(index * batch_size + offset) % len(indices)] for offset in range(batch_size)]
        yield dict(phase="warmup", kind="ordinary", indices=selected)
    for index in range(settings["measure_batches"]):
        if index < len(worst):
            yield dict(phase="measure", kind="worst", indices=[worst[index]] * batch_size)
        else:
            ordinary = index - len(worst)
            selected = [indices[(ordinary * batch_size + offset) % len(indices)] for offset in range(batch_size)]
            yield dict(phase="measure", kind="ordinary", indices=selected)
