"""Full pinned MLearn E/F data with released test and grouped training validation."""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from universal_gnn.data.splits import create_manifest
from .jarvis import file_sha256, finite_scalar, prepare_records, records_from


ELEMENTS = ("Cu", "Ge", "Li", "Mo", "Ni", "Si")
REPOSITORY = "materialyzeai/mlearn"


def source_entries(receipt):
    entries = [item for item in receipt.get("resources", []) if item.get("repo") == REPOSITORY]
    expected = {f"data/{element}/{role}.json" for element in ELEMENTS for role in ("training", "test")}
    if len(entries) != 12 or {item.get("upstream_path") for item in entries} != expected:
        raise ValueError("MLearn requires exactly twelve released training/test resources")
    commits = {item.get("commit") for item in entries}
    if len(commits) != 1 or not re.fullmatch(r"[0-9a-f]{40}", next(iter(commits)) or ""):
        raise ValueError("MLearn resources must share a pinned Git commit")
    for item in entries:
        if item.get("filename") != item["upstream_path"].replace("/", "-"):
            raise ValueError("MLearn filename/path does not match the pinned source")
        if (not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")) or
                not re.fullmatch(r"[0-9a-f]{40}", item.get("git_blob_sha1", "")) or
                type(item.get("bytes")) is not int or item["bytes"] <= 0):
            raise ValueError("MLearn resource requires size, SHA256 and Git blob SHA1")
    return sorted(entries, key=lambda item: item["upstream_path"])


def verify_resource(path, item):
    if path.is_symlink() or path.stat().st_size != item["bytes"]:
        raise ValueError("MLearn raw resource size/symlink mismatch")
    sha, blob = hashlib.sha256(), hashlib.sha1(f"blob {item['bytes']}\0".encode())
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
            blob.update(block)
    if sha.hexdigest() != item["sha256"] or blob.hexdigest() != item["git_blob_sha1"]:
        raise ValueError("MLearn raw checksum/Git blob mismatch")


def atoms_from_record(record, element):
    if record.get("element", element) != element:
        raise ValueError("mlearn_element_mismatch")
    structure = record.get("structure")
    if not isinstance(structure, dict):
        raise ValueError("mlearn_missing_structure")
    sites, lattice = structure.get("sites"), structure.get("lattice")
    if not isinstance(sites, list) or not sites or not isinstance(lattice, dict):
        raise ValueError("mlearn_invalid_structure")
    elements, coords = [], []
    for site in sites:
        if not isinstance(site, dict):
            raise ValueError("mlearn_invalid_site")
        species = site.get("species")
        if (not isinstance(species, list) or len(species) != 1 or not isinstance(species[0], dict) or
                not finite_scalar(species[0].get("occu")) or
                not math.isclose(species[0]["occu"], 1., rel_tol=0., abs_tol=1e-8)):
            raise ValueError("mlearn_disordered_site")
        symbol = species[0].get("element")
        if symbol != element:
            raise ValueError("mlearn_element_mismatch")
        xyz = site.get("xyz")
        if not isinstance(xyz, list) or len(xyz) != 3 or not all(finite_scalar(x) for x in xyz):
            raise ValueError("mlearn_invalid_cartesian_site")
        elements.append(symbol)
        coords.append([float(x) for x in xyz])
    count = record.get("num_atoms", len(sites))
    if type(count) is not int or count != len(sites):
        raise ValueError("mlearn_atom_count_mismatch")
    return {"elements": elements, "coords": coords, "lattice_mat": lattice.get("matrix"), "cartesian": True}


def forcefield_targets(record):
    if record.get("conversion_error"):
        raise ValueError(record["conversion_error"])
    outputs = record.get("outputs")
    if not isinstance(outputs, dict) or not finite_scalar(outputs.get("energy")):
        raise ValueError("mlearn_missing_or_nonfinite_energy")
    forces = outputs.get("forces")
    count = len(record["atoms"]["elements"])
    if (not isinstance(forces, list) or len(forces) != count or
            any(not isinstance(row, list) or len(row) != 3 or not all(finite_scalar(x) for x in row)
                for row in forces)):
        raise ValueError("mlearn_missing_nonfinite_or_wrong_forces")
    return {"energy": float(outputs["energy"]), "forces": [[float(x) for x in row] for row in forces]}


def prepare_mlearn(source, output, *, split_seed=0, validation_fraction=.1, execution=None):
    if not finite_scalar(validation_fraction) or not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be finite and between zero and one")
    source = Path(source)
    receipt = json.loads(source.read_text(encoding="utf-8"))
    entries = source_entries(receipt)
    info, counts = {}, Counter()
    families = {"training": set(), "test": set()}
    details = {"tasks": ["energy", "forces"], "channels": None, "vector_transform": None,
               "units": {"energy": "eV total per structure", "forces": "eV/angstrom", "positions": "angstrom"},
               "stress": "virial_stress retained in raw source only; not converted or supervised",
               "source_files": [{key: item[key] for key in ("upstream_path", "sha256", "git_blob_sha1", "bytes", "commit")}
                                for item in entries],
               "validation_fraction_of_training_groups": validation_fraction,
               "grouping": "exact geometry plus training-only MD description families; not crystallographic equivalence",
               "author_test_policy": "all valid released test records remain test; no test labels used for validation assignment"}

    def records():
        for item in entries:
            _, element, filename = item["upstream_path"].split("/")
            role = filename.removesuffix(".json")
            path = source.parent / "mlearn" / item["filename"]
            verify_resource(path, item)
            for index, record in enumerate(records_from(path)):
                identifier = f"mlearn:{element}:{role}:{index:06d}"
                origin = {"file": item["filename"], "file_sha256": item["sha256"], "source_index": index,
                          "element": element, "released_partition": role}
                normalized = {"jid": identifier, "source_details": origin}
                if not isinstance(record, dict):
                    normalized["conversion_error"] = "mlearn_invalid_record"
                else:
                    origin.update({key: record.get(key) for key in ("description", "group", "tag")})
                    tag = record.get("tag")
                    if tag is not None and tag != ("train" if role == "training" else "test"):
                        raise ValueError("MLearn file and released tag disagree")
                    try:
                        normalized["atoms"] = atoms_from_record(record, element)
                    except ValueError as error:
                        normalized["conversion_error"] = str(error)
                    normalized["outputs"] = record.get("outputs")
                    description = record.get("description")
                    match = re.match(r"^Snapshot \d+ of \d+ of\s+(.+)$", description) if isinstance(description, str) else None
                    origin["trajectory_family"] = f"{element}:{match[1]}" if match else None
                info[identifier] = origin
                yield normalized

    def group_key(record):
        origin = record["source_details"]
        role, family = origin["released_partition"], origin.get("trajectory_family")
        counts[f"valid_{origin['element']}_{role}"] += 1
        if family:
            families[role].add(family)
        return family if role == "training" else None

    def split_builder(records, *, source_sha256, seed):
        groups = {}
        for record in records:
            groups.setdefault(record["group"], []).append(record["id"])
        train_groups = {element: [] for element in ELEMENTS}
        test_groups = set()
        for group, identifiers in groups.items():
            roles = {info[identifier]["released_partition"] for identifier in identifiers}
            if len(roles) != 1:
                raise ValueError("Exact duplicate geometry across released train/test; review source, do not silently reassign")
            elements = {info[identifier]["element"] for identifier in identifiers}
            if len(elements) != 1:
                raise ValueError("MLearn group crosses source elements")
            if roles == {"test"}:
                test_groups.add(group)
            else:
                train_groups[next(iter(elements))].append(group)
        validation = set()
        for element, groups_for_element in train_groups.items():
            if len(groups_for_element) < 2:
                raise ValueError(f"Need at least two training groups for {element}; do not fall back to random frames")
            ordered = sorted(groups_for_element, key=lambda group: (hashlib.sha256(f"{seed}\0{group}".encode()).hexdigest(), group))
            count = min(len(ordered) - 1, max(1, int(len(ordered) * validation_fraction)))
            validation.update(ordered[:count])
        official = {record["id"]: "test" if record["group"] in test_groups else
                    "validation" if record["group"] in validation else "train" for record in records}
        split = create_manifest(records, source_sha256=source_sha256, seed=seed, official=official)
        split["protocol"] = {"kind": "released_test_training_family_hash_v1", "split_seed": seed,
                             "validation_fraction_of_training_groups": validation_fraction, "stratification": "element"}
        details["valid_counts_by_source"] = dict(counts)
        details["train_test_trajectory_family_overlap"] = sorted(families["training"] & families["test"])
        details["trajectory_limit"] = "released train/test may share AIMD families; only training-vs-validation family independence enforced"
        return split

    return prepare_records(source, output, records(), kind="forcefield", field="outputs.energy/forces", channels=1,
                           url=f"https://github.com/{REPOSITORY}/tree/{entries[0]['commit']}/data",
                           targets=forcefield_targets, group_key=group_key, split_builder=split_builder,
                           split_seed=split_seed, execution={**(execution or {}), "mlearn_source_sha256": file_sha256(__file__)},
                           audit_details=details)
