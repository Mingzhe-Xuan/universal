import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from universal_gnn.data.preparation.jarvis import (ATOMIC_NUMBERS, geometry, iter_json_array,
                                                  prepare_release)


def records(count=15):
    return [{"jid": f"J-{i}", "optb88vdw_bandgap": i * .01,
             "pdos_elast": [i * .1] * 200,
             "atoms": {"lattice_mat": [[8., 0., 0.], [0., 8., 0.], [0., 0., 8.]],
                       "elements": ["Si"] * (24 if i == 14 else 2),
                       "coords": [[j * .1, i * .01, 0.] for j in range(24 if i == 14 else 2)],
                       "cartesian": True}} for i in range(count)]


class FullJarvisPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def source(self, values):
        path = self.root / "release.zip"
        with zipfile.ZipFile(path, "w") as output:
            output.writestr("records.json", json.dumps(values))
        return path

    def test_entire_release_zero_gap_large_structure_and_shared_partition(self):
        source = self.source(records())
        output = self.root / "prepared"
        audit = prepare_release(source, output, kind="bandgap", split_seed=4, metal_threshold=.01,
                                execution={"slurm_job_id": "fixture"})
        rows = [json.loads(line) for line in (output / "structures.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 15)
        self.assertEqual(audit["maximum_atoms"], 24)
        self.assertEqual(audit["atomic_numbers_present"], [14])
        self.assertEqual(audit["atom_occurrences_by_number"], {"14": 52})
        self.assertEqual(rows[0]["targets"], {"bandgap": 0., "classification": 0})
        self.assertEqual(rows[1]["targets"]["classification"], 0)
        self.assertEqual(rows[2]["targets"]["classification"], 1)
        self.assertEqual(audit["dataset_sha256"], hashlib.sha256((output / "structures.jsonl").read_bytes()).hexdigest())
        split = json.loads((output / "split.json").read_text())
        self.assertEqual(sum(split["counts"].values()), 15)
        self.assertEqual(audit["tasks"], ["bandgap", "classification"])
        self.assertEqual(audit["execution"]["slurm_job_id"], "fixture")
        self.assertEqual(len(audit["execution"]["preparation_source_sha256"]), 64)
        with self.assertRaises(FileExistsError):
            prepare_release(source, output, kind="bandgap")

    def test_invalid_labels_geometry_and_duplicate_ids_are_audited(self):
        values = records()
        values[0]["optb88vdw_bandgap"] = "na"
        values[1]["atoms"]["lattice_mat"] = [[0., 0., 0.]] * 3
        values.append(copy.deepcopy(values[2]))
        audit = prepare_release(self.source(values), self.root / "prepared", kind="bandgap")
        self.assertEqual(audit["counts"]["source_records"], 16)
        self.assertEqual(audit["counts"]["written_records"], 13)
        self.assertEqual(audit["counts"]["missing_or_nonfinite_label"], 1)
        self.assertEqual(audit["counts"]["singular_cell"], 1)
        self.assertEqual(audit["counts"]["identical_duplicate_id"], 1)
        values[-1]["optb88vdw_bandgap"] += 1
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            prepare_release(self.source(values), self.root / "conflict", kind="bandgap")
        self.assertFalse((self.root / "conflict/audit.json").exists())

    def test_dos_exact_channels_and_values_without_resampling(self):
        values = records()
        values[0]["pdos_elast"] = "na"
        values[1]["pdos_elast"] = [0.] * 199
        values[2]["pdos_elast"][0] = float("nan")
        output = self.root / "dos"
        audit = prepare_release(self.source(values), output, kind="phonon_dos")
        rows = [json.loads(line) for line in (output / "structures.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0]["targets"]["spectrum"], values[3]["pdos_elast"])
        self.assertEqual(audit["channels"], 200)
        self.assertEqual(audit["counts"]["missing_nonfinite_or_wrong_channels"], 3)

    def test_geometry_and_material_reference_groups_do_not_cross_partitions(self):
        values = records()
        values[0]["reference"] = values[1]["reference"] = "mp-123"
        values[1]["atoms"] = copy.deepcopy(values[2]["atoms"])
        output = self.root / "grouped"
        prepare_release(self.source(values), output, kind="bandgap")
        split = json.loads((output / "split.json").read_text())
        self.assertEqual(len({split["records"][i]["group"] for i in (0, 1, 2)}), 1)
        roles = {i: role for role, indices in split["partitions"].items() for i in indices}
        self.assertEqual(len({roles[i] for i in (0, 1, 2)}), 1)

    def test_fractional_conversion_elements_and_strict_streaming_array(self):
        atoms = records(1)[0]["atoms"]
        atoms.update(elements=["H", "Og"], coords=[[.5, .25, 0.], [0., 0., .5]], cartesian=False)
        normalized, _ = geometry(atoms)
        self.assertEqual(normalized["numbers"], [1, 118])
        self.assertEqual(normalized["positions"], [[4., 2., 0.], [0., 0., 4.]])
        self.assertEqual(ATOMIC_NUMBERS["U"], 92)
        self.assertEqual(list(iter_json_array(io.StringIO(' [ {"value": 1} , 2 ] \n'))), [{"value": 1}, 2])
        for text in ('[{"value":', '[1,]', '[1] false', '[1 2]', '{}'):
            with self.assertRaises(ValueError):
                list(iter_json_array(io.StringIO(text)))


if __name__ == "__main__":
    unittest.main()
