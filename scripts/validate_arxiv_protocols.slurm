#!/bin/bash
#SBATCH --job-name=ugnn-arxiv-protocol
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=512M
#SBATCH --time=00:05:00
#SBATCH --output=runs/arxiv-protocol-%j.out
#SBATCH --error=runs/arxiv-protocol-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src"
python3 - <<'PY'
import json
import os
from pathlib import Path
import subprocess

patterns = ["test_preflight_control.py", "test_split_manifest.py",
            "test_evaluation_metrics.py", "test_validation_selection.py"]
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
for pattern in patterns:
    subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests", "-p", pattern, "-v"], check=True)
result = {"passed": True, "test_modules": patterns, "git_commit": commit,
          "slurm_job_id": os.environ["SLURM_JOB_ID"], "node": os.environ.get("SLURMD_NODENAME"),
          "scope": "17 pure control/protocol/metric tests; no neural model or CUDA execution"}
Path(f"runs/arxiv-protocol-{os.environ['SLURM_JOB_ID']}.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result))
PY
