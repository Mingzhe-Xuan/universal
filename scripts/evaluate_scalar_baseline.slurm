#!/bin/bash
#SBATCH --job-name=ugnn-scalar-baseline
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=runs/scalar-baseline-%j.out
#SBATCH --error=runs/scalar-baseline-%j.err
set -euo pipefail
cd "${UGNN_SOURCE_SNAPSHOT:-/home/xmz/universal}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
task_python="${UGNN_VENV:-/home/xmz/.venvs/universal-official}/bin/python"
: "${UGNN_BASELINE_CONFIG:?Set a frozen full-data config path}"
task_output="${UGNN_BASELINE_OUTPUT:-runs/arxiv-v1/scalar-baseline-${SLURM_JOB_ID}}"
"$task_python" scripts/evaluate_scalar_baseline.py --config "$UGNN_BASELINE_CONFIG" --output "$task_output"
