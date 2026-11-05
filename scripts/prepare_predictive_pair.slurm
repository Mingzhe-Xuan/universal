#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=16:00:00
#SBATCH --no-requeue
#SBATCH --output=runs/full-predictive-preparation-%j.out
#SBATCH --error=runs/full-predictive-preparation-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set original provider Python}"
: "${UGNN_MATRIX:?Set full frozen matrix path}"
: "${UGNN_MATRIX_SHA256:?Set canonical matrix SHA}"
: "${UGNN_PAIR:?Set original predictive pair ID}"
: "${UGNN_OUTPUT:?Set fresh output directory}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
exec "$UGNN_PYTHON" scripts/prepare_predictive_pair.py "$UGNN_MATRIX" \
  --matrix-sha256 "$UGNN_MATRIX_SHA256" --pair "$UGNN_PAIR" --output "$UGNN_OUTPUT"
