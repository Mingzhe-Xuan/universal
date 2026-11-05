#!/bin/bash
#SBATCH --partition=compute
#SBATCH --nodelist=node42
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --no-requeue
#SBATCH --output=runs/tensor-train-%j.out
#SBATCH --error=runs/tensor-train-%j.err
set -euo pipefail
: "${UGNN_PYTHON:?Set original provider Python}"
: "${UGNN_CASE:?Set registered seed123 supplemental case}"
: "${UGNN_PREPARATION:?Set complete GPU preparation}"
: "${UGNN_INDEPENDENT_GATE:?Set complete independent pair gate directory}"
: "${UGNN_BUDGET_SECONDS:?Set independently measured reserved budget}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
arguments=(train --case "$UGNN_CASE" --preparation "$UGNN_PREPARATION"
           --independent-gate "$UGNN_INDEPENDENT_GATE" --budget-seconds "$UGNN_BUDGET_SECONDS")
[[ -z "${UGNN_DEFINITIONS:-}" ]] || arguments+=(--definitions "$UGNN_DEFINITIONS")
[[ -z "${UGNN_PRIMARY_MATRIX:-}" ]] || arguments+=(--primary-matrix "$UGNN_PRIMARY_MATRIX")
[[ -z "${UGNN_RECEIPT:-}" ]] || arguments+=(--receipt "$UGNN_RECEIPT")
exec "$UGNN_PYTHON" scripts/run_tensor_case.py "${arguments[@]}"
