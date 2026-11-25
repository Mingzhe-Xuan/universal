"""Parse original XYZ without RDKit; retain every author-characterized molecule."""

import json
import math
import os
from pathlib import Path
import tarfile
import time

from universal_gnn.data.splits.manifest import create_manifest
from .source import (CLEAN_COUNT, HARTREE_TO_EV, RAW_COUNT, SOURCE_URL, UNITS,
                     digest, excluded_ids, verify_sources)

NUMBERS = dict(H=1, C=6, N=7, O=8, F=9)


def numeric(value):
    number = float(value.replace("*^", "e").replace("D", "E").replace("d", "e"))
    if not math.isfinite(number):
        raise ValueError("QM9 contains a nonfinite numeric field")
    return number


def parse_xyz(text):
    lines = text.splitlines()
    count = int(lines[0])
    if not 1 <= count <= 29 or len(lines) < count + 5:
        raise ValueError("Invalid or truncated QM9 XYZ")
    props = lines[1].split()
    if len(props) != 17 or props[0] not in {"gdb", "gdb9"}:
        raise ValueError("Unknown original QM9 property header")
    index = int(props[1])
    if not 1 <= index <= RAW_COUNT:
        raise ValueError("QM9 original index outside release")
    numbers, positions = [], []
    for line in lines[2:count + 2]:
        atom = line.split()
        if len(atom) != 5 or atom[0] not in NUMBERS:
            raise ValueError("Unknown QM9 element or atom layout")
        numbers.append(NUMBERS[atom[0]])
        positions.append([numeric(x) for x in atom[1:4]])
        numeric(atom[4])
    values = [numeric(x) for x in props[2:]]
    mu, alpha, homo, lumo = values[3:7]
    if mu < 0 or alpha <= 0:
        raise ValueError("Invalid QM9 dipole magnitude or isotropic polarizability")
    smiles = lines[count + 3].split()
    if len(smiles) != 2:
        raise ValueError("Require both original and relaxed QM9 SMILES")
    return dict(schema_version=1, id=f"qm9:{index:06d}", numbers=numbers, positions=positions,
                cell=[[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]], pbc=[False] * 3,
                targets=dict(homo=homo * HARTREE_TO_EV, lumo=lumo * HARTREE_TO_EV,
                             dipole_magnitude=mu, isotropic_polarizability=alpha),
                metadata=dict(source_index=index, source_url=SOURCE_URL,
                              smiles=smiles[0], relaxed_smiles=smiles[1],
                              method="B3LYP/6-31G(2df,p)", units=UNITS,
                              cell_convention="nonperiodic identity placeholder; coordinates unmodified"))


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def prepare_qm9(raw_directory, output):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Complete QM9 conversion/checks require CPU Slurm")
    start = time.perf_counter()
    raw_directory, output = Path(raw_directory), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(status="running", kind="qm9_four_scalar_preparation", slurm_job_id=os.environ["SLURM_JOB_ID"])
    write_json(output / "report.json", report)
    try:
        sources = verify_sources(raw_directory)
        excluded = excluded_ids((raw_directory / "uncharacterized.txt").read_text())
        records, seen, counts = [], set(), dict(atoms=0, maximum_atoms=0)
        with tarfile.open(raw_directory / "dsgdb9nsd.xyz.tar.bz2", "r|bz2") as archive, \
                (output / "structures.jsonl.partial").open("wb") as stream:
            for member in archive:
                if member.isdir():
                    continue
                if not member.isfile() or not member.name.endswith(".xyz") or member.size > 100000:
                    raise ValueError("Unexpected entry in original QM9 archive")
                row = parse_xyz(archive.extractfile(member).read().decode("utf-8"))
                index = row["metadata"]["source_index"]
                if index in seen:
                    raise ValueError("Duplicate original QM9 molecule ID")
                seen.add(index)
                if index in excluded:
                    continue
                stream.write((json.dumps(row, separators=(",", ":"), sort_keys=True, allow_nan=False) + "\n").encode())
                records.append(dict(id=row["id"], group=row["metadata"]["smiles"]))
                counts["atoms"] += len(row["numbers"])
                counts["maximum_atoms"] = max(counts["maximum_atoms"], len(row["numbers"]))
        if seen != set(range(1, RAW_COUNT + 1)) or len(records) != CLEAN_COUNT:
            raise ValueError("QM9 complete source/cleaned coverage differs")
        (output / "structures.jsonl.partial").replace(output / "structures.jsonl")
        source_sha = digest(output / "structures.jsonl")
        split = create_manifest(records, source_sha256=source_sha, seed=0)
        split["protocol"]["interpretation"] = "UGNN fixed original-SMILES group hash 80/10/10; not an author/standard QM9 split"
        write_json(output / "split.json", split)
        split_sha = __import__("hashlib").sha256(json.dumps(split, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        report.update(status="passed", sources=sources, raw_count=len(seen), excluded_count=len(excluded),
                      clean_count=len(records), counts=counts, units=UNITS, hartree_to_ev=HARTREE_TO_EV,
                      dataset=dict(path=str(output / "structures.jsonl"), sha256=source_sha,
                                   split_manifest=str(output / "split.json"), split_manifest_sha256=split_sha),
                      split_counts=split["counts"], split_file_sha256=digest(output / "split.json"),
                      exclusion_ids=sorted(excluded), wall_seconds=time.perf_counter() - start)
    except Exception as error:
        report.update(status="failed", error_type=type(error).__name__, error=str(error))
        write_json(output / "report.json", report)
        raise
    write_json(output / "report.json", report)
    return report
