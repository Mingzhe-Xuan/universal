"""Complete frozen ethanol source and author-partition audit, without model imports."""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path

from ..execution.gates import file_sha
from ..experiments.registry import canonical_digest
from ..prediction_assessment.contracts import finite_shape
from universal_gnn.data.preparation.rmd17.conversion import KCAL_MOL_TO_EV
from universal_gnn.data.preparation.rmd17.partitions import build_manifest, frame_id, parse_indices
from universal_gnn.data.preparation.rmd17.source import SOURCE_FILES, SOURCE_URL, verify_sources
from universal_gnn.data.splits import validate_manifest


DATA_ROOT = "data/arxiv-v1/rmd17-ethanol-prepared-4f30bea"
RAW_ROOT = "data/arxiv-v1/molecular-rmd17-v4/raw"
SOURCE_SHA = "71747e9ce58fd67aba9b87ef367036915a1ba9348c6ce74968a63691b6def4db"
SPLIT_FILE_SHA = "d1072a6c351ed760e60929cbade2b1bd1da542931efd715a5e181db1b469e58a"
AUDIT_SHA = "4368a66d86207526be824b35798afa023a93eaeeb8e397bdf70d4905f79fdd66"
COUNTS = dict(train=900, validation=100, test=99000)
IDENTITY_CELL = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]


def _inspect_records(path, manifest, *, source_sha256, source_count):
    """Small synthetic fixtures may exercise this scanner; campaign always uses100000."""
    validate_manifest(manifest, source_sha256=source_sha256, source_count=source_count)
    digest, count = hashlib.sha256(), 0
    old_indices, records = set(), []
    energies = forces = zero_forces = 0
    species = None
    with Path(path).open("rb") as stream:
        for raw in stream:
            digest.update(raw)
            row = json.loads(raw)
            if (not isinstance(row, dict) or count >= source_count
                    or type(row.get("schema_version")) is not int or row["schema_version"] != 1):
                raise ValueError("Molecular complete record count/schema differs")
            if row.get("id") != frame_id(count) or row["id"] != manifest["records"][count]["id"]:
                raise ValueError("Molecular complete ordered source frame IDs differ")
            numbers = row.get("numbers")
            if (not isinstance(numbers, list) or any(type(z) is not int for z in numbers)
                    or Counter(numbers) != {1: 6, 6: 2, 8: 1}):
                raise ValueError("Molecular original ethanol species differ")
            if species is None:
                species = numbers
            if numbers != species:
                raise ValueError("Molecular constant source atom order changed")
            if row.get("pbc") != [False, False, False] or any(type(v) is not bool for v in row["pbc"]):
                raise ValueError("Molecular input must be explicitly nonperiodic")
            finite_shape(row.get("positions"), (9, 3))
            finite_shape(row.get("cell"), (3, 3))
            if row["cell"] != IDENTITY_CELL:
                raise ValueError("Molecular source placeholder cell changed")
            targets = row.get("targets")
            if not isinstance(targets, dict) or set(targets) != {"energy", "forces"}:
                raise ValueError("Molecular source requires revised E/F labels only")
            energies += finite_shape(targets["energy"], ())
            forces += finite_shape(targets["forces"], (9, 3))
            zero_forces += all(value == 0 for values in targets["forces"] for value in values)
            metadata = row.get("metadata", {})
            if not isinstance(metadata, dict):
                raise ValueError("Molecular source metadata must be a mapping")
            old_index = metadata.get("old_index")
            if (type(metadata.get("source_index")) is not int or metadata["source_index"] != count
                    or type(old_index) is not int or old_index < 0 or old_index in old_indices
                    or metadata.get("source_url") != SOURCE_URL or metadata.get("molecule") != "ethanol"
                    or metadata.get("archive_sha256") != SOURCE_FILES["rmd17_ethanol.npz"]["sha256"]
                    or metadata.get("label_field") != "revised energies/forces; old labels not used"):
                raise ValueError("Molecular original source/frame/revised-label provenance differs")
            atoms = {name: row[name] for name in ("numbers", "positions", "cell", "pbc")}
            group = canonical_digest(atoms)
            if metadata.get("geometry_sha256") != group or manifest["records"][count]["group"] != group:
                raise ValueError("Molecular exact geometry fingerprint/group differs")
            old_indices.add(old_index)
            records.append(dict(id=row["id"], group=group))
            count += 1
    if count != source_count or digest.hexdigest() != source_sha256:
        raise ValueError("Molecular full source count/byte SHA differs")
    return dict(structures=count, atoms=count * 9, energy_components=energies, force_components=forces,
        whole_zero_force_records=zero_forces, maximum_atoms=9, atomic_numbers_present=sorted(set(species)),
        source_sha256=digest.hexdigest(), excluded_records=0), records


def inspect_molecular_inputs(data_directory=DATA_ROOT, raw_directory=RAW_ROOT):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Complete molecular source inspection requires Slurm")
    root = Path(data_directory)
    if (file_sha(root / "audit.json") != AUDIT_SHA or file_sha(root / "split.json") != SPLIT_FILE_SHA):
        raise ValueError("Frozen independent-accepted molecular conversion audit/split changed")
    audit = json.loads((root / "audit.json").read_bytes())
    if (audit.get("status") != "passed" or audit.get("stage") != "complete"
            or audit.get("dataset_sha256") != SOURCE_SHA or audit.get("split_sha256") != SPLIT_FILE_SHA
            or audit.get("source_to_target_factor") != KCAL_MOL_TO_EV
            or audit.get("split_counts") != COUNTS or audit.get("source_records") != 100000
            or audit.get("written_records") != 100000 or audit.get("excluded_records") != 0):
        raise ValueError("Molecular full conversion count/units/source contract differs")
    package = Path(__file__).resolve().parents[2]
    for name, expected in audit["source_sha256"].items():
        if file_sha(package / name) != expected:
            raise ValueError("Original molecular conversion implementation changed")
    author_files = verify_sources(raw_directory)
    official = {role: parse_indices((Path(raw_directory) / ("index_" + role + "_01.csv")).read_text(),
                                   source_count=100000) for role in ("train", "test")}
    manifest = json.loads((root / "split.json").read_bytes())
    observed, records = _inspect_records(root / "structures.jsonl", manifest, source_sha256=SOURCE_SHA, source_count=100000)
    if (manifest != build_manifest(records, source_sha256=SOURCE_SHA,
                                  official_train=official["train"], official_test=official["test"])
            or manifest["counts"] != COUNTS or observed["energy_components"] != 100000
            or observed["force_components"] != 2700000):
        raise ValueError("Complete molecular author development/test/ID-hash validation partition differs")
    if observed["whole_zero_force_records"] != audit["whole_zero_force_records"]:
        raise ValueError("Molecular zero-force labels were removed or changed")
    return dict(version=1, kind="arxiv_v1_complete_molecular_inputs", status="passed",
        dataset=dict(path=(root / "structures.jsonl").as_posix(), sha256=SOURCE_SHA,
            split_manifest=(root / "split.json").as_posix(), split_manifest_sha256=canonical_digest(manifest)),
        audit_sha256=AUDIT_SHA, split_file_sha256=SPLIT_FILE_SHA, counts=dict(COUNTS), **observed,
        official_test_cohort_count=1000, author_development_count=1000, author_files=author_files,
        unit_conversion_factor=KCAL_MOL_TO_EV, training_rng_used_for_split=False,
        units=dict(positions="angstrom", total_energy="eV", forces="eV/angstrom"),
        interpretation="Complete100000 source/author bytes,900train/100validation/99000test and original1000testcohort. No DFT, bulk-stress accuracy, independent-trajectory or new-molecule claim. No model/graph/capacity/training acceptance.")
