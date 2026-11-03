import copy
import hashlib
import json
import os
from pathlib import Path
import pickle
import tempfile
import unittest

from universal_gnn.data.preparation.gmtnet import prepare_gmtnet


def values(count=15):
    return [{"JARVIS_ID": f"JVASP-{i}", "dielectric": [[i, 2., 3.], [4., 5., 6.], [7., 8., 9.]],
             "dielectric_ionic": [[999.] * 3] * 3,
             "atoms": {"elements": ["Si"] * (24 if i == 14 else 1),
                       "coords": [[j * .1, i * .1, 0.] for j in range(24 if i == 14 else 1)],
                       "lattice_mat": [[8., 0., 0.], [0., 8., 0.], [0., 0., 8.]],
                       "cartesian": True}} for i in range(count)]


class GMTNetPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def source(self, records):
        path = self.root / "source.pkl"
        path.write_bytes(pickle.dumps(records))
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def prepare(self, records, name="prepared"):
        path, digest = self.source(records)
        return prepare_gmtnet(path, self.root / name, expected_sha256=digest,
                              execution={"slurm_job_id": "fixture"})

    def test_full_coverage_large_structure_tensor_order_no_ionic_sum(self):
        source = values()
        source[0]["dielectric"] = [[0.] * 3] * 3
        audit = self.prepare(source)
        rows = [json.loads(line) for line in (self.root / "prepared/structures.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 15)
        self.assertEqual(audit["maximum_atoms"], 24)
        self.assertEqual(rows[0]["targets"]["dielectric"], [[0.] * 3] * 3)
        self.assertEqual(rows[1]["targets"]["dielectric"], source[1]["dielectric"])
        self.assertNotEqual(rows[1]["targets"]["dielectric"][0][1], rows[1]["targets"]["dielectric"][1][0])
        self.assertEqual(audit["tensor_shape"], [3, 3])
        self.assertEqual(audit["tasks"], ["dielectric"])
        self.assertEqual(sum(audit["split_counts"].values()), 15)
        self.assertEqual(audit["dataset_sha256"], hashlib.sha256((self.root / "prepared/structures.jsonl").read_bytes()).hexdigest())
        self.assertEqual(audit["execution"]["slurm_job_id"], "fixture")
        self.assertEqual(len(audit["execution"]["gmtnet_source_sha256"]), 64)

    def test_bad_tensor_labels_are_audited_without_filtering_zero(self):
        source = values()
        source[0]["dielectric"] = [[0.] * 3] * 3
        source[1]["dielectric"] = [[1.] * 3] * 2
        source[2]["dielectric"][0][0] = float("nan")
        source[3]["dielectric"][0][0] = True
        source[4]["dielectric"] = "na"
        source[5]["atoms"]["elements"] = ["Unknown"]
        audit = self.prepare(source)
        self.assertEqual(audit["counts"]["source_records"], 15)
        self.assertEqual(audit["counts"]["written_records"], 10)
        self.assertEqual(audit["counts"]["missing_nonfinite_or_wrong_tensor_shape"], 4)
        self.assertEqual(audit["counts"]["unknown_element"], 1)

    def test_duplicate_material_and_geometry_groups_remain_together(self):
        source = values()
        source[0]["atoms"] = copy.deepcopy(source[1]["atoms"])
        source[1]["reference"] = source[2]["reference"] = "mp-42"
        source.append(copy.deepcopy(source[3]))
        audit = self.prepare(source)
        self.assertEqual(audit["counts"]["identical_duplicate_id"], 1)
        manifest = json.loads((self.root / "prepared/split.json").read_text())
        roles = {index: role for role, indices in manifest["partitions"].items() for index in indices}
        self.assertEqual(len({roles[i] for i in (0, 1, 2)}), 1)
        source[-1]["dielectric"][0][0] += 1
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            self.prepare(source, "conflict")
        self.assertFalse((self.root / "conflict/audit.json").exists())

    def test_source_digest_mismatch_rejects_before_loading(self):
        path, _ = self.source(values())
        with self.assertRaisesRegex(ValueError, "checksum"):
            prepare_gmtnet(path, self.root / "wrong", expected_sha256="0" * 64)
        self.assertFalse((self.root / "wrong/audit.json").exists())

    def test_unexpected_pickle_classes_and_trailing_objects_rejected(self):
        for index, payload in enumerate((pickle.dumps(Path("forbidden")),
                                         pickle.dumps(values()) + pickle.dumps(values()))):
            path = self.root / "untrusted.pkl"
            path.write_bytes(payload)
            with self.assertRaises((ValueError, pickle.UnpicklingError)):
                prepare_gmtnet(path, self.root / f"bad-{index}",
                               expected_sha256=hashlib.sha256(payload).hexdigest())
            self.assertFalse((self.root / f"bad-{index}/audit.json").exists())

    def test_plain_collection_protocols_and_no_overwrite(self):
        source = values()
        source[0]["atoms"]["lattice_mat"] = tuple(tuple(row) for row in source[0]["atoms"]["lattice_mat"])
        self.prepare(source)
        with self.assertRaises(FileExistsError):
            self.prepare(source)

    @unittest.skipUnless(os.environ.get("SLURM_JOB_ID"), "NumPy binary fixture executes on Slurm")
    def test_released_numpy_scalars_arrays_and_ordered_collection_protocol(self):
        from collections import OrderedDict
        import numpy as np

        source = values()
        source[0] = OrderedDict(source[0])
        source[0]["dielectric"] = np.arange(9, dtype=np.float64).reshape(3, 3)
        source[0]["atoms"]["coords"] = np.asarray(source[0]["atoms"]["coords"])
        source[0]["atoms"]["lattice_mat"][0][0] = np.float64(8.)
        source[0]["atoms"]["cartesian"] = np.bool_(True)
        self.prepare(source)
        first = json.loads((self.root / "prepared/structures.jsonl").read_text().splitlines()[0])
        self.assertEqual(first["targets"]["dielectric"], [[0., 1., 2.], [3., 4., 5.], [6., 7., 8.]])


if __name__ == "__main__":
    unittest.main()
