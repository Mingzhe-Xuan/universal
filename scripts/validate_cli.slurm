#!/bin/bash
#SBATCH --job-name=ugnn-cli-check
#SBATCH --partition=compute
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:20:00
#SBATCH --output=runs/cli-check-%j.out
#SBATCH --error=runs/cli-check-%j.err
set -euo pipefail
cd /home/xmz/universal
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OPENBLAS_NUM_THREADS="$SLURM_CPUS_PER_TASK"
task_python=/home/xmz/.venvs/universal/bin/python
task_output="runs/cli-usage-${SLURM_JOB_ID}"
mkdir -p "$task_output"
common=(--model alignn --dataset data/acceptance/bandgap-10.json --task bandgap --config configs/bandgap.yaml)
"$task_python" -m universal_gnn.cli --mode train "${common[@]}" --epochs 15 \
    --logging "$task_output/train" --save "$task_output/first.pt"
"$task_python" -m universal_gnn.cli --mode train "${common[@]}" --resume "$task_output/first.pt" --epochs 30 \
    --logging "$task_output/resume" --save "$task_output/final.pt"
"$task_python" -m universal_gnn.cli --mode infer "${common[@]}" --resume "$task_output/final.pt" \
    --logging "$task_output/infer" --results "$task_output/predictions.json"
"$task_python" -m universal_gnn.cli --mode train "${common[@]}" --epochs 30 \
    --logging "$task_output/continuous" --save "$task_output/continuous.pt"
"$task_python" - "$task_output" <<'PY'
import json
from pathlib import Path
import sys
import torch

root = Path(sys.argv[1])
resumed = torch.load(root / 'final.pt', weights_only=True)
continuous = torch.load(root / 'continuous.pt', weights_only=True)
for name, value in continuous['state_dict'].items():
    torch.testing.assert_close(resumed['state_dict'][name], value, rtol=0, atol=0)
prediction = json.loads((root / 'predictions.json').read_text())
report = json.loads((root / 'resume/report.json').read_text())
assert len(prediction['structures']) == 10
assert report['resume']['kind'] == 'full' and report['resume']['completed_epochs_before'] == 15
torch.testing.assert_close(torch.tensor(prediction['predictions']['bandgap']),
                           torch.tensor(report['predictions']['bandgap']), rtol=0, atol=0)
result = {'passed': True, 'structures': 10, 'epochs': 30,
          'resume_matches_uninterrupted': True, 'inference_matches_reloaded': True,
          'execution': report['execution']}
(root / 'validation.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
PY
