#!/bin/bash
#SBATCH --job-name=ugnn
#SBATCH --partition=compute
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --output=runs/ugnn-%j.out
#SBATCH --error=runs/ugnn-%j.err
set -euo pipefail
if [[ -z "${SLURM_JOB_ID:-}" ]]; then
    echo 'Submit this entry point through sbatch.' >&2
    exit 2
fi
cd "$SLURM_SUBMIT_DIR"
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OPENBLAS_NUM_THREADS="$SLURM_CPUS_PER_TASK"
"${UGNN_PYTHON:-/home/xmz/.venvs/universal/bin/python}" -m universal_gnn.cli "$@"
