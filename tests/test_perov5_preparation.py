import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.data.preparation.perov5 import REPOSITORY, prepare_perov5


def fixture_atoms(offset):
    return {"elements": ["Ba", "Ti", "O", "O", "O"],
            "coords": [[offset, 0., 0.], [2., 2., 2.], [0., 2., 2.], [2., 0., 2.], [2., 2., 0.]],
            "lattice_mat": [[4., 0., 0.], [0., 4., 0.], [0., 0., 4.]], "cartesian": True}


class Perov5PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.values = {role: [{"material_id": str(100 * i + j), "cif": json.dumps(fixture_atoms(.001 * (100 * i + j))),
                               "heat_all": "nan", "dir_gap": "not a number"} for j in range(12)]
                       for i, role in enumerate(("train", "val", "test"), start=1)}

    def tearDown(self):
        self.temporary.cleanup()

    def receipt(self):
        raw = self.root / "perov5"
        raw.mkdir(exist_ok=True)
        entries = []
        for role, rows in self.values.items():
            upstream = f"data/perov_5/{role}.csv"
            path = raw / upstream.replace("/", "-")
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["material_id", "cif", "heat_all", "dir_gap"])
                writer.writeheader()
                writer.writerows(rows)
            payload = path.read_bytes()
            entries.append({"repo": REPOSITORY, "commit": "b" * 40, "upstream_path": upstream,
                            "filename": path.name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
                            "git_blob_sha1": hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()})
        receipt = self.root / "receipt.json"
        receipt.write_text(json.dumps({"resources": entries}))
        return receipt

    def prepare(self, name="prepared"):
        with patch("universal_gnn.data.preparation.perov5.atoms_from_cif", side_effect=json.loads):
            audit = prepare_perov5(self.receipt(), self.root / name, execution={"slurm_job_id": "fixture"})
        rows = [json.loads(line) for line in (self.root / name / "structures.jsonl").read_text().splitlines()]
        manifest = json.loads((self.root / name / "split.json").read_text())
        return audit, rows, manifest

    def test_all_rows_and_released_roles_without_property_filters(self):
        audit, rows, manifest = self.prepare()
        self.assertEqual(audit["counts"], {"source_records": 36, "written_records": 36})
        self.assertEqual(audit["split_counts"], {"train": 12, "validation": 12, "test": 12})
        self.assertEqual(audit["maximum_atoms"], 5)
        self.assertEqual(audit["tasks"], ["generation"])
        self.assertEqual(manifest["protocol"]["kind"], "released_author_partitions")
        for role, indices in manifest["partitions"].items():
            for index in indices:
                row = rows[index]
                self.assertEqual(row["metadata"]["source_details"]["released_partition"], "val" if role == "validation" else role)
                self.assertEqual(row["targets"], {})
                self.assertEqual(row["numbers"], [56, 22, 8, 8, 8])
                self.assertEqual(row["pbc"], [True, True, True])
        _, _, again = self.prepare("again")
        self.assertEqual(manifest, again)

    def test_bad_cif_and_geometry_are_audited_by_id(self):
        self.values["train"][0]["cif"] = "invalid cif"
        invalid = fixture_atoms(0.)
        invalid["lattice_mat"] = [[0., 0., 0.]] * 3
        self.values["val"][1]["cif"] = json.dumps(invalid)
        audit, rows, _ = self.prepare()
        self.assertEqual(audit["counts"]["source_records"], 36)
        self.assertEqual(audit["counts"]["written_records"], 34)
        excluded = [json.loads(line) for line in (self.root / "prepared/exclusions.jsonl").read_text().splitlines()]
        self.assertEqual({row["id"] for row in excluded}, {"perov5:100", "perov5:201"})
        self.assertEqual(len(rows), 34)

    def test_cross_partition_geometry_never_silently_reassigned(self):
        self.values["test"][0]["cif"] = self.values["train"][0]["cif"]
        with self.assertRaisesRegex(ValueError, "Group leakage"):
            self.prepare()
        self.assertFalse((self.root / "prepared/audit.json").exists())

    def test_duplicate_material_id_rejected_even_with_same_geometry(self):
        self.values["train"].append(self.values["train"][0].copy())
        with self.assertRaisesRegex(ValueError, "Duplicate Perov-5 material_id"):
            self.prepare()

    def test_raw_hash_registry_and_paths_fail_closed(self):
        receipt = self.receipt()
        raw = self.root / "perov5/data-perov_5-train.csv"
        payload = bytearray(raw.read_bytes())
        payload[-1] = ord(" ")
        raw.write_bytes(payload)
        with self.assertRaisesRegex(ValueError, "checksum"):
            prepare_perov5(receipt, self.root / "bad-hash")
        receipt = self.receipt()
        registry = json.loads(receipt.read_text())
        registry["resources"][0]["filename"] = "../outside.csv"
        receipt.write_text(json.dumps(registry))
        with self.assertRaisesRegex(ValueError, "filename/path"):
            prepare_perov5(receipt, self.root / "bad-path")
        registry["resources"].pop()
        receipt.write_text(json.dumps(registry))
        with self.assertRaisesRegex(ValueError, "exactly three"):
            prepare_perov5(receipt, self.root / "bad-registry")

    def test_import_without_torch_numpy_or_ase_and_cli_requires_slurm(self):
        environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
        environment.pop("SLURM_JOB_ID", None)
        subprocess.run([sys.executable, "-S", "-c", "import sys; import universal_gnn.data.preparation.perov5; "
                        "assert not {'torch','numpy','ase'} & sys.modules.keys()"], env=environment, check=True, capture_output=True)
        value = subprocess.run([sys.executable, "-S", "-m", "universal_gnn.data.preparation", "missing.json",
                                "--kind", "perov5", "--output", "missing-output"], env=environment, capture_output=True, text=True)
        self.assertNotEqual(value.returncode, 0)
        self.assertIn("must run through Slurm", value.stderr)


if __name__ == "__main__":
    unittest.main()
