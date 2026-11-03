#!/bin/bash
#SBATCH --job-name=ugnn-wheel-recovery
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=12G
#SBATCH --time=00:20:00
#SBATCH --output=runs/wheel-recovery-%j.out
#SBATCH --error=runs/wheel-recovery-%j.err
set -euo pipefail
cd /home/xmz/universal
task_catalog="${UGNN_WHEEL_CATALOG:-models/official-install/arxiv-base-bootstrap/torch-cuda-catalog.json}"
/home/xmz/.venvs/universal/bin/python -m unittest discover -s tests -p test_environment_cache.py -v
/home/xmz/.venvs/universal/bin/python scripts/recover_environment_cache.py "$task_catalog" \
  --wheelhouse models/official-install/arxiv-linux-base \
  --report "runs/wheel-recovery-${SLURM_JOB_ID}.json"
