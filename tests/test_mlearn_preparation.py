import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from universal_gnn.data.preparation.mlearn import ELEMENTS, REPOSITORY, prepare_mlearn


def record(element, index, role):
    atoms = 24 if index == 11 else 2
    sites = [{"species": [{"element": element, "occu": 1}], "xyz": [j * .1, index * .01, .5 if role == "test" else 0.]}
             for j in range(atoms)]
    family = "AIMD at 300 K" if index < 4 else "AIMD at 800 K"
    return {"structure": {"lattice": {"matrix": [[8.,0.,0.],[0.,8.,0.],[0.,0.,8.]]}, "sites": sites},
            "outputs": {"energy": -2. * atoms, "forces": [[0., 1., -1.]] * atoms, "virial_stress": [5.] * 6},
            "element": element, "num_atoms": atoms, "tag": "train" if role == "training" else "test",
            "group": "Vacancy", "description": f"Snapshot {index+1} of 4 of {family}" if index < 8 else f"strain {index}"}


class MLearnPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.values = {(element, role): [record(element, index, role) for index in range(12 if role == "training" else 3)]
                       for element in ELEMENTS for role in ("training", "test")}

    def tearDown(self):
        self.temporary.cleanup()

    def receipt(self):
        folder = self.root / "mlearn"
        folder.mkdir(exist_ok=True)
        entries = []
        for (element, role), records in self.values.items():
            upstream = f"data/{element}/{role}.json"
            filename = upstream.replace("/", "-")
            payload = json.dumps(records).encode()
            (folder / filename).write_bytes(payload)
            entries.append({"repo": REPOSITORY, "commit": "f" * 40, "upstream_path": upstream, "filename": filename,
                            "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
                            "git_blob_sha1": hashlib.sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()})
        source = self.root / "receipt.json"
        source.write_text(json.dumps({"resources": entries}))
        return source

    def prepare(self, name="prepared", seed=0):
        source = self.receipt()
        audit = prepare_mlearn(source, self.root / name, split_seed=seed, execution={"slurm_job_id": "fixture"})
        rows = [json.loads(line) for line in (self.root/name/"structures.jsonl").read_text().splitlines()]
        manifest = json.loads((self.root/name/"split.json").read_text())
        return audit, rows, manifest

    def test_all_six_elements_full_released_test_large_structures_and_exact_targets(self):
        audit, rows, manifest = self.prepare()
        self.assertEqual(audit["counts"], {"source_records":90,"written_records":90})
        self.assertEqual(audit["maximum_atoms"], 24)
        self.assertEqual(audit["split_counts"]["test"], 18)
        self.assertEqual(sum(audit["split_counts"].values()), 90)
        self.assertEqual(audit["tasks"], ["energy", "forces"])
        self.assertEqual(len(audit["source_files"]), 12)
        self.assertEqual(audit["execution"]["slurm_job_id"], "fixture")
        self.assertEqual(len(audit["execution"]["mlearn_source_sha256"]), 64)
        for row in rows:
            self.assertEqual(row["targets"]["energy"], -2. * len(row["numbers"]))
            self.assertEqual(row["targets"]["forces"], [[0., 1., -1.]] * len(row["numbers"]))
            self.assertEqual(row["pbc"], [True, True, True])
            self.assertNotIn("stress", row["targets"])
        roles = {i:role for role,indices in manifest["partitions"].items() for i in indices}
        for i,row in enumerate(rows):
            self.assertEqual(roles[i]=="test", row["metadata"]["source_details"]["released_partition"]=="test")

    def test_training_validation_families_disjoint_but_released_test_overlap_disclosed(self):
        audit, rows, manifest = self.prepare()
        sets = {role:set() for role in manifest["partitions"]}
        elements = {role:set() for role in manifest["partitions"]}
        for role,indices in manifest["partitions"].items():
            for index in indices:
                source=rows[index]["metadata"]["source_details"]
                elements[role].add(source["element"])
                if source.get("trajectory_family"):sets[role].add(source["trajectory_family"])
        self.assertFalse(sets["train"] & sets["validation"])
        self.assertEqual(elements["train"], set(ELEMENTS))
        self.assertEqual(elements["validation"], set(ELEMENTS))
        self.assertEqual(elements["test"], set(ELEMENTS))
        self.assertEqual(len(audit["train_test_trajectory_family_overlap"]), 6)
        self.assertEqual(manifest["protocol"]["kind"], "released_test_training_family_hash_v1")
        _,_,again=self.prepare("again")
        self.assertEqual(manifest,again)
        _,_,different=self.prepare("different",seed=4)
        self.assertEqual(manifest["partitions"]["test"],different["partitions"]["test"])

    def test_invalid_targets_disorder_and_atomcount_are_excluded_with_ids(self):
        records=self.values[("Cu","training")]
        records[0]["outputs"]["energy"]=float("nan")
        records[1]["outputs"]["forces"]=[[0.,0.,0.]]
        records[2]["structure"]["sites"][0]["species"][0]["occu"]=.5
        records[3]["num_atoms"]=100
        records[4]["outputs"]["energy"]=0.
        records[4]["outputs"]["forces"]=[[0.,0.,0.]]*2
        audit,rows,_=self.prepare()
        self.assertEqual(audit["counts"]["source_records"],90)
        self.assertEqual(audit["counts"]["written_records"],86)
        excluded=[json.loads(line) for line in (self.root/"prepared/exclusions.jsonl").read_text().splitlines()]
        self.assertEqual({item["id"] for item in excluded},{f"mlearn:Cu:training:{i:06d}" for i in range(4)})
        zero=next(row for row in rows if row["id"]=="mlearn:Cu:training:000004")
        self.assertEqual(zero["targets"],{"energy":0.,"forces":[[0.,0.,0.]]*2})

    def test_exact_geometry_across_released_train_test_fails_instead_of_reassignment(self):
        self.values[("Cu","test")][0]["structure"]=copy.deepcopy(self.values[("Cu","training")][0]["structure"])
        with self.assertRaisesRegex(ValueError,"across released train/test"):
            self.prepare()
        self.assertFalse((self.root/"prepared/audit.json").exists())

    def test_raw_hash_registry_path_and_tag_mismatch_fail_closed(self):
        source=self.receipt()
        raw=self.root/"mlearn/data-Cu-training.json"
        raw.write_bytes(raw.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,"size"):
            prepare_mlearn(source,self.root/"bad-hash")
        source=self.receipt()
        registry=json.loads(source.read_text())
        registry["resources"][0]["filename"]="../outside.json"
        source.write_text(json.dumps(registry))
        with self.assertRaisesRegex(ValueError,"filename/path"):
            prepare_mlearn(source,self.root/"bad-path")
        registry["resources"].pop()
        source.write_text(json.dumps(registry))
        with self.assertRaisesRegex(ValueError,"twelve"):
            prepare_mlearn(source,self.root/"bad-registry")
        self.values[("Cu","training")][0]["tag"]="test"
        with self.assertRaisesRegex(ValueError,"tag disagree"):
            self.prepare("bad-tag")

    def test_insufficient_training_groups_never_falls_back_to_frame_split(self):
        for item in self.values[("Cu","training")]:
            item["description"]="Snapshot 1 of 12 of same trajectory"
        with self.assertRaisesRegex(ValueError,"at least two training groups"):
            self.prepare()
        with self.assertRaisesRegex(ValueError,"validation_fraction"):
            prepare_mlearn(self.receipt(),self.root/"bad-fraction",validation_fraction=True)

    def test_preparation_import_is_independent_of_torch_and_site_packages(self):
        environment={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1]/"src")}
        subprocess.run([sys.executable,"-S","-c",
                        "import sys; import universal_gnn.data.preparation.mlearn; "
                        "assert 'torch' not in sys.modules; assert 'numpy' not in sys.modules"],
                       env=environment,check=True,capture_output=True)


if __name__=="__main__":
    unittest.main()
