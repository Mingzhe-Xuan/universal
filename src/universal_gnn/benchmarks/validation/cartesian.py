"""Cartesian response validation conventions; importing this module needs no Torch."""


def response_rank(shape, scope):
    shape = tuple(shape)
    if (scope != "graph" or len(shape) not in {2, 3, 4} or
            any(type(size) is not int or size != 3 for size in shape)):
        raise ValueError("Response geometry acceptance requires graph Cartesian rank2/3/4 output")
    return len(shape)


def rotation_subscripts(rank):
    if type(rank) is not int or rank not in {2, 3, 4}:
        raise ValueError("Cartesian response rotation requires rank2/3/4")
    source, target = "abcd"[:rank], "ijkl"[:rank]
    factors = [out + old for out, old in zip(target, source)]
    return ",".join([*factors, "n" + source]) + "->n" + target
