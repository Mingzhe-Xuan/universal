"""Plot original accepted summary values; this does not repeat scientific acceptance."""

import hashlib
import json
import math
from pathlib import Path
import re
import sys

from .runtime import identity

MODELS = ("cgcnn", "alignn", "mace", "nequip")
DIMENSIONLESS_SCORES = {"roc_auc", "auroc", "average_precision", "accuracy", "balanced_accuracy", "f1", "precision", "recall", "mcc"}
DEFAULT_PANELS = (
    dict(task="forcefield", path="energy_per_atom.mae", unit="eV/atom", title="Energy per atom"),
    dict(task="forcefield", path="forces.mae", unit="eV/angstrom", title="Forces"),
    dict(task="dielectric", path="dielectric.mae", unit="dimensionless", title="Dielectric components"),
    dict(task="spectrum", path="spectrum.mae", unit="dataset_defined", title="Phonon spectrum"),
)


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("A plotted metric must be a finite number")
    return value


def _metric(row, path):
    value = row["metrics"]
    try:
        for part in path.split("."):
            value = value[part]
    except (KeyError, TypeError) as error:
        raise ValueError("Accepted row lacks selected metric: " + path) from error
    if value is None:
        return None
    value = _number(value)
    if path.split(".")[-1] in {"mae", "rmse"} and value < 0:
        raise ValueError("An absolute or root mean square error cannot be negative")
    return value


def prepare_plot(summary, panels=DEFAULT_PANELS):
    """Check the fixed scope and retain raw values, missing slots and same-seed pairs."""
    if (summary.get("kind") != "single_seed_accepted_primary_summary"
            or summary.get("version") != 1 or summary.get("training_seeds") != [123]
            or summary.get("required_cases") != 48):
        raise ValueError("Select an unchanged 48-case seed123 accepted-result summary")
    rows = {}
    for row in summary["rows"]:
        ident = identity(row["case_id"])
        if row["case_id"] in rows or any(row.get(key) != value for key, value in ident.items()):
            raise ValueError("Summary row identity is duplicate or inconsistent")
        accepted = row["status"] == "independently_accepted"
        if accepted:
            if not isinstance(row["metrics"], dict) or not row["metrics"]:
                raise ValueError("An accepted row must contain original metrics")
        elif (row["status"] != "not_independently_accepted"
                or row["metrics"] is not None or row["costs"] is not None):
            raise ValueError("Unaccepted slots must retain missing metrics and costs")
        rows[row["case_id"]] = row
    accepted_count = sum(row["status"] == "independently_accepted" for row in rows.values())
    if (len(rows) != 48 or summary["accepted_cases"] != accepted_count
            or summary["missing_cases"] != 48 - accepted_count):
        raise ValueError("Summary counts do not match the complete scope")
    pairs = {}
    for pair in summary["pairs"]:
        key = pair["task"], pair["model"]
        if key in pairs or pair.get("seed") != 123:
            raise ValueError("Pair identity is duplicate or has a different seed")
        expected = {mode: f"seed-123--{key[0]}--{key[1]}--{mode}" for mode in ["pretrained", "scratch"]}
        if any(pair.get(mode) != case or case not in rows for mode, case in expected.items()):
            raise ValueError("Pair does not refer to its original rows")
        missing = [case for case in expected.values() if rows[case]["status"] != "independently_accepted"]
        if pair["status"] != ("incomplete" if missing else "complete") or pair["missing"] != missing:
            raise ValueError("Pair completeness contradicts accepted rows")
        pairs[key] = pair
    if len(pairs) != 24 or summary["complete_pairs"] != sum(p["status"] == "complete" for p in pairs.values()):
        raise ValueError("Pair counts do not match the complete scope")
    if not panels or len(panels) > 12:
        raise ValueError("Select between one and twelve explicit metric panels")
    result = []
    for panel in panels:
        if set(panel) != {"task", "path", "unit", "title"} or not all(isinstance(v, str) and v for v in panel.values()):
            raise ValueError("Each panel needs task, path, unit and title strings")
        if (panel["task"], MODELS[0]) not in pairs:
            raise ValueError("Panel task is outside the fixed scope")
        points, differences = [], []
        for model in MODELS:
            pair = pairs[panel["task"], model]
            selected = {}
            for mode in ["pretrained", "scratch"]:
                row = rows[pair[mode]]
                value = None
                if row["status"] == "independently_accepted":
                    value = _metric(row, panel["path"])
                    target = panel["path"].split(".")[0]
                    block = row["metrics"].get(target, {})
                    unit = block.get("unit") if isinstance(block, dict) else None
                    unit = unit or row.get("target_bindings", {}).get(target, {}).get("unit")
                    if unit is None and panel["path"].split(".")[-1] in DIMENSIONLESS_SCORES:
                        unit = "dimensionless"
                    if unit != panel["unit"]:
                        raise ValueError("Panel unit must match the reported target unit; no inferred conversion")
                    if value is not None:
                        selected[mode] = value
                points.append(dict(case_id=row["case_id"], model=model, initialization=mode, value=value, status=row["status"]))
            if pair["status"] == "complete" and len(selected) == 2:
                expected = dict(pretrained=selected["pretrained"], scratch=selected["scratch"],
                                pretrained_minus_scratch=selected["pretrained"] - selected["scratch"])
                if pair["differences"].get(panel["path"]) != expected:
                    raise ValueError("Paired values or signed difference disagree with original summary")
                differences.append(dict(model=model, **expected))
            elif pair["status"] == "complete" and panel["path"] in pair["differences"]:
                raise ValueError("An undefined metric cannot have a numeric paired difference")
        result.append(dict(**panel, points=points, differences=differences))
    return dict(version=1, kind="accepted_summary_metric_figure_data", training_seeds=[123],
                required_cases=48, accepted_cases=accepted_count, missing_cases=48 - accepted_count,
                panels=result, scientific_acceptance_performed=False,
                interpretation="Selected original accepted metrics; missing slots remain null. Single training seed, no error bars or cross-seed claims. This presentation does not repeat the reporter's underlying scientific input verification.")


def write_figures(summary_path, expected_sha256, output, panels=DEFAULT_PANELS):
    """Save SVG/PNG, exact point data and a caption from an explicitly hash-bound summary."""
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Refusing to overwrite a figure directory")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("Provide the exact lower-case SHA256 of the accepted summary bytes")
    raw = Path(summary_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Summary bytes differ from the requested SHA256")
    data = prepare_plot(json.loads(raw), panels)
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    output.mkdir(parents=True, exist_ok=False)
    columns = min(2, len(data["panels"]))
    rows = (len(data["panels"]) + columns - 1) // columns
    with plt.rc_context({"font.size": 10, "svg.fonttype": "none"}):
        figure, axes = plt.subplots(rows, columns, figsize=(6.2 * columns, 3.5 * rows), squeeze=False)
        for axis, panel in zip(axes.flat, data["panels"]):
            for offset, mode, color, marker in [(-0.09, "pretrained", "#0072B2", "o"), (0.09, "scratch", "#D55E00", "s")]:
                points = [p for p in panel["points"] if p["initialization"] == mode and p["value"] is not None]
                axis.scatter([MODELS.index(p["model"]) + offset for p in points], [p["value"] for p in points],
                             label="Pretrained fine-tune" if mode == "pretrained" else "From scratch", c=color, marker=marker, zorder=3)
            for difference in panel["differences"]:
                x = MODELS.index(difference["model"])
                axis.plot([x - .09, x + .09], [difference["pretrained"], difference["scratch"]], color="0.65", zorder=1)
            axis.set_xticks(range(4), ["CGCNN", "ALIGNN", "MACE", "NequIP"])
            axis.set_xlim(-.5, 3.5)
            unit = "dataset units" if panel["unit"] == "dataset_defined" else panel["unit"]
            axis.set_ylabel(panel["path"].split(".")[-1].upper() + " (" + unit + ")")
            axis.set_title(panel["title"])
            axis.grid(axis="y", alpha=.25)
            if not any(p["value"] is not None for p in panel["points"]):
                axis.text(.5, .5, "No numerical accepted metric", ha="center", transform=axis.transAxes)
            elif min(p["value"] for p in panel["points"] if p["value"] is not None) >= 0:
                axis.set_ylim(bottom=0)
        for axis in list(axes.flat)[len(data["panels"]):]:
            axis.set_visible(False)
        handles, labels = axes[0, 0].get_legend_handles_labels()
        figure.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(.5, .95), frameon=False)
        figure.suptitle(f"Selected full-data metrics: {data['accepted_cases']}/48 cases accepted; training seed 123", y=.995)
        figure.tight_layout(rect=(0, .025, 1, .89))
        for extension in ["svg", "png"]:
            figure.savefig(output / ("accepted-metrics." + extension), dpi=180)
        plt.close(figure)
    data.update(summary_sha256=expected_sha256, matplotlib_version=matplotlib.__version__,
                renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), python_version=sys.version)
    (output / "summary.json").write_bytes(raw)
    (output / "plot-data.json").write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf8")
    caption = (f"Selected full-data test metrics; {data['accepted_cases']}/48 independently accepted cases. "
               "Training seed 123. Points are original pretrained fine-tune and scratch values; links join complete same-seed pairs. "
               "Missing or undefined metrics remain missing. Axes are linear; values retain original units with no renormalization. "
               "No cross-seed uncertainty or general pretraining advantage is claimed. "
               "This figure presents a hash-bound reporter summary; it does not independently reverify its scientific archives.\n")
    selected_tasks = {panel["task"] for panel in data["panels"]}
    if "dielectric" in selected_tasks:
        caption += "Dielectric component errors use the recorded coordinate frame.\n"
    if "spectrum" in selected_tasks:
        caption += "Phonon spectrum units are dataset-defined.\n"
    (output / "caption.md").write_text(caption, encoding="utf8")
    if Path(summary_path).read_bytes() != raw:
        raise ValueError("Input summary changed during rendering")
    return data
