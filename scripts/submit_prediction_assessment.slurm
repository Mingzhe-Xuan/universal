#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=runs/prediction-post-dispatch-%j.out
#SBATCH --error=runs/prediction-post-dispatch-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set original provider Python}"
: "${UGNN_MATRIX:?Set original frozen matrix path}"
: "${UGNN_MATRIX_SHA256:?Set original frozen matrix digest}"
: "${UGNN_PAIR:?Set active predictive pair}"
: "${UGNN_DISPATCH_JOB:?Set successful original pair-gate job}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec "$UGNN_PYTHON" scripts/submit_prediction_assessment.py "$UGNN_MATRIX" \
  --matrix-sha256 "$UGNN_MATRIX_SHA256" --pair "$UGNN_PAIR" \
  --dispatch-job "$UGNN_DISPATCH_JOB" --post-hours "${UGNN_POST_HOURS:-72}" \
  --verify-hours "${UGNN_VERIFY_HOURS:-4}"
