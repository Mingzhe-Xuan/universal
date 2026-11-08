"""Metadata refusal fixtures only; synthetic numbers are not scientific results."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from universal_gnn.benchmarks.reporting.figures import DEFAULT_PANELS, prepare_plot, write_figures


def fixture(accepted_tasks=("forcefield", "dielectric", "spectrum")):
    rows, pairs = [], []
    for task in ["classification", "bandgap", "dielectric", "spectrum", "forcefield", "generation"]:
        for model in ["cgcnn", "alignn", "mace", "nequip"]:
            chosen = {}
            for mode in ["pretrained", "scratch"]:
                case = f"seed-123--{task}--{model}--{mode}"
                row = dict(case_id=case, task=task, model=model, initialization=mode, seed=123,
                           status="not_independently_accepted", metrics=None, costs=None)
                if task in accepted_tasks:
                    row.update(status="independently_accepted", metrics={}, target_bindings={})
                    for panel in DEFAULT_PANELS:
                        if panel["task"] == task:
                            target = panel["path"].split(".")[0]
                            row["metrics"][target] = dict(mae=0. if mode == "pretrained" else .25)
                            row["target_bindings"][target] = dict(unit=panel["unit"])
                    row["costs"] = {}
                rows.append(row)
                chosen[mode] = row
            complete = task in accepted_tasks
            differences = {}
            if complete:
                for panel in DEFAULT_PANELS:
                    if panel["task"] == task:
                        differences[panel["path"]] = dict(pretrained=0., scratch=.25, pretrained_minus_scratch=-.25)
            pairs.append(dict(task=task, model=model, seed=123, pretrained=chosen["pretrained"]["case_id"],
                              scratch=chosen["scratch"]["case_id"], status="complete" if complete else "incomplete",
                              missing=[] if complete else [row["case_id"] for row in chosen.values()], differences=differences))
    count = sum(row["status"] == "independently_accepted" for row in rows)
    return dict(version=1, kind="single_seed_accepted_primary_summary", training_seeds=[123], required_cases=48,
                accepted_cases=count, missing_cases=48-count, complete_pairs=count//2, rows=rows, pairs=pairs)


class FigureMetadataTests(unittest.TestCase):
    def test_exact_original_values_and_zero_retained(self):
        source = fixture();before = copy.deepcopy(source);data = prepare_plot(source)
        self.assertEqual(source, before)
        self.assertEqual((data["accepted_cases"], data["missing_cases"]), (24, 24))
        self.assertEqual(len(data["panels"]), 4)
        self.assertFalse(data["scientific_acceptance_performed"])
        for panel in data["panels"]:
            self.assertEqual([p["value"] for p in panel["points"]], [0., .25]*4)
            self.assertEqual([p["pretrained_minus_scratch"] for p in panel["differences"]], [-.25]*4)

    def test_missing_slots_remain_null(self):
        data = prepare_plot(fixture(()))
        self.assertEqual(data["accepted_cases"], 0)
        self.assertTrue(all(p["value"] is None for panel in data["panels"] for p in panel["points"]))
        self.assertTrue(all(not panel["differences"] for panel in data["panels"]))

    def test_identity_count_status_and_pair_contradictions_rejected(self):
        changes = [lambda s:s.update(training_seeds=[123,456]), lambda s:s.update(accepted_cases=48),
                   lambda s:s["rows"].append(copy.deepcopy(s["rows"][0])), lambda s:s["rows"].pop(),
                   lambda s:s["rows"][0].update(seed=456), lambda s:s["rows"][0].update(model="mace"),
                   lambda s:s["rows"][0].update(metrics={"fake":1}), lambda s:s["rows"][0].update(status="passed"),
                   lambda s:s["pairs"].append(copy.deepcopy(s["pairs"][0])),
                   lambda s:s["pairs"][0].update(status="complete", missing=[]),
                   lambda s:s["pairs"][0].update(pretrained=s["pairs"][1]["pretrained"])]
        for mutate in changes:
            with self.subTest(mutate=mutate):
                summary=fixture();mutate(summary)
                with self.assertRaises(ValueError):prepare_plot(summary)

    def test_nonfinite_boolean_negative_and_missing_metric_rejected(self):
        for value in [float("nan"),float("inf"),True,-.1,"1"]:
            summary=fixture();row=next(r for r in summary["rows"] if r["task"]=="forcefield")
            row["metrics"]["energy_per_atom"]["mae"]=value
            with self.subTest(value=value),self.assertRaises(ValueError):prepare_plot(summary)
        summary=fixture();next(r for r in summary["rows"] if r["task"]=="forcefield")["metrics"].pop("energy_per_atom")
        with self.assertRaises(ValueError):prepare_plot(summary)

    def test_units_and_signed_differences_rejected(self):
        summary=fixture();next(r for r in summary["rows"] if r["task"]=="forcefield")["target_bindings"]["forces"]["unit"]="other"
        with self.assertRaises(ValueError):prepare_plot(summary)
        for key in ["pretrained","scratch","pretrained_minus_scratch"]:
            summary=fixture();pair=next(p for p in summary["pairs"] if p["task"]=="dielectric")
            pair["differences"]["dielectric.mae"][key]=999
            with self.subTest(key=key),self.assertRaises(ValueError):prepare_plot(summary)

    def test_explicit_panels_and_invalid_selections(self):
        self.assertEqual(len(prepare_plot(fixture(),DEFAULT_PANELS[:1])["panels"]),1)
        for panels in [[], [dict(DEFAULT_PANELS[0],unit="meV/atom")], [dict(DEFAULT_PANELS[0],path="not.a.metric")],
                       [dict(DEFAULT_PANELS[0],task="unknown")], [dict(DEFAULT_PANELS[0],scale=1000)]]:
            with self.subTest(panels=panels),self.assertRaises(ValueError):prepare_plot(fixture(),panels)

    def test_sha_and_overwrite_refusal_before_plot_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/"summary.json";source.write_text(json.dumps(fixture()),encoding="utf8")
            with self.assertRaises(ValueError):write_figures(source,"0"*64,root/"new")
            self.assertFalse((root/"new").exists())
            with self.assertRaises(FileExistsError):write_figures(source,"0"*64,root)

    def test_custom_classification_scores_and_undefined_auc(self):
        panel=dict(task="classification",path="roc_auc",unit="dimensionless",title="AUROC")
        for undefined in [False, True]:
            summary=fixture(())
            for row in summary["rows"]:
                if row["task"]=="classification":
                    value=None if undefined else (.8 if row["initialization"]=="pretrained" else .6)
                    row.update(status="independently_accepted",metrics=dict(roc_auc=value),costs={})
            for pair in summary["pairs"]:
                if pair["task"]=="classification":
                    pair.update(status="complete",missing=[],differences={} if undefined else {
                        "roc_auc":dict(pretrained=.8,scratch=.6,pretrained_minus_scratch=.8-.6)})
            summary.update(accepted_cases=8,missing_cases=40,complete_pairs=4)
            data=prepare_plot(summary,[panel])["panels"][0]
            self.assertEqual(len(data["differences"]),0 if undefined else 4)
            self.assertEqual([p["value"] for p in data["points"]],[None]*8 if undefined else [.8,.6]*4)

    def test_single_accepted_member_keeps_point_without_pair(self):
        summary=fixture(())
        selected=next(r for r in summary["rows"] if r["task"]=="forcefield")
        selected.update(status="independently_accepted",costs={},metrics={
            "energy_per_atom":dict(mae=.1,unit="eV/atom"),"forces":dict(mae=.2,unit="eV/angstrom")})
        pair=next(p for p in summary["pairs"] if p["task"]=="forcefield")
        pair["missing"]=[pair["scratch"]];summary.update(accepted_cases=1,missing_cases=47)
        data=prepare_plot(summary)
        self.assertEqual(data["panels"][0]["points"][0]["value"],.1)
        self.assertEqual(len(data["panels"][0]["differences"]),0)


if __name__ == "__main__":
    unittest.main()
