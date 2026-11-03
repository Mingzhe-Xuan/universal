#!/bin/bash
#SBATCH --job-name=ugnn-full-gmtnet
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:20:00
#SBATCH --output=runs/full-gmtnet-%j.out
#SBATCH --error=runs/full-gmtnet-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src"
task_python=/home/xmz/.venvs/universal-base/bin/python
: "${UGNN_GMTNET_SHA256:?Set the SHA256 recorded in the GMTNet source download receipt}"
"$task_python" -m unittest discover -s tests -p test_gmtnet_preparation.py -v
"$task_python" -m universal_gnn.data.preparation \
  data/downloads/gmtnet-jarvis-diele-piezo.pkl --kind dielectric \
  --source-sha256 "$UGNN_GMTNET_SHA256" --split-seed "${UGNN_SPLIT_SEED:-0}" \
  --output "${UGNN_DATA_OUTPUT:-data/arxiv-v1/gmtnet-dielectric}"
