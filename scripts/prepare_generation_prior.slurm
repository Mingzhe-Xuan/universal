#!/bin/bash
#SBATCH --job-name=ugnn-generation-prior
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --output=runs/generation-prior-%j.out
#SBATCH --error=runs/generation-prior-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src"
python3 -S -m unittest discover -s tests -p test_generation_protocol.py -v
python3 -S scripts/prepare_generation_prior.py \
  data/arxiv-v1/perov5/structures.jsonl data/arxiv-v1/perov5/split.json \
  --output "${UGNN_PRIOR_OUTPUT:-data/arxiv-v1/perov5/training-cell-prior.json}"
