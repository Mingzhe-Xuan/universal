"""Check running-job GPU evidence across Slurm accounting field versions."""

import re


def running_gpu_allocation(fields, *, job_id, user):
    if (fields.get("JobId") != job_id or fields.get("UserId", "").split("(")[0] != user or
            fields.get("JobState") != "RUNNING" or
            fields.get("NodeList") in (None, "", "(null)", "None")):
        raise RuntimeError("Require this user's current running Slurm job on allocated nodes")
    name = "AllocTRES" if "AllocTRES" in fields else "TRES"
    resources = dict(item.split("=", 1) for item in fields.get(name, "").split(",") if "=" in item)
    gpu = [value for key, value in resources.items() if key == "gres/gpu" or key.startswith("gres/gpu:")]
    if gpu:
        if any(not re.fullmatch(r"[1-9][0-9]*", value) for value in gpu):
            raise RuntimeError("Explicit GPU allocation count must be positive")
        return dict(gpus=max(map(int, gpu)), evidence=name, node_list=fields["NodeList"])
    if name == "AllocTRES":
        raise RuntimeError("Explicit Slurm allocation has no GPU; do not substitute request fields")
    count, nodes = 0, fields.get("NumNodes", "")
    if not re.fullmatch(r"[1-9][0-9]*", nodes):
        raise RuntimeError("Legacy GPU allocation needs a positive allocated node count")
    for token in fields.get("TresPerNode", fields.get("TRESPerNode", "")).split(","):
        if not token.startswith(("gres:gpu", "gres/gpu")):
            continue
        match = re.fullmatch(r"gres[:/]gpu(?::[A-Za-z0-9_.+-]+)?[:=]([1-9][0-9]*)", token)
        if match is None:
            raise RuntimeError("Invalid legacy per-node GPU allocation count")
        count += int(match.group(1))
    if not count:
        raise RuntimeError("Formal execution requires a Slurm GPU allocation")
    return dict(gpus=count * int(nodes), evidence="running_nodes_and_TresPerNode", node_list=fields["NodeList"])
