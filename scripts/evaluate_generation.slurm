#!/bin/bash
#SBATCH --job-name=ugnn-generation-quality
#SBATCH --partition=compute
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=12:00:00
#SBATCH --output=runs/generation-quality-%j.out
#SBATCH --error=runs/generation-quality-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src"
task_python="${UGNN_VENV:-/home/xmz/.venvs/universal-official}/bin/python"
task_checkpoint="${UGNN_GENERATION_CHECKPOINT:?Set the last checkpoint with validation selection history}"
task_output="${UGNN_GENERATION_OUTPUT:?Set a fresh independent evaluation output directory}"
"$task_python" -m pip check
"$task_python" scripts/evaluate_generation.py "$task_checkpoint" --output "$task_output" \
  --samples "${UGNN_GENERATION_SAMPLES:-1000}" --draws-per-condition "${UGNN_GENERATION_DRAWS:-5}" \
  --seed "${UGNN_GENERATION_SEED:-456}" --device cuda
