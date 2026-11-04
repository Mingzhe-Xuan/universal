#!/bin/bash
#SBATCH --job-name=ugnn-native-neighbors
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=04:00:00
#SBATCH --output=runs/native-neighbors-%j.out
#SBATCH --error=runs/native-neighbors-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
: "${UGNN_CONFIG:?Specify the complete scratch training configuration}"
: "${UGNN_RESOLVED_CONFIG:?Specify a new output path}"
: "${UGNN_PYTHON:?Specify the provider virtual environment Python}"
"$UGNN_PYTHON" scripts/prepare_native_neighbors.py --config "$UGNN_CONFIG" --output "$UGNN_RESOLVED_CONFIG"
