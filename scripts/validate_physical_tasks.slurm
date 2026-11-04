#!/bin/bash
#SBATCH --job-name=ugnn-physical-regression
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:1
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=runs/physical-regression-%j.out
#SBATCH --error=runs/physical-regression-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1 UGNN_PHYSICAL_DEVICE=cuda
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
task_python="${UGNN_VENV:-/home/xmz/.venvs/universal-official}/bin/python"
task_output="runs/physical-regression-${SLURM_JOB_ID}"
mkdir "$task_output"
"$task_python" -m pytest -q tests/test_physical_task_validation.py tests/test_forcefield_energy_metrics.py \
  tests/test_holdout_training.py --junitxml="$task_output/tests.xml"
"$task_python" - "$task_output" <<'PY'
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
import torch
assert torch.cuda.is_available()
output=Path(sys.argv[1]);root=ET.parse(output/'tests.xml').getroot()
counts={name:sum(int(s.get(name,'0')) for s in root.iter('testsuite')) for name in ('tests','errors','failures','skipped')}
assert len(list(root.iter('testcase')))==14 and counts==dict(tests=14,errors=0,failures=0,skipped=0),counts
sources=['src/universal_gnn/benchmarks/validation/derivatives.py','src/universal_gnn/engine/evaluation/heldout.py',
 'tests/test_physical_task_validation.py','tests/test_forcefield_energy_metrics.py','tests/test_holdout_training.py']
report=dict(status='passed',tests=counts,slurm_job_id=os.environ['SLURM_JOB_ID'],device=torch.cuda.get_device_name(),
 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 source_sha256={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sources},
 scope='GCN numerical validation fixtures on GPU, E/atom and heldout regressions; original four models remain separate')
(output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
PY
