"""Pinned Perov-5 CIF release, preserving the author's three partitions."""

import csv
import io
import json
import math
from pathlib import Path
import re

from universal_gnn.data.splits import create_manifest
from .jarvis import file_sha256, prepare_records
from .mlearn import verify_resource


REPOSITORY = "txie-93/cdvae"
PARTITIONS = {"train": "train", "val": "validation", "test": "test"}


def source_entries(receipt):
    entries = [item for item in receipt.get("resources", []) if item.get("repo") == REPOSITORY]
    expected = {f"data/perov_5/{role}.csv" for role in PARTITIONS}
    if len(entries) != 3 or {item.get("upstream_path") for item in entries} != expected:
        raise ValueError("Perov-5 requires exactly three released train/val/test CSV resources")
    commits = {item.get("commit") for item in entries}
    if len(commits) != 1 or not re.fullmatch(r"[0-9a-f]{40}", next(iter(commits)) or ""):
        raise ValueError("Perov-5 resources must share a pinned Git commit")
    for item in entries:
        if item.get("filename") != item["upstream_path"].replace("/", "-"):
            raise ValueError("Perov-5 filename/path does not match the pinned source")
        if (not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")) or
                not re.fullmatch(r"[0-9a-f]{40}", item.get("git_blob_sha1", "")) or
                type(item.get("bytes")) is not int or item["bytes"] <= 0):
            raise ValueError("Perov-5 resource requires size, SHA256 and Git blob SHA1")
    return sorted(entries, key=lambda item: item["upstream_path"])


def atoms_from_cif(cif):
    """Use upstream ASE CIF semantics, rejecting silent majority-species disorder."""
    from ase.io.cif import read_cif

    if not isinstance(cif, str) or not cif.strip():
        raise ValueError("perov5_missing_cif")
    try:
        images = read_cif(io.BytesIO(cif.encode("utf-8")), index=slice(None),
                          store_tags=True, primitive_cell=False, fractional_occupancies=True)
    except (ValueError, KeyError, IndexError, AssertionError, TypeError, StopIteration) as error:
        raise ValueError("perov5_invalid_cif") from error
    if len(images) != 1:
        raise ValueError("perov5_requires_one_cif_structure")
    atoms = images[0]
    occupancies = atoms.info.get("occupancy", {})
    for species in occupancies.values():
        if (len(species) != 1 or any(not math.isfinite(value) or
                not math.isclose(value, 1., rel_tol=0., abs_tol=1e-8) for value in species.values())):
            raise ValueError("perov5_disordered_occupancy")
    if len(atoms) != 5:
        raise ValueError("perov5_requires_five_atoms")
    if atoms.pbc.tolist() != [True, True, True]:
        raise ValueError("perov5_requires_three_dimensional_periodicity")
    return {"elements": atoms.get_chemical_symbols(), "coords": atoms.positions.tolist(),
            "lattice_mat": atoms.cell.array.tolist(), "cartesian": True}


def prepare_perov5(source, output, *, execution=None):
    source = Path(source)
    entries = source_entries(json.loads(source.read_text(encoding="utf-8")))
    for item in entries:
        verify_resource(source.parent / "perov5" / item["filename"], item)
    roles, identifiers = {}, set()
    details = {"tasks": ["generation"], "channels": None, "vector_transform": None,
               "source_files": [{key: item[key] for key in ("upstream_path", "sha256", "git_blob_sha1", "bytes", "commit")}
                                for item in entries],
               "units": {"positions": "angstrom", "cell": "angstrom, row vectors"},
               "label_policy": "no scalar property read, filtered, normalized or used as a generation condition",
               "cif_policy": "ASE CIF reader; retain conventional released cell and atom order; no primitive reduction",
               "conditioning": "given composition and atom count; not unconditional generation",
               "grouping": "exact Cartesian geometry; no crystallographic equivalence claim"}

    def records():
        for item in entries:
            role = Path(item["upstream_path"]).stem
            path = source.parent / "perov5" / item["filename"]
            with path.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                if not reader.fieldnames or not {"material_id", "cif"}.issubset(reader.fieldnames):
                    raise ValueError("Perov-5 CSV requires material_id and cif columns")
                for index, row in enumerate(reader):
                    material_id = row.get("material_id")
                    if not isinstance(material_id, str) or not material_id.strip():
                        raise ValueError("Perov-5 source row lacks material_id")
                    identifier = "perov5:" + material_id.strip()
                    if identifier in identifiers:
                        raise ValueError("Duplicate Perov-5 material_id; review author partitions")
                    identifiers.add(identifier)
                    roles[identifier] = PARTITIONS[role]
                    record = {"jid": identifier, "source_details": {
                        "file": item["filename"], "file_sha256": item["sha256"], "source_index": index,
                        "material_id": material_id, "released_partition": role}}
                    try:
                        record["atoms"] = atoms_from_cif(row.get("cif"))
                    except ValueError as error:
                        record["conversion_error"] = str(error)
                    yield record

    def targets(record):
        if record.get("conversion_error"):
            raise ValueError(record["conversion_error"])
        return {}

    def split_builder(records, *, source_sha256, seed):
        assignments = {record["id"]: roles[record["id"]] for record in records}
        return create_manifest(records, source_sha256=source_sha256, seed=seed, official=assignments)

    return prepare_records(source, output, records(), kind="generation", field="cif", channels=1,
                           url=f"https://github.com/{REPOSITORY}/tree/{entries[0]['commit']}/data/perov_5",
                           targets=targets, split_builder=split_builder, audit_details=details,
                           execution={**(execution or {}), "perov5_source_sha256": file_sha256(__file__)})
