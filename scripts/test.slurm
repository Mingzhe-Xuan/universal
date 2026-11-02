#!/bin/bash
#SBATCH --job-name=universal-unit
#SBATCH --partition=compute
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=runs/unit-%j.out
#SBATCH --error=runs/unit-%j.err
set -euo pipefail
cd /home/xmz/universal
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
"${UGNN_PYTHON:-/home/xmz/.venvs/universal/bin/python}" -m pytest -q tests
