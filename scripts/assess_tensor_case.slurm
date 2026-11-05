#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=72:00:00
#SBATCH --no-requeue
#SBATCH --output=runs/tensor-assess-%j.out
#SBATCH --error=runs/tensor-assess-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set original provider Python}"
: "${UGNN_STAGE:?Set post or verify}"
: "${UGNN_CASE:?Set completed supplemental case}"
: "${UGNN_OUTPUT:?Set fresh output directory}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1 CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
arguments=("$UGNN_STAGE" --case "$UGNN_CASE" --output "$UGNN_OUTPUT")
[[ -z "${UGNN_DEFINITIONS:-}" ]] || arguments+=(--definitions "$UGNN_DEFINITIONS")
[[ -z "${UGNN_PRIMARY_MATRIX:-}" ]] || arguments+=(--primary-matrix "$UGNN_PRIMARY_MATRIX")
if [[ "$UGNN_STAGE" == verify ]]; then
  : "${UGNN_POSTPROCESSING:?Set completed CPU post output}"
  arguments+=(--postprocessing "$UGNN_POSTPROCESSING")
elif [[ "$UGNN_STAGE" != post ]]; then
  echo 'UGNN_STAGE must be post or verify' >&2
  exit 2
fi
exec "$UGNN_PYTHON" scripts/run_tensor_case.py "${arguments[@]}"
