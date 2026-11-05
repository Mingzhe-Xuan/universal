#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=16:00:00
#SBATCH --output=runs/prediction-assessment-%j.out
#SBATCH --error=runs/prediction-assessment-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set original provider Python}"
: "${UGNN_STAGE:?Set post or verify}"
: "${UGNN_MATRIX:?Set frozen original matrix path}"
: "${UGNN_MATRIX_SHA256:?Set frozen original matrix digest}"
: "${UGNN_CASE:?Set completed single-seed case}"
: "${UGNN_OUTPUT:?Set fresh output directory}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
arguments=("$UGNN_STAGE" --matrix "$UGNN_MATRIX" --matrix-sha256 "$UGNN_MATRIX_SHA256"
           --case "$UGNN_CASE" --output "$UGNN_OUTPUT")
if [[ "$UGNN_STAGE" == verify ]]; then
  : "${UGNN_POSTPROCESSING:?Set completed post-processing directory}"
  arguments+=(--postprocessing "$UGNN_POSTPROCESSING")
elif [[ "$UGNN_STAGE" != post ]]; then
  echo 'UGNN_STAGE must be post or verify' >&2
  exit 2
fi
exec "$UGNN_PYTHON" scripts/assess_prediction.py "${arguments[@]}"
