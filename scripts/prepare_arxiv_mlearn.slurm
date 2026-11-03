#!/bin/bash
#SBATCH --job-name=ugnn-full-mlearn
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:20:00
#SBATCH --output=runs/full-mlearn-%j.out
#SBATCH --error=runs/full-mlearn-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src"
python3 -m unittest discover -s tests -p test_mlearn_preparation.py -v
python3 -m universal_gnn.data.preparation \
  data/downloads/arxiv-matrix-raw/download-receipt.json --kind mlearn_forcefield \
  --split-seed "${UGNN_SPLIT_SEED:-0}" --validation-fraction "${UGNN_VALIDATION_FRACTION:-0.1}" \
  --output "${UGNN_DATA_OUTPUT:-data/arxiv-v1/mlearn-forcefield}"
