#!/bin/bash
#SBATCH --job-name=universal-workflow
#SBATCH --partition=compute
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:40:00
#SBATCH --output=runs/workflow-%A_%a.out
#SBATCH --error=runs/workflow-%A_%a.err
set -euo pipefail
cd /home/xmz/universal
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export NUMBA_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OPENBLAS_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export DASK_NUM_WORKERS="$SLURM_CPUS_PER_TASK"
models=(cgcnn megnet alignn equiformer nequip mace)
/home/xmz/.venvs/universal/bin/python scripts/run_workflows.py --model "${models[$SLURM_ARRAY_TASK_ID]}"
