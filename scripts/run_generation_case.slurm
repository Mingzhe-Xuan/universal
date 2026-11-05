#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=runs/generation-case-%j.out
#SBATCH --error=runs/generation-case-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set provider Python}"
: "${UGNN_MATRIX:?Set frozen matrix path}"
: "${UGNN_MATRIX_SHA256:?Set frozen matrix digest}"
: "${UGNN_CASE:?Set full generation case ID}"
: "${UGNN_STAGE:?Set train or quality}"
: "${UGNN_BUDGET_SECONDS:?Set declared stage budget}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
if [[ "$UGNN_STAGE" == "train" ]]; then
  : "${UGNN_PREPARATION:?Set passed full generation preparation}"
  exec "$UGNN_PYTHON" scripts/run_generation_case.py "$UGNN_MATRIX" \
    --matrix-sha256 "$UGNN_MATRIX_SHA256" --case "$UGNN_CASE" \
    --stage train --preparation "$UGNN_PREPARATION" --budget-seconds "$UGNN_BUDGET_SECONDS"
elif [[ "$UGNN_STAGE" == "quality" ]]; then
  exec "$UGNN_PYTHON" scripts/run_generation_case.py "$UGNN_MATRIX" \
    --matrix-sha256 "$UGNN_MATRIX_SHA256" --case "$UGNN_CASE" \
    --stage quality --budget-seconds "$UGNN_BUDGET_SECONDS"
else
  echo 'UGNN_STAGE must be train or quality' >&2
  exit 2
fi
