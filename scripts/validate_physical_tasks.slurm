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
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1 UGNN_PHYSICAL_DEVICE=cuda CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
task_python="${UGNN_VENV:-/home/xmz/.venvs/universal-official}/bin/python"
task_output="runs/physical-regression-${SLURM_JOB_ID}"
mkdir "$task_output"
"$task_python" -m pytest -q tests/test_physical_task_validation.py tests/test_finite_difference_control.py tests/test_forcefield_energy_metrics.py \
  tests/test_holdout_training.py --junitxml="$task_output/tests.xml"
"$task_python" - "$task_output" <<'PY'
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
import torch
assert torch.cuda.is_available()
output=Path(sys.argv[1]);root=ET.parse(output/'tests.xml').getroot()
counts={name:sum(int(s.get(name,'0')) for s in root.iter('testsuite')) for name in ('tests','errors','failures','skipped')}
expected={'tests.test_physical_task_validation':10,'tests.test_finite_difference_control.FiniteDifferenceControlTests':4,
 'tests.test_forcefield_energy_metrics':4,'tests.test_holdout_training':6}
cases=list(root.iter('testcase'))
assert Counter(case.get('classname') for case in cases)==expected,counts
assert len({(case.get('classname'),case.get('name')) for case in cases})==24
assert all(counts[name]==0 for name in ['errors','failures','skipped']),counts
sources=['src/universal_gnn/benchmarks/validation/derivatives.py',
 'src/universal_gnn/benchmarks/validation/precision.py',
 'src/universal_gnn/benchmarks/validation/finite_difference.py','src/universal_gnn/engine/evaluation/heldout.py',
 'scripts/validate_other_forcefields.py','tests/test_finite_difference_control.py',
 'tests/test_physical_task_validation.py','tests/test_forcefield_energy_metrics.py','tests/test_holdout_training.py']
report=dict(status='passed',tests=counts,main_test_cases=24,slurm_job_id=os.environ['SLURM_JOB_ID'],device=torch.cuda.get_device_name(),
 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 source_sha256={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sources},
 scope='GCN numerical validation fixtures on GPU, E/atom and heldout regressions; original four models remain separate')
(output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
PY
