"""Bounded candidate selection from a complete source-ordered training graph-size stream."""

import copy
import hashlib
import heapq
import json
import re

METRICS = ("atoms", "native_edges", "native_triplets", "auxiliary_edges", "maximum_degree")


def _positive(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def select_probe(rows, records, binding, *, worst_per_metric=2, ordinary_count=32, seed=0,
                 warmup_batches=2, measure_batches=100):
    """Verify every expected identity while retaining only extremes and ordinary candidates.

    Supplied counts are not evidence that an original graph builder actually ran. The
    numerical scanner must attach that separate execution provenance before certification.
    """
    for name, value in (("worst_per_metric", worst_per_metric), ("ordinary_count", ordinary_count),
                        ("warmup_batches", warmup_batches), ("measure_batches", measure_batches)):
        _positive(value, name)
    if type(seed) is not int or seed < 0:
        raise ValueError("Selection seed must be a nonnegative integer")
    if not isinstance(binding, dict):
        raise ValueError("Graph-size binding must be a mapping")
    for key in ("source_sha256", "split_manifest_sha256", "graph_definition_sha256"):
        if not isinstance(binding.get(key), str) or not re.fullmatch("[0-9a-f]{64}", binding[key]):
            raise ValueError(f"Graph-size binding requires {key}")
    if binding.get("dtype") not in {"float32", "float64"} or binding.get("native_edge_kind") not in {"directed_edges", "padded_neighbor_slots"}:
        raise ValueError("Graph-size binding requires input precision and explicit native edge semantics")
    if not isinstance(records, list) or not records:
        raise ValueError("Require the complete nonempty source-ordered training identity list")
    ids, sources = set(), set()
    for record in records:
        if (not isinstance(record, dict) or not isinstance(record.get("id"), str) or not record["id"] or
                type(record.get("source_index")) is not int or record["source_index"] < 0 or
                record["id"] in ids or record["source_index"] in sources):
            raise ValueError("Training identities require unique IDs and source indices")
        ids.add(record["id"]);sources.add(record["source_index"])
    heaps = {metric:[] for metric in METRICS}
    ordinary, digest = [], hashlib.sha256()
    sums, maxima = {metric:0 for metric in METRICS}, {metric:0 for metric in METRICS}

    def retain(heap, rank, record, count):
        entry = (rank, record["index"], record)
        if len(heap) < count:
            heapq.heappush(heap, entry)
        elif entry[:2] > heap[0][:2]:
            heapq.heapreplace(heap, entry)

    seen = 0
    for index, row in enumerate(rows):
        if (index >= len(records) or not isinstance(row, dict) or type(row.get("index")) is not int or
                row["index"] != index or row.get("id") != records[index]["id"] or
                type(row.get("source_index")) is not int or row["source_index"] != records[index]["source_index"]):
            raise ValueError("Graph-size stream differs from the complete source-ordered train partition")
        values = {key:row.get(key) for key in METRICS}
        if any(type(value) is not int or value < (1 if key == "atoms" else 0) for key, value in values.items()):
            raise ValueError("Graph-size counts must be nonnegative integers with positive atom count")
        edges = values["native_edges"] + values["auxiliary_edges"]
        if (values["maximum_degree"] > edges or (edges > 0 and values["maximum_degree"] == 0) or
                (values["native_triplets"] > 0 and values["native_edges"] == 0)):
            raise ValueError("Graph-size degree/triplet counts are inconsistent")
        compact = dict(index=index, source_index=row["source_index"], id=row["id"], **values)
        digest.update(json.dumps(compact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n")
        key = json.dumps(["ugnn-graph-probe-v1", seed, row["id"]], separators=(",", ":")).encode()
        priority = int.from_bytes(hashlib.sha256(key).digest(), "big")
        for metric, value in values.items():
            sums[metric] += value;maxima[metric] = max(maxima[metric], value)
            if value:
                retain(heaps[metric], (value, -priority, -row["source_index"]), compact, worst_per_metric)
        retain(ordinary, (-priority, -row["source_index"]), compact,
               ordinary_count + len(METRICS) * worst_per_metric)
        seen += 1
    if seen != len(records):
        raise ValueError("Graph-size stream is incomplete; no partial training scan is accepted")
    by_metric, worst, selected = {}, [], {}
    for metric in METRICS:
        entries = sorted(heaps[metric], reverse=True)
        by_metric[metric] = [entry[2]["index"] for entry in entries]
        for _, index, row in entries:
            if index not in selected:
                worst.append(index);selected[index] = row
    ordinary_rows = [entry[2] for entry in sorted(ordinary, reverse=True) if entry[2]["index"] not in selected][:ordinary_count]
    for row in ordinary_rows:
        selected[row["index"]] = row
    return dict(indices=sorted(selected), worst_indices=worst, warmup_batches=warmup_batches, measure_batches=measure_batches,
                selection=dict(seed=seed, worst_per_metric=worst_per_metric, ordinary_count=ordinary_count,
                               ordinary_indices=[row["index"] for row in ordinary_rows], worst_by_metric=by_metric,
                               selected_records=[selected[index] for index in sorted(selected)]),
                coverage=dict(version=1, kind="complete_train_graph_size_aggregation", binding=copy.deepcopy(binding),
                              structures=seen, complete_training_records_observed=True,
                              verified_full_training_scan=False, graph_size_rows_sha256=digest.hexdigest(),
                              sums=sums, maxima=maxima,
                              interpretation="complete supplied counts only; original graph construction provenance still required"))
