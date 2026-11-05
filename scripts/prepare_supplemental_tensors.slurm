#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --output=runs/supplemental-tensors-%j.out
#SBATCH --error=runs/supplemental-tensors-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set task Python}"
: "${UGNN_ELASTIC_SOURCE:?Set complete SHA-verified elastic source}"
: "${UGNN_OUTPUT:?Set fresh supplemental output directory}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec "$UGNN_PYTHON" scripts/prepare_supplemental_tensors.py \
  --elastic-source "$UGNN_ELASTIC_SOURCE" --output "$UGNN_OUTPUT"
