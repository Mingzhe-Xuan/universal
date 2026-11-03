"""Select training labels independently of the force-field model's computed outputs."""

FORCEFIELD_OUTPUTS = ("total_energy", "forces", "stress")


def supervised_outputs(config):
    task = config["task"]
    if task["kind"] != "forcefield":
        if "supervised_outputs" in task:
            raise ValueError("task.supervised_outputs is only supported for forcefield tasks")
        return (task["property"],)
    selected = task.get("supervised_outputs", FORCEFIELD_OUTPUTS)
    if (not isinstance(selected, (list, tuple)) or not selected
            or any(not isinstance(name, str) or name not in FORCEFIELD_OUTPUTS for name in selected)):
        raise ValueError("task.supervised_outputs must be a nonempty list of total_energy, forces, stress")
    if len(set(selected)) != len(selected):
        raise ValueError("task.supervised_outputs must not contain duplicate outputs")
    return tuple(name for name in FORCEFIELD_OUTPUTS if name in selected)


def supervised_predictions(predictions, config):
    names = supervised_outputs(config)
    missing = set(names) - predictions.keys()
    if missing:
        raise ValueError(f"Missing predictions for supervised outputs: {sorted(missing)}")
    return {name: predictions[name] for name in names}
