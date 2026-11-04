#!/bin/bash
#SBATCH --job-name=ugnn-arxiv-definitions
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=runs/arxiv-definitions-%j.out
#SBATCH --error=runs/arxiv-definitions-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src"
task_output="${UGNN_MATRIX_OUTPUT:-runs/arxiv-v1/definition-${SLURM_JOB_ID}}"
/home/xmz/.venvs/universal-base/bin/python -S scripts/prepare_arxiv_matrix.py --output "$task_output"
