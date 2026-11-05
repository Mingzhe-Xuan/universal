"""Full released-source conversion with joint, immutable dielectric anchors."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import time

from universal_gnn.data.preparation.gmtnet import records_from_pickle
from universal_gnn.data.preparation.jarvis import file_sha256, geometry, prepare_records
from universal_gnn.data.splits import validate_manifest
from ..experiments.registry import canonical_digest
from .partitions import AnchorConflict, build_partitions, task_manifest
from .targets import elastic_targets, piezoelectric_targets

SOURCE_HASHES = dict(
    piezoelectric="2a57e081f0072b2ac7fca7769095adcded1d299d2cd971db5c93fd25eb66929d",
    elastic="5def6ffc1136c482298bc20c389037ce3dc14fab1a63b52d15f0b32a40757db5",
    dielectric="e2f3ec9569e67e31d353bad3f1f05da6856da64e7f34cb0fd59589e3c3edaa77",
    dielectric_split="95963b54eedee9bdf12dd82ac320776170842f4d8be4727a3df8fc3febdd6d49")
TASKS = dict(
    piezoelectric=dict(field="piezoelectric_C_m2", channels=27, shape=[3, 3, 3], unit="C/m^2", factor=1.,
                       targets=piezoelectric_targets, url="https://raw.githubusercontent.com/YKQ98/GMTNet/main/data/jarvis_diele_piezo.pkl"),
    elastic=dict(field="elastic_total_kbar", channels=81, shape=[3, 3, 3, 3], unit="GPa", factor=.1,
                 targets=elastic_targets, url="https://raw.githubusercontent.com/YKQ98/GMTNet/main/data/jarvis_elastic.pkl"))


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(json.dumps(value, indent=2, allow_nan=False).encode())
    temporary.replace(path)


def load_anchors(data, split, expected):
    if file_sha256(data) != expected["dielectric"]:
        raise ValueError("Primary dielectric data checksum mismatch")
    manifest = json.loads(Path(split).read_text(encoding="utf8"))
    if canonical_digest(manifest) != expected["dielectric_split"]:
        raise ValueError("Primary dielectric split checksum mismatch")
    validate_manifest(manifest, source_sha256=expected["dielectric"], source_count=manifest["source_count"])
    roles = {i: role for role, indices in manifest["partitions"].items() for i in indices}
    anchors = []
    with Path(data).open(encoding="utf8") as stream:
        for index, line in enumerate(stream):
            row = json.loads(line)
            if index >= len(manifest["records"]) or row["id"] != manifest["records"][index]["id"]:
                raise ValueError("Primary dielectric ordered IDs differ from frozen split")
            atoms = {key: row[key] for key in ("numbers", "positions", "cell", "pbc")}
            fingerprint = hashlib.sha256(json.dumps(atoms, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if fingerprint != row["metadata"]["geometry_sha256"]:
                raise ValueError("Primary dielectric exact geometry fingerprint mismatch")
            anchors.append(dict(id=row["id"], geometry=fingerprint, reference=row["metadata"].get("external_reference"),
                                role=roles[index], group=manifest["records"][index]["group"]))
    if len(anchors) != manifest["source_count"]:
        raise ValueError("Primary dielectric data coverage mismatch")
    return anchors, manifest


def candidates(source, *, kind, expected_sha256):
    metadata, known, counts = [], {}, Counter()
    for record in records_from_pickle(source, expected_sha256=expected_sha256):
        counts["source_records"] += 1
        identifier = record.get("jid") if isinstance(record, dict) else None
        if not isinstance(identifier, str) or not identifier:
            counts["missing_jid"] += 1
            continue
        try:
            targets = TASKS[kind]["targets"](record)
            _, fingerprint = geometry(record.get("atoms"))
        except ValueError as error:
            counts[str(error)] += 1
            continue
        content = hashlib.sha256(json.dumps(dict(geometry=fingerprint, targets=targets), sort_keys=True).encode()).hexdigest()
        if identifier in known:
            if known[identifier] != content:
                raise ValueError("Conflicting source records for " + identifier)
            counts["identical_duplicate_id"] += 1
            continue
        known[identifier] = content
        metadata.append(dict(id=identifier, geometry=fingerprint, reference=record.get("reference")))
    counts["written_records"] = len(metadata)
    return metadata, dict(counts)


def prepare_supplemental_tensors(piezo_source, elastic_source, dielectric_data, dielectric_split,
                                 output, *, split_seed=0, execution=None, expected_hashes=None):
    """Visit every source record; retain full Cartesian labels and original geometry."""
    started = time.perf_counter()
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Supplemental preparation requires a fresh empty output")
    output.mkdir(parents=True, exist_ok=True)
    expected = dict(SOURCE_HASHES if expected_hashes is None else expected_hashes)
    if set(expected) != set(SOURCE_HASHES):
        raise ValueError("Require all raw and primary anchor checksums")
    paths = dict(piezoelectric=Path(piezo_source), elastic=Path(elastic_source),
                 dielectric=Path(dielectric_data), dielectric_split=Path(dielectric_split))
    report = dict(status="running", stage="source_integrity", formal_training_runs=0, datasets_prepared=0,
                  expected_hashes=expected, sources={key: str(path) for key, path in paths.items()},
                  execution=execution or {})
    def record(**fields):
        report.update(fields)
        write_json(output / "report.json", report)
    try:
        record()
        for kind in TASKS:
            if file_sha256(paths[kind]) != expected[kind]:
                raise ValueError(kind + " raw source checksum mismatch")
        anchors, anchor_manifest = load_anchors(dielectric_data, dielectric_split, expected)
        record(stage="complete_cross_source_candidates")
        rows, counts = {}, {}
        for kind in TASKS:
            rows[kind], counts[kind] = candidates(paths[kind], kind=kind, expected_sha256=expected[kind])
        record(stage="immutable_anchor_grouping", candidate_counts=counts)
        partitions = build_partitions(rows, anchors, seed=split_seed)
        partitions["anchor_source_sha256"] = expected["dielectric"]
        partitions["anchor_split_sha256"] = expected["dielectric_split"]
        write_json(output / "cross-task-partitions.json", partitions)
        audits = {}
        for kind, specification in TASKS.items():
            record(stage="convert_" + kind)
            def split_builder(records, *, source_sha256, seed):
                return task_manifest(records, source_sha256=source_sha256, seed=seed,
                                     partition_records=partitions["records"][kind], protocol={
                                         **partitions["protocol"], "anchor_source_sha256": expected["dielectric"],
                                         "anchor_split_sha256": expected["dielectric_split"]})
            audits[kind] = prepare_records(
                paths[kind], output / kind, records_from_pickle(paths[kind], expected_sha256=expected[kind]),
                kind=kind, field=specification["field"], channels=specification["channels"], url=specification["url"],
                targets=specification["targets"], split_seed=split_seed, split_builder=split_builder,
                execution=execution, audit_details=dict(
                    tasks=[kind], tensor_shape=specification["shape"], tensor_unit=specification["unit"],
                    source_field=specification["field"], source_to_target_unit_factor=specification["factor"],
                    source_pair_order=["xx", "yy", "zz", "xy", "yz", "xz"],
                    vector_transform="contracted source minor-index duplication only; no factor2, averaging, symmetry projection, magnitude/zero/atom-count filter",
                    model_output_convention="free Cartesian27/81 outputs; label encoding imposes no model symmetry constraint",
                    primary_anchor_counts=partitions["counts"][kind]))
            if audits[kind]["counts"] != counts[kind]:
                raise ValueError("Full source passes disagree on candidate/exclusion accounting")
        for kind in ("piezoelectric", "elastic", "dielectric"):
            if file_sha256(paths[kind]) != expected[kind]:
                raise ValueError("Input bytes changed during complete preparation")
        if canonical_digest(json.loads(paths["dielectric_split"].read_text(encoding="utf8"))) != expected["dielectric_split"]:
            raise ValueError("Primary anchor changed during preparation")
        repository = Path(__file__).resolve().parents[4]
        sources = [Path(__file__), Path(__file__).with_name("targets.py"), Path(__file__).with_name("partitions.py")]
        sources += [repository / "src/universal_gnn/data" / name for name in
                    ("preparation/gmtnet.py", "preparation/jarvis.py", "splits/manifest.py")]
        record(status="passed", stage="complete", datasets_prepared=2, audits=audits,
               original_dielectric_counts=anchor_manifest["counts"],
               cross_task_partitions_sha256=file_sha256(output / "cross-task-partitions.json"),
               source_sha256={str(path.resolve().relative_to(repository)).replace("\\", "/"): file_sha256(path)
                              for path in sources},
               elapsed_seconds=time.perf_counter() - started,
               interpretation="Full source conversion and anchored splits only; no model, graph, capacity, numerical derivative or training acceptance")
        return report
    except Exception as error:
        if isinstance(error, AnchorConflict):
            write_json(output / "anchor-conflicts.json", error.conflicts)
        record(status="failed", error_type=type(error).__name__, error=str(error))
        raise
