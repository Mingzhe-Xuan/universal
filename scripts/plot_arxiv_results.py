"""Export publication SVG/PNG from a hash-bound accepted-result summary."""

import argparse
import json
from pathlib import Path

from universal_gnn.benchmarks.reporting.figures import DEFAULT_PANELS, write_figures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--summary-sha256", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--panels", help="JSON list of task/path/unit/title objects; defaults to E/atom, forces, dielectric and spectrum")
    args = parser.parse_args()
    panels = json.loads(Path(args.panels).read_bytes()) if args.panels else DEFAULT_PANELS
    result = write_figures(args.summary, args.summary_sha256, args.output, panels)
    print(json.dumps({key: result[key] for key in ["accepted_cases", "missing_cases", "summary_sha256"]}))


if __name__ == "__main__":
    main()
