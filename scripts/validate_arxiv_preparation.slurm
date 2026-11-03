#!/bin/bash
#SBATCH --job-name=ugnn-arxiv-prep
#SBATCH --partition=compute
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=00:40:00
#SBATCH --output=runs/arxiv-preparation-%j.out
#SBATCH --error=runs/arxiv-preparation-%j.err
set -euo pipefail
cd /home/xmz/universal
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
task_environment="${UGNN_TEST_ENV:-universal}"
case "$task_environment" in
    universal|universal-mace|universal-official) ;;
    *) echo 'UGNN_TEST_ENV must select an existing task environment' >&2; exit 2 ;;
esac
task_python="/home/xmz/.venvs/${task_environment}/bin/python"
task_output="runs/arxiv-preparation-${SLURM_JOB_ID}"
mkdir "$task_output"
git rev-parse HEAD > "$task_output/commit.txt"
"$task_python" -m pip list --format=json > "$task_output/packages.json"
"$task_python" -c 'import torch; assert torch.cuda.is_available(), "Slurm GPU/Torch CUDA unavailable"; print(torch.__version__,torch.cuda.get_device_name())'
"$task_python" -m pytest tests -q --junitxml="$task_output/tests.xml"
"$task_python" scripts/validate_preflight_cuda.py --output "$task_output/cuda-preflight"
