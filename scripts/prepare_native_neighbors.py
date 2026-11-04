"""Prepare original training graph statistics under Slurm before scratch capacity/training."""

import argparse
import json
import os
from pathlib import Path
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Native graph preparation must run through Slurm")
    output = Path(args.output)
    if output.exists() or output.is_symlink():
        parser.error("Output already exists; never overwrite a resolved initialization configuration")
    from universal_gnn.engine.initialization.neighbors import prepare_native_neighbors
    from universal_gnn.engine.configuration import load_config

    resolved = prepare_native_neighbors(load_config(args.config))
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(resolved, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.link(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    print(json.dumps({"status": "complete", "output": str(output),
                      "neighbor_statistics": resolved["backbone"]["neighbor_statistics"]}))


if __name__ == "__main__":
    main()
