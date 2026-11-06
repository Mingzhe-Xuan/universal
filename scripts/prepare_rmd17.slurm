#!/bin/bash
#SBATCH --job-name=ugnn-full-rmd17
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=runs/full-rmd17-%j.out
#SBATCH --error=runs/full-rmd17-%j.err
set -euo pipefail
: "${UGNN_SOURCE_CHECKOUT:?Set the clean pinned source checkout}"
: "${UGNN_RMD17_OUTPUT:?Set a fresh output directory}"
cd "$UGNN_SOURCE_CHECKOUT"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=""
task_python=${UGNN_PYTHON:-/home/xmz/.venvs/universal-official/bin/python}
"$task_python" scripts/prepare_rmd17.py \
  --raw "${UGNN_RMD17_RAW:-data/arxiv-v1/molecular-rmd17-v4/raw}" \
  --output "$UGNN_RMD17_OUTPUT"
