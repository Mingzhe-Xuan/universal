#!/bin/bash
#SBATCH --job-name=ugnn-cuda-base
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=12G
#SBATCH --time=00:40:00
#SBATCH --output=runs/cuda-base-%j.out
#SBATCH --error=runs/cuda-base-%j.err
set -euo pipefail
cd /home/xmz/universal
task_catalog=models/official-install/arxiv-base-bootstrap/torch-cuda-catalog.json
task_report="runs/cuda-resource-verification-${SLURM_JOB_ID}.json"
printf '%s  %s\n' c191a5448ae0c5710236fcfa1d4109d7f557988098c6f679247181e3c81be009 "$task_catalog" | sha256sum -c -
/home/xmz/.venvs/universal/bin/python scripts/recover_environment_cache.py "$task_catalog" \
  --wheelhouse models/official-install/arxiv-linux-base --report "$task_report"
python3 - "$task_report" <<'PY'
import json,sys
value=json.load(open(sys.argv[1]))
assert value['complete'] and len(value['resources'])==16,'All exact Torch/CUDA resources must be verified first'
PY
/home/xmz/.venvs/universal/bin/python -m pip --python /home/xmz/.venvs/universal-base/bin/python install \
  --disable-pip-version-check --no-index --no-cache-dir --only-binary=:all: \
  --find-links models/official-install/arxiv-linux-base 'torch==2.7.1+cu128'
/home/xmz/.venvs/universal-base/bin/python -m pip check
python3 - <<'PY'
from pathlib import Path
base=Path('/home/xmz/.venvs/universal-base/lib/python3.10/site-packages')
assert (base/'torch').is_dir()
for name in ('universal','universal-mace','universal-official','universal-equiformer'):
 root=Path('/home/xmz/.venvs')/name/'lib/python3.10/site-packages'
 assert root.is_dir(),f'Missing task environment: {name}'
 (root/'ugnn-common-base.pth').write_text(str(base)+'\n')
 print('TASK_COMMON_BASE_LINKED',name)
PY
/home/xmz/.venvs/universal-base/bin/python -m pip list --format=json > "runs/cuda-base-packages-${SLURM_JOB_ID}.json"
printf 'SHARED_BASE_INSTALLED_PROVIDER_EXTRAS_AND_MODEL_GPU_TESTS_STILL_REQUIRED\n'
