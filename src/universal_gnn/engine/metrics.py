"""Dataset-level label scales and element-weighted losses across uneven minibatches."""

import math

import torch

from universal_gnn.properties import property_spec
from universal_gnn.tasks.supervision import supervised_outputs, supervised_predictions


def is_classification(config):
    task = config["task"]
    return task["kind"] == "supervised" and property_spec(
        task["property"], definition=task.get("spec")).kind == "classification"


def dataset_scales(structures, config):
    if is_classification(config):
        return {config["task"]["property"]: 1.}
    names = supervised_outputs(config)
    statistics = {name: [0, 0., 0., 0.] for name in names}
    for structure in structures:
        for name in names:
            if name not in structure.targets:
                raise ValueError(f"{structure.identifier}: missing bound label {name}")
            values = torch.as_tensor(structure.targets[name], dtype=torch.float64).reshape(-1)
            values = values[torch.isfinite(values)]
            if not len(values):
                continue
            n, mean, m2, absolute = statistics[name]
            k, local = len(values), float(values.mean())
            delta = local - mean
            statistics[name] = [n + k, mean + delta * k / (n + k),
                                m2 + float((values - local).square().sum()) + delta * delta * n * k / (n + k),
                                absolute + float(values.abs().sum())]
    result = {}
    for name, (n, mean, m2, absolute) in statistics.items():
        if not n:
            raise ValueError(f"No finite labels for {name}")
        result[name] = max(math.sqrt(m2 / n), absolute / n * .1, 1e-2)
    return result


def loss_parts(predictions, batch, config, scales):
    from universal_gnn.engine.training import label

    classification = is_classification(config)
    result = {}
    for name, prediction in supervised_predictions(predictions, config).items():
        if not bool(torch.isfinite(prediction).all()):
            raise FloatingPointError(f"Nonfinite predictions: {name}")
        target = label(batch, name, prediction, classification=classification)
        if classification:
            numerator = torch.nn.functional.cross_entropy(prediction, target, reduction="sum")
            count = target.numel()
        else:
            mask = torch.isfinite(target)
            count = int(mask.sum())
            numerator = ((prediction[mask] - target[mask]) / scales[name]).square().sum()
        result[name] = (numerator, count)
    return result


def weighted_loss(parts, config):
    terms = [config["task"].get("loss_weights", {}).get(name, 1.) * numerator / count
             for name, (numerator, count) in parts.items() if count]
    if not terms:
        raise ValueError("Minibatch has no finite labels")
    return torch.stack(terms).sum()


class LossTotals:
    def __init__(self):
        self.values = {}

    def add(self, parts):
        for name, (numerator, count) in parts.items():
            previous, n = self.values.get(name, (0., 0))
            self.values[name] = (previous + float(numerator.detach()), n + count)

    def loss(self, config):
        if any(not count for _, count in self.values.values()) or not self.values:
            raise ValueError("Dataset contains an output with no finite labels")
        return sum(config["task"].get("loss_weights", {}).get(name, 1.) * total / count
                   for name, (total, count) in self.values.items())
