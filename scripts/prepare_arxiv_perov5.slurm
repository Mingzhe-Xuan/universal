#!/bin/bash
#SBATCH --job-name=ugnn-full-perov5
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:20:00
#SBATCH --output=runs/full-perov5-%j.out
#SBATCH --error=runs/full-perov5-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src"
task_python=/home/xmz/.venvs/universal-base/bin/python
"$task_python" -m unittest discover -s tests -p 'test_perov5*.py' -v
"$task_python" -m universal_gnn.data.preparation \
  "${UGNN_SOURCE_RECEIPT:-data/downloads/arxiv-matrix-raw/perov5-receipt.json}" \
  --kind perov5 --output "${UGNN_DATA_OUTPUT:-data/arxiv-v1/perov5}"
