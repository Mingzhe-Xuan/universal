"""Full author-released GMTNet dielectric tensors, preserving Cartesian components."""

from collections import OrderedDict
from pathlib import Path
import pickle

from .jarvis import file_sha256, finite_scalar, prepare_records


SOURCE_URL = "https://raw.githubusercontent.com/YKQ98/GMTNet/main/data/jarvis_diele_piezo.pkl"


class TensorDataUnpickler(pickle.Unpickler):
    """Allow the released plain collections/NumPy data, never arbitrary classes."""

    def find_class(self, module, name):
        if (module, name) == ("collections", "OrderedDict"):
            return OrderedDict
        if (module, name) in {("numpy", "dtype"), ("numpy", "ndarray"),
                              ("numpy.core.multiarray", "scalar"),
                              ("numpy.core.multiarray", "_reconstruct")}:
            import numpy as np

            return {"dtype": np.dtype, "ndarray": np.ndarray, "scalar": np.core.multiarray.scalar,
                    "_reconstruct": np.core.multiarray._reconstruct}[name]
        raise pickle.UnpicklingError(f"Unexpected object in tensor data: {module}.{name}")


def plain(value):
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    if hasattr(value, "tolist"):
        return plain(value.tolist())
    return value


def records_from_pickle(source, *, expected_sha256):
    if file_sha256(source) != expected_sha256:
        raise ValueError("GMTNet source checksum mismatch")
    with Path(source).open("rb") as stream:
        records = TensorDataUnpickler(stream).load()
        if stream.read(1):
            raise ValueError("Unexpected trailing pickle content")
    if not isinstance(records, (list, tuple)):
        raise ValueError("GMTNet source must contain a record list")
    for record in records:
        if not isinstance(record, dict):
            yield record
            continue
        normalized = plain(record)
        normalized["jid"] = normalized.get("JARVIS_ID", normalized.get("jid"))
        yield normalized


def dielectric_targets(record):
    value = record.get("dielectric")
    if (not isinstance(value, list) or len(value) != 3 or
            any(not isinstance(row, list) or len(row) != 3 or
                not all(finite_scalar(item) for item in row) for row in value)):
        raise ValueError("missing_nonfinite_or_wrong_tensor_shape")
    return {"dielectric": [[float(item) for item in row] for row in value]}


def prepare_gmtnet(source, output, *, expected_sha256, split_seed=0, execution=None):
    return prepare_records(source, output, records_from_pickle(source, expected_sha256=expected_sha256),
                           kind="dielectric", field="dielectric", channels=9, url=SOURCE_URL,
                           targets=dielectric_targets, split_seed=split_seed,
                           execution={**(execution or {}), "gmtnet_source_sha256": file_sha256(__file__)},
                           audit_details={"tensor_shape": [3, 3],
                               "tensor_convention": "released Cartesian components; dimensionless",
                               "vector_transform": "none; no symmetry projection, Voigt expansion or eigenvalue filter",
                               "label_convention": "source field dielectric retained; dielectric_ionic not added",
                               "input_loading": "entire restricted pickle in memory; full conversion requires Slurm"})
