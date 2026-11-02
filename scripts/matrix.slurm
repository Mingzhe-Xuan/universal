#!/bin/bash
#SBATCH --job-name=universal-matrix
#SBATCH --partition=compute
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --output=runs/matrix-%A_%a.out
#SBATCH --error=runs/matrix-%A_%a.err
set -euo pipefail
cd /home/xmz/universal
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
/home/xmz/.venvs/universal/bin/python scripts/run_matrix.py run \
    --matrix "${UGNN_MATRIX:-runs/acceptance/matrix.json}" --index "$SLURM_ARRAY_TASK_ID"
