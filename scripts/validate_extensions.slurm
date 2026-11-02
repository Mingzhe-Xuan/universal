#!/bin/bash
#SBATCH --job-name=ugnn-custom
#SBATCH --partition=compute
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:20:00
#SBATCH --output=runs/custom-%j.out
#SBATCH --error=runs/custom-%j.err
set -euo pipefail
cd /home/xmz/universal
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OPENBLAS_NUM_THREADS="$SLURM_CPUS_PER_TASK"
task_python=/home/xmz/.venvs/universal/bin/python
task_output="runs/custom-extensions-${SLURM_JOB_ID}"
mkdir -p "$task_output"
"$task_python" scripts/prepare_molecular_data.py
"$task_python" - "$task_output" <<'PY'
import json
from pathlib import Path
import sys
from universal_gnn.engine.configuration import load_config

config = load_config('configs/custom_knn_gcn.yaml')
config['graph'] = {'name': 'stored'}
config['dataset']['path'] = 'data/acceptance/molecules-g2-10-graphs.json'
Path(sys.argv[1], 'stored.json').write_text(json.dumps(config, indent=2))
PY
"$task_python" -m universal_gnn.cli --mode train --config configs/custom_knn_gcn.yaml --epochs 15 \
    --logging "$task_output/first" --save "$task_output/first.pt"
"$task_python" -m universal_gnn.cli --mode train --config configs/custom_knn_gcn.yaml --epochs 30 \
    --resume "$task_output/first.pt" --logging "$task_output/resume" --save "$task_output/resumed.pt"
"$task_python" -m universal_gnn.cli --mode infer --config configs/custom_knn_gcn.yaml \
    --resume "$task_output/resumed.pt" --logging "$task_output/infer" --results "$task_output/predictions.json"
"$task_python" -m universal_gnn.cli --mode train --config configs/custom_knn_gcn.yaml \
    --logging "$task_output/continuous" --save "$task_output/continuous.pt"
"$task_python" -m universal_gnn.cli --mode train --config "$task_output/stored.json" \
    --logging "$task_output/stored" --save "$task_output/stored.pt"
"$task_python" -m universal_gnn.cli --mode infer --config "$task_output/stored.json" \
    --resume "$task_output/stored.pt" --logging "$task_output/stored-infer" --results "$task_output/stored-predictions.json"
"$task_python" - "$task_output" <<'PY'
import json
from pathlib import Path
import sys
import torch

root = Path(sys.argv[1])
resumed = torch.load(root/'resumed.pt', weights_only=True)
continuous = torch.load(root/'continuous.pt', weights_only=True)
stored = torch.load(root/'stored.pt', weights_only=True)
for name, value in continuous['state_dict'].items():
    torch.testing.assert_close(resumed['state_dict'][name], value, rtol=0, atol=0)
    torch.testing.assert_close(stored['state_dict'][name], value, rtol=0, atol=0)
prediction = json.loads((root/'predictions.json').read_text())
imported = json.loads((root/'stored-predictions.json').read_text())
assert len(prediction['structures']) == 10 and prediction['predictions'] == imported['predictions']
assert continuous['contract_versions'] == {'config':1,'dataset':1,'graph':1,'gnn':1}
report = json.loads((root/'continuous/report.json').read_text())
result = {'passed':True,'structures':10,'resume_matches_continuous':True,'imported_graph_matches_knn':True,
          'contract_versions':continuous['contract_versions'],'extensions':continuous['extensions'],
          'execution':report['execution'],'initial_loss':report['initial_loss'],'final_loss':report['final_loss']}
(root/'validation.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
PY
