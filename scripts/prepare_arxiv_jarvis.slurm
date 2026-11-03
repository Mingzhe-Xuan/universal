#!/bin/bash
#SBATCH --job-name=ugnn-full-jarvis
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:40:00
#SBATCH --output=runs/full-jarvis-%j.out
#SBATCH --error=runs/full-jarvis-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src"
task_kind="${UGNN_DATA_KIND:-bandgap}"
case "$task_kind" in
  bandgap) task_source=data/downloads/jarvis-dft3d-38521619.zip ;;
  phonon_dos|electron_dos) task_source=data/downloads/jarvis-edos-pdos-29216859.zip ;;
  *) echo 'Unknown UGNN_DATA_KIND' >&2; exit 2 ;;
esac
python3 -m unittest discover -s tests -p test_jarvis_preparation.py -v
python3 -m universal_gnn.data.preparation "$task_source" \
  --kind "$task_kind" --split-seed "${UGNN_SPLIT_SEED:-0}" \
  --metal-threshold "${UGNN_METAL_THRESHOLD:-0.01}" \
  --output "${UGNN_DATA_OUTPUT:-data/arxiv-v1/$task_kind}"
