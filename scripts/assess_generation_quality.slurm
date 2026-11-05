#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=04:00:00
#SBATCH --output=runs/generation-assessment-%j.out
#SBATCH --error=runs/generation-assessment-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set provider Python with matching numeric packages}"
: "${UGNN_MATRIX:?Set frozen matrix path}"
: "${UGNN_MATRIX_SHA256:?Set frozen matrix digest}"
: "${UGNN_CASE:?Set completed full generation case}"
: "${UGNN_OUTPUT:?Set new assessment directory}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec "$UGNN_PYTHON" scripts/assess_generation_quality.py \
  --matrix "$UGNN_MATRIX" --matrix-sha256 "$UGNN_MATRIX_SHA256" \
  --case "$UGNN_CASE" --output "$UGNN_OUTPUT"
