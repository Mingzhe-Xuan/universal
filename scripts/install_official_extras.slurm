#!/bin/bash
#SBATCH --job-name=ugnn-official-extras
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=runs/official-extras-%j.out
#SBATCH --error=runs/official-extras-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONNOUSERSITE=1
unset PYTHONPATH
python3 scripts/install_official_extras.py --report "runs/official-extras-${SLURM_JOB_ID}.json"
