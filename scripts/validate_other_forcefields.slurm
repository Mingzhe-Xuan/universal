#!/bin/bash
#SBATCH --job-name=other-forcefields
#SBATCH --partition=compute
#SBATCH --array=0-4%2
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G
#SBATCH --time=00:40:00
#SBATCH --output=runs/other-forcefields-%A_%a.out
#SBATCH --error=runs/other-forcefields-%A_%a.err
set -euo pipefail
test -n "${SLURM_JOB_ID:-}"
cd "$SLURM_SUBMIT_DIR"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
models=(alignn cgcnn megnet nequip equiformer)
interpreters=(/home/xmz/.venvs/universal-official/bin/python /home/xmz/.venvs/universal-official/bin/python /home/xmz/.venvs/universal-official/bin/python /home/xmz/.venvs/universal/bin/python /home/xmz/.venvs/universal-equiformer/bin/python)
index="${SLURM_ARRAY_TASK_ID}"
numeric=()
if [[ "${models[$index]}" == alignn ]]; then numeric=(--fd-step .0002); fi
"${interpreters[$index]}" scripts/validate_other_forcefields.py --model "${models[$index]}" --output "runs/other-forcefields-${SLURM_ARRAY_JOB_ID}/${models[$index]}" "${numeric[@]}" "$@"
