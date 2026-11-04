#!/bin/bash
#SBATCH --job-name=ugnn-tensor-groups
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=runs/tensor-groups-%j.out
#SBATCH --error=runs/tensor-groups-%j.err
set -euo pipefail
cd "${UGNN_SOURCE_SNAPSHOT:-/home/xmz/universal}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
task_python="${UGNN_VENV:-/home/xmz/.venvs/universal-official}/bin/python"
: "${UGNN_TENSOR_REPORT:?Set the completed training report path}"
: "${UGNN_TENSOR_OUTPUT:?Set a new assessment directory}"
"$task_python" -S scripts/evaluate_tensor_groups.py --report "$UGNN_TENSOR_REPORT" --shape 3 3 --output "$UGNN_TENSOR_OUTPUT"
