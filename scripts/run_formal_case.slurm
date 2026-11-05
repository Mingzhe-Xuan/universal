#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=runs/formal-case-%j.out
#SBATCH --error=runs/formal-case-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set provider environment Python}"
: "${UGNN_MATRIX:?Set frozen matrix path}"
: "${UGNN_MATRIX_SHA256:?Set frozen matrix digest}"
: "${UGNN_CASE:?Set predictive case ID}"
: "${UGNN_PREPARATION:?Set passed complete-data preparation directory}"
: "${UGNN_BUDGET_SECONDS:?Set declared wall budget in seconds}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
exec "$UGNN_PYTHON" scripts/run_formal_case.py "$UGNN_MATRIX" \
  --matrix-sha256 "$UGNN_MATRIX_SHA256" --case "$UGNN_CASE" \
  --preparation "$UGNN_PREPARATION" --budget-seconds "$UGNN_BUDGET_SECONDS"
