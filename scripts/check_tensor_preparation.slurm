#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=runs/tensor-preparation-gate-%j.out
#SBATCH --error=runs/tensor-preparation-gate-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set original provider Python}"
: "${UGNN_PAIR:?Set registered supplemental pair}"
: "${UGNN_PREPARATION:?Set original complete preparation directory}"
: "${UGNN_RECEIPT:?Set original preparation job.json}"
: "${UGNN_OUTPUT:?Set fresh independent gate directory}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES=""
exec "$UGNN_PYTHON" scripts/check_tensor_preparation.py \
  --definitions "${UGNN_DEFINITIONS:-runs/tensor-definition-control-1231/definitions/definitions.json}" \
  --primary-matrix "${UGNN_PRIMARY_MATRIX:-runs/arxiv-v1/definition-947/matrix.json}" \
  --pair "$UGNN_PAIR" --preparation "$UGNN_PREPARATION" --receipt "$UGNN_RECEIPT" --output "$UGNN_OUTPUT"
