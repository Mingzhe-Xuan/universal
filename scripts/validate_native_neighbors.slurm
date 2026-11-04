#!/bin/bash
#SBATCH --job-name=ugnn-native-neighbor-check
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=runs/native-neighbor-check-%j.out
#SBATCH --error=runs/native-neighbor-check-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
task_output="runs/native-neighbor-check-${SLURM_JOB_ID}"
mkdir "$task_output"
git rev-parse HEAD > "$task_output/commit.txt"
UGNN_NEIGHBOR_PROVIDER=mace /home/xmz/.venvs/universal-mace/bin/python -m pytest \
    scripts/validation_cases/native_neighbors.py -q --junitxml="$task_output/mace.xml"
UGNN_NEIGHBOR_PROVIDER=nequip /home/xmz/.venvs/universal/bin/python -m pytest \
    scripts/validation_cases/native_neighbors.py -q --junitxml="$task_output/nequip.xml"
python3 - "$task_output" <<'PY'
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
output=Path(sys.argv[1]);counts={}
for provider in ('mace','nequip'):
 suites=list(ET.parse(output/(provider+'.xml')).getroot().iter('testsuite'))
 count={k:sum(int(s.get(k,'0')) for s in suites) for k in ('tests','errors','failures','skipped')}
 assert count==dict(tests=5,errors=0,failures=0,skipped=0),count
 counts[provider]=count
sources=['scripts/validation_cases/native_neighbors.py','src/universal_gnn/backbones/official/mace.py',
         'src/universal_gnn/backbones/official/nequip.py','src/universal_gnn/engine/initialization/neighbors.py',
         'src/universal_gnn/backbones/blueprints.py']
report=dict(status='passed',slurm_job_id=os.environ['SLURM_JOB_ID'],tests=counts,
 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 source_sha256={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sources},
 scope='Actual MACE/NequIP native graphs, train-bound calibration and fresh constructor; no formal training')
(output/'report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
PY
