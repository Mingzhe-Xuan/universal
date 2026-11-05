"""Joint material groups inherit immutable primary dielectric partition roles."""

from collections import Counter, defaultdict
import re

from universal_gnn.data.splits import create_manifest
from universal_gnn.data.splits.manifest import PARTITIONS


class AnchorConflict(ValueError):
    def __init__(self, conflicts):
        self.conflicts = conflicts
        super().__init__("Conflicting immutable dielectric anchors: " + repr(conflicts))


def identity_keys(row):
    identifier, geometry = row.get("id"), row.get("geometry")
    if (not isinstance(identifier, str) or not identifier or not isinstance(geometry, str) or
            not re.fullmatch("[0-9a-f]{64}", geometry)):
        raise ValueError("Candidate requires a nonempty ID and exact geometry SHA256")
    result = [("id", identifier), ("geometry", geometry)]
    reference = row.get("reference")
    result += [("reference", token) for token in sorted(set(re.findall(
        r"\bmp-\d+\b", reference if isinstance(reference, str) else "")))]
    return result


def build_partitions(candidates, anchors, *, seed=0):
    """Return per-task IDs/groups/roles; never move an existing primary record."""
    if set(candidates) != {"piezoelectric", "elastic"}:
        raise ValueError("Require both complete supplemental task candidate sets")
    if not anchors or {row.get("role") for row in anchors} != set(PARTITIONS):
        raise ValueError("Require the complete nonempty three-role dielectric anchor")
    rows = [("dielectric", row) for row in anchors]
    rows += [(kind, row) for kind in sorted(candidates) for row in candidates[kind]]
    seen_ids, parents, first, anchor_keys = set(), list(range(len(rows))), {}, set()
    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index
    def join(a, b):
        a, b = find(a), find(b)
        if a != b:
            parents[max(a, b)] = min(a, b)
    for index, (kind, row) in enumerate(rows):
        keys = identity_keys(row)
        if (kind, row["id"]) in seen_ids:
            raise ValueError("Candidate IDs must be unique within each complete source")
        seen_ids.add((kind, row["id"]))
        if kind == "dielectric":
            if not isinstance(row.get("group"), str) or not row["group"]:
                raise ValueError("Primary anchor requires its original group")
            anchor_keys.update(keys)
            keys += [("primary_group", row["group"])]
        for key in keys:
            if key in first:
                join(index, first[key])
            first[key] = index
    groups = defaultdict(list)
    for index in range(len(rows)):
        groups[find(index)].append(index)
    conflicts, names, anchored_roles = [], {}, {}
    for indices in groups.values():
        name = "material:" + min(rows[i][1]["id"] for i in indices)
        roles = {rows[i][1]["role"] for i in indices if rows[i][0] == "dielectric"}
        if len(roles) > 1:
            conflicts.append(dict(group=name, roles=sorted(roles),
                                  members=[dict(task=rows[i][0], id=rows[i][1]["id"]) for i in indices]))
        if roles:
            anchored_roles[name] = next(iter(roles))
        for index in indices:
            names[index] = name
    if conflicts:
        raise AnchorConflict(conflicts)
    base = create_manifest([dict(id="node:" + str(i), group=names[i]) for i in range(len(rows))],
                           source_sha256="0" * 64, seed=seed)
    base_roles = {base["records"][i]["group"]: role for role, indices in base["partitions"].items() for i in indices}
    result = {kind: [] for kind in ("dielectric", "piezoelectric", "elastic")}
    counts = {kind: Counter() for kind in result}
    for index, (kind, row) in enumerate(rows):
        name = names[index]
        role = anchored_roles.get(name, base_roles[name])
        direct = sorted({key[0] for key in identity_keys(row) if key in anchor_keys})
        result[kind].append(dict(id=row["id"], group=name, role=role,
                                 anchored_group=name in anchored_roles, direct_anchor_kinds=direct))
        counts[kind][role] += 1
        counts[kind]["anchored_group_records" if name in anchored_roles else "unanchored_group_records"] += 1
        for label in direct:
            counts[kind]["direct_" + label + "_anchor_records"] += 1
        if kind == "dielectric" and row["role"] != role:
            raise AssertionError("An immutable primary anchor moved")
    return dict(records=result, counts={kind: dict(value) for kind, value in counts.items()},
                global_groups=len(groups), anchored_groups=len(anchored_roles),
                unanchored_groups=len(groups) - len(anchored_roles),
                protocol=dict(kind="joint_primary_anchored_group_hash_v1", split_seed=seed,
                              requested_unanchored_base_group_ratios=[.8, .1, .1],
                              grouping=["ID", "exact Cartesian geometry", "explicit MP references", "primary groups"],
                              interpretation="Global group-hash base roles overridden only by immutable primary anchors; report actual per-task counts. Exact geometry grouping is not crystallographic equivalence"))


def task_manifest(records, *, source_sha256, seed, partition_records, protocol):
    assignments = {row["id"]: row for row in partition_records}
    if set(assignments) != {row["id"] for row in records}:
        raise ValueError("Converted data IDs differ from the complete partition candidates")
    normalized = [dict(id=row["id"], group=assignments[row["id"]]["group"]) for row in records]
    manifest = create_manifest(normalized, source_sha256=source_sha256, seed=seed,
                               official={identifier: row["role"] for identifier, row in assignments.items()})
    manifest["protocol"] = protocol
    return manifest
