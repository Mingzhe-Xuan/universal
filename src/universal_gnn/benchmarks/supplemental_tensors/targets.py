"""Expand the released VASP contracted labels into unconstrained output formats."""

from universal_gnn.data.preparation.jarvis import finite_scalar

PAIR_INDEX = ((0, 3, 5), (3, 1, 4), (5, 4, 2))


def matrix(record, field, rows):
    value = record.get(field)
    if (not isinstance(value, list) or len(value) != rows or
            any(not isinstance(row, list) or len(row) != 6 or
                not all(finite_scalar(item) for item in row) for row in value)):
        raise ValueError("missing_nonfinite_or_wrong_tensor_shape")
    return value


def piezoelectric_targets(record):
    value = matrix(record, "piezoelectric_C_m2", 3)
    return {"piezoelectric": [[[float(value[i][PAIR_INDEX[j][k]]) for k in range(3)]
                              for j in range(3)] for i in range(3)]}


def elastic_targets(record):
    value = matrix(record, "elastic_total_kbar", 6)
    return {"elastic": [[[[float(value[PAIR_INDEX[i][j]][PAIR_INDEX[k][l]]) * .1
                           for l in range(3)] for k in range(3)]
                         for j in range(3)] for i in range(3)]}
