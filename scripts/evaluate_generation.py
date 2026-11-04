"""Independent validation-best conditional sampling evaluation; execute through Slurm."""

import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, help="Last checkpoint containing validation selection history")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--draws-per-condition", type=int, default=5)
    parser.add_argument("--seed", type=int, default=456)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Generation quality evaluation must run through Slurm")
    from universal_gnn.engine.generative.quality import run_generation_quality

    print(json.dumps(run_generation_quality(args.checkpoint, args.output, count=args.samples,
                                            draws_per_condition=args.draws_per_condition,
                                            seed=args.seed, device=args.device)))


if __name__ == "__main__":
    main()
