#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
#SBATCH --output=runs/tensor-pair-dispatch-%j.out
#SBATCH --error=runs/tensor-pair-dispatch-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set original provider Python}"
: "${UGNN_PAIR:?Set original seed123 supplemental pair}"
: "${UGNN_PREPARATION:?Set passed original GPU preparation}"
: "${UGNN_INDEPENDENT_GATE:?Set passed original independent CPU gate directory}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1 CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
args=(--pair "$UGNN_PAIR" --preparation "$UGNN_PREPARATION" --independent-gate "$UGNN_INDEPENDENT_GATE")
[[ -z "${UGNN_DEFINITIONS:-}" ]] || args+=(--definitions "$UGNN_DEFINITIONS")
[[ -z "${UGNN_PRIMARY_MATRIX:-}" ]] || args+=(--primary-matrix "$UGNN_PRIMARY_MATRIX")
exec "$UGNN_PYTHON" scripts/submit_tensor_pair.py "${args[@]}"
