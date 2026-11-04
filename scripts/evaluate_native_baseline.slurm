#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=runs/native-baseline-%j.out
#SBATCH --error=runs/native-baseline-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set provider Python}"
: "${UGNN_MATRIX:?Set frozen matrix path}"
: "${UGNN_MATRIX_SHA256:?Set frozen matrix SHA256}"
: "${UGNN_PROVIDER:?Select original provider}"
: "${UGNN_OUTPUT:?Set a new output directory}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec "$UGNN_PYTHON" scripts/evaluate_native_baseline.py "$UGNN_MATRIX" \
  --provider "$UGNN_PROVIDER" --matrix-sha256 "$UGNN_MATRIX_SHA256" --output "$UGNN_OUTPUT"
