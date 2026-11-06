"""Complete molecular workload and closed official/plugin initialization contracts."""

import math
from pathlib import Path
import re

from ...submission.planning import finite_budget
from ..contracts import DEFINITION_SHA, selected_group
from ..parity.contracts import plugin_identity
from ..source import COUNTS


def selected_case(identifier):
    if identifier == "molecular-plugin--seed-123--forcefield--knn-gcn--scratch":
        model = "custom_knn_gcn"
    else:
        match = re.fullmatch(r"molecular--seed-123--forcefield--(cgcnn|alignn|mace|nequip)--(pretrained|scratch)", identifier)
        if not match:
            raise ValueError("Select one of the closed nine seed123 molecular cases")
        model = match.group(1)
    group = selected_group(model)
    cases = [case for case in group["cases"] if case["id"] == identifier]
    if len(cases) != 1:
        raise ValueError("Molecular case is absent from its complete frozen definition")
    return dict(group, case=cases[0])


def workload(config, batch):
    if (type(batch) is not int or batch < 1 or config.get("epochs") != 300
            or config.get("seed") != 123 or config.get("structures") != "all"
            or config.get("max_atoms") is not None or config.get("dtype") != "float32"
            or config.get("evaluation", {}).get("patience") != 30):
        raise ValueError("Preserve the full seed123/300cap-pat30/f32 molecular protocol")
    train = math.ceil(900 / batch)
    # Initial/final loss, two forwards in reload comparison, and a scheduling
    # allowance for full training-only normalization/calibration traversal.
    return dict(training_batches=300 * train, validation_batches=300 * math.ceil(100 / batch),
        heldout_batches=math.ceil(99000 / batch), additional_training_pass_batches=5 * train,
        author_cohort_model_batches=0, author_cohort_saved_rows=1000)


def execution_budget(config, evidence, *, maximum=None):
    batch = evidence["common_batch_size"]
    counts = workload(config, batch)
    samples = []
    for worker in evidence.get("successful_workers", []):
        for phase in ("base_capacity", "mixed_capacity"):
            observed = worker.get(phase, {})
            elapsed, batches = observed.get("elapsed_seconds"), observed.get("measured_batches")
            if (type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed <= 0
                    or type(batches) is not int or batches < 100
                    or type(worker.get("batch_size")) is not int or worker["batch_size"] < batch):
                raise ValueError("Require the original complete homogeneous100/mixed100 timing evidence")
            samples.append(dict(phase=phase, batch_size=worker["batch_size"], elapsed_seconds=elapsed,
                measured_batches=batches, seconds_per_batch=elapsed / batches))
    if not samples:
        raise ValueError("Missing actual measured capacity timing")
    seconds = max(row["seconds_per_batch"] for row in samples)
    batches = sum(counts[key] for key in ("training_batches", "validation_batches", "heldout_batches", "additional_training_pass_batches"))
    estimate = seconds * batches
    return dict(kind="complete_molecular_training_equivalent_schedule_v1", common_batch_size=batch,
        counts=dict(COUNTS), max_epochs=300, workload=counts, training_equivalent_batches=batches,
        measured_training_samples=samples, conservative_training_seconds_per_batch=seconds,
        estimated_execution_seconds=estimate, budget_seconds=finite_budget(estimate, maximum),
        evaluation_throughput_measured=False, timing_upper_bound_proven=False,
        interpretation="Scheduling proxy using the slowest measured homogeneous/mixed training average; includes full validation/99000 test and ancillary traversals. Not measured evaluation throughput or a proven timing bound. Reserve50%+900s; author1000 reuses saved full test predictions.")


def verify_plugin_initialization(trained, gate):
    spec = selected_case(gate["case"]["id"])
    if (spec["official"] or gate.get("kind") != "formal_molecular_execution_gate"
            or gate.get("definition_sha256") != DEFINITION_SHA or gate["case"] != spec["case"]
            or gate["case"]["initialization"] != "scratch"
            or trained["execution"].get("official") is not None
            or trained["execution"].get("backbone_class") != "StandardBackbone"
            or trained["execution"].get("gnn_class") != "MolecularGCN"):
        raise ValueError("Only the closed directory plugin may omit official initialization metadata")
    expected_config = spec["case"]["config"]
    batch = gate["config"].get("batch_size")
    if (gate.get("counts") != COUNTS or gate.get("source_structures") != 100000
            or type(batch) is not int or not 1 <= batch <= expected_config["batch_size"]
            or dict(gate["config"], batch_size=expected_config["batch_size"]) != expected_config):
        raise ValueError("Plugin verification must retain the entire original molecular recipe and scope")
    expected = gate["native_graph"]
    previous = Path(expected["gnn"]["path"]).parent.parent
    plugin_identity(trained["execution"]["extensions"], expected, current_checkout=Path.cwd().resolve(),
        reference_checkout=previous, reference_commit=gate["capacity_commit"])
