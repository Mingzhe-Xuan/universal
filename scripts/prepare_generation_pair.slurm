#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=08:00:00
#SBATCH --output=runs/full-generation-preparation-%j.out
#SBATCH --error=runs/full-generation-preparation-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set provider environment Python}"
: "${UGNN_MATRIX:?Set frozen matrix path}"
: "${UGNN_MATRIX_SHA256:?Set frozen matrix SHA256}"
: "${UGNN_PAIR:?Set generation pair ID}"
: "${UGNN_OUTPUT:?Set a new preparation directory}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
exec "$UGNN_PYTHON" scripts/prepare_generation_pair.py "$UGNN_MATRIX" \
  --pair "$UGNN_PAIR" --output "$UGNN_OUTPUT" --matrix-sha256 "$UGNN_MATRIX_SHA256"
