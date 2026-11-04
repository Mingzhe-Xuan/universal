#!/bin/bash
#SBATCH --job-name=ugnn-checkpoint-regression
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:1
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=runs/checkpoint-regression-%j.out
#SBATCH --error=runs/checkpoint-regression-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
task_python="${UGNN_VENV:-/home/xmz/.venvs/universal-official}/bin/python"
task_output="runs/checkpoint-regression-${SLURM_JOB_ID}"
mkdir "$task_output"
"$task_python" -m pytest -q tests/test_checkpoint_verification.py tests/test_holdout_training.py \
  tests/test_generation_heldout_runtime.py tests/test_generation.py tests/test_forcefield.py \
  tests/test_cli.py::test_generation_continuation_and_old_weights_warm_start \
  --junitxml="$task_output/tests.xml"
python3 - "$task_output" <<'PY'
from collections import Counter
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
output=Path(sys.argv[1]);root=ET.parse(output/'tests.xml').getroot()
counts={name:sum(int(s.get(name,'0')) for s in root.iter('testsuite')) for name in ('tests','errors','failures','skipped')}
expected={'tests.test_checkpoint_verification':7,'tests.test_holdout_training':6,
 'tests.test_generation_heldout_runtime':5,'tests.test_generation':4,'tests.test_forcefield':2,'tests.test_cli':1}
assert Counter(c.get('classname') for c in root.iter('testcase'))==expected,counts
assert all(counts[name]==0 for name in ['errors','failures','skipped']),counts
sources=['src/universal_gnn/engine/verification.py','src/universal_gnn/engine/training.py',
 'src/universal_gnn/engine/generation.py','tests/test_checkpoint_verification.py']
report=dict(status='passed',tests=counts,main_test_cases=25,slurm_job_id=os.environ['SLURM_JOB_ID'],
 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 source_sha256={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sources},
 scope='exact state and scoped deterministic CUDA verification; original tolerance unchanged')
(output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
PY
