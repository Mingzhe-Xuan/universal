#!/bin/bash
#SBATCH --job-name=ugnn-fresh-check
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=runs/official-fresh-%j.out
#SBATCH --error=runs/official-fresh-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
task_python=/home/xmz/.venvs/universal-official/bin/python
task_xml="runs/official-fresh-${SLURM_JOB_ID}-regression.xml"
"$task_python" -m pytest tests/test_initialization_runtime.py tests/test_official.py -q --junitxml="$task_xml"
python3 - "$task_xml" <<'PY'
import sys,xml.etree.ElementTree as ET
suites=list(ET.parse(sys.argv[1]).getroot().iter('testsuite'))
assert sum(int(s.get('tests','0')) for s in suites)>0
assert not any(int(s.get(k,'0')) for s in suites for k in ('errors','failures','skipped'))
PY
"$task_python" scripts/validate_official_scratch.py --output "runs/official-fresh-${SLURM_JOB_ID}"
