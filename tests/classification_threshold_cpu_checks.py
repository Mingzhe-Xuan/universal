"""Explicit Slurm CPU fixture controls; no GNN load/forward or scientific claim."""

import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import runpy


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if not os.environ.get("SLURM_JOB_ID") or os.environ.get("CUDA_VISIBLE_DEVICES"):
        raise RuntimeError("CPU fixture checks require a CUDA-hidden Slurm allocation")
    args.output.mkdir(parents=True, exist_ok=False)
    import torch
    from unittest.mock import patch
    from test_classification_threshold import fixture, assess
    from universal_gnn.benchmarks.prediction_assessment.rescoring import class_observation
    from universal_gnn.benchmarks.execution.gates import file_sha

    def forbidden(*unused, **kwargs):
        raise AssertionError("Fixture control must never load or execute a model")

    cases = {}
    with patch.object(torch, "load", side_effect=forbidden), patch.object(torch.nn.Module, "__call__", side_effect=forbidden):
        for dtype in ["float32", "float64"]:
            selections = []
            for reverse in [False, True]:
                name = dtype + ("-counterfactual" if reverse else "-original")
                with fixture(dtype=dtype, reverse_test_labels=reverse, directory=args.output/name) as (root, report, stream, trained, rows):
                    result = assess(report, stream, root / "assessment")
                    expected, _ = class_observation(rows[4]["predictions"]["classification"], dtype)
                    assert result["selection"]["rule"] == dict(kind="score_at_least", value=expected)
                    assert result["selection"]["balanced_accuracy"] == 1
                    assert result["metrics"]["roc_auc"] == (0 if reverse else 1)
                    assert result["metrics"]["balanced_accuracy"] == .5
                    assert result["same_stream_argmax_metrics"]["balanced_accuracy"] == (0 if reverse else 1)
                    assert result["unchanged_original_heldout_metrics"] == trained["heldout"]["metrics"]["classification"]
                    assert result["formal_training_runs"] == 0 and not result["model_execution_performed"]
                    selections.append(result["selection"])
                    cases[name] = dict(status="passed", report=str(root/"assessment/report.json"),
                                      report_sha256=file_sha(root/"assessment/report.json"), dtype=dtype)
            assert selections[0] == selections[1]
        entry = runpy.run_path("scripts/evaluate_classification_threshold.py", run_name="cpu_control")
        for dtype in ["float32", "float64"]:
            name = dtype + "-public-cli"
            with fixture(dtype=dtype, directory=args.output/name) as (root, report, stream, _, _):
                with redirect_stdout(io.StringIO()):
                    entry["main"](["--report", str(report), "--predictions", str(stream),
                        "--prediction-sha256", file_sha(stream), "--prediction-bytes", str(stream.stat().st_size),
                        "--output", str(root/"assessment")])
                result = json.loads((root/"assessment/report.json").read_bytes())
                assert result["execution"]["device"] == "cpu" and result["execution"]["slurm_job_id"] == os.environ["SLURM_JOB_ID"]
                assert len(result["execution"]["source_sha256"]) == 7
                cases[name] = dict(status="passed", report=str(root/"assessment/report.json"),
                                  report_sha256=file_sha(root/"assessment/report.json"), dtype=dtype)
    result = dict(status="passed", actual_cpu_fixture_cases=len(cases), cases=cases,
        torch_version=torch.__version__, model_execution_performed=False, formal_training_runs=0,
        scientific_acceptance=False, interpretation="Six small actual CPU softmax/protocol fixtures only; original full classification results remain pending.")
    (args.output/"report.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps(dict(status="passed", actual_cpu_fixture_cases=len(cases), output=str(args.output))))


if __name__ == "__main__":
    main()
