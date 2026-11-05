#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
#SBATCH --output=runs/pair-submission-%j.out
#SBATCH --error=runs/pair-submission-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set original provider Python}"
: "${UGNN_MATRIX:?Set frozen full matrix}"
: "${UGNN_MATRIX_SHA256:?Set matrix canonical SHA}"
: "${UGNN_PAIR:?Set full pair ID}"
: "${UGNN_PREPARATION:?Set full preparation output}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec "$UGNN_PYTHON" scripts/submit_formal_pair.py "$UGNN_MATRIX" \
  --matrix-sha256 "$UGNN_MATRIX_SHA256" --pair "$UGNN_PAIR" \
  --preparation "$UGNN_PREPARATION"
