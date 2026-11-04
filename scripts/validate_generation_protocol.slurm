#!/bin/bash
#SBATCH --job-name=ugnn-generation-regression
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=3G
#SBATCH --time=00:20:00
#SBATCH --output=runs/generation-regression-%j.out
#SBATCH --error=runs/generation-regression-%j.err
set -euo pipefail
cd /home/xmz/universal
export PYTHONPATH="$PWD/src"
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONNOUSERSITE=1
task_python="${UGNN_VENV:-/home/xmz/.venvs/universal-official}/bin/python"
task_output="runs/generation-regression-${SLURM_JOB_ID}"
mkdir "$task_output"
"$task_python" -m pip check
"$task_python" -m pytest -q tests/test_generation_protocol.py tests/test_generation.py \
  tests/test_generation_heldout_runtime.py tests/test_generation_quality_runtime.py tests/test_structure_quality.py \
  tests/test_initialization_runtime.py tests/test_initialization_routes.py \
  tests/test_cli.py::test_generation_continuation_and_old_weights_warm_start \
  --junitxml="$task_output/tests.xml"
python3 - "$task_output" <<'PY'
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
output=Path(sys.argv[1]);suites=list(ET.parse(output/'tests.xml').getroot().iter('testsuite'))
counts={name:sum(int(s.get(name,'0')) for s in suites) for name in ('tests','errors','failures','skipped')}
cases=[case for suite in suites for case in suite.findall('testcase')]
expected={'tests.test_generation_protocol.GenerationProtocolTests':10,
 'tests.test_generation':4,'tests.test_generation_heldout_runtime':5,
 'tests.test_generation_quality_runtime':4,'tests.test_structure_quality.StructuralQualityTests':6,
 'tests.test_initialization_runtime':5,'tests.test_initialization_routes':5,'tests.test_cli':1}
assert Counter(case.get('classname') for case in cases)==expected, 'Incomplete main-test coverage'
assert len({(case.get('classname'),case.get('name')) for case in cases})==40, 'Duplicate main tests'
assert all(counts[name]==0 for name in ('errors','failures','skipped')),counts
assert not any(case.find(tag) is not None for case in cases for tag in ('error','failure','skipped'))
assert counts['tests']>=len(cases),counts
sources=['src/universal_gnn/engine/generation.py','src/universal_gnn/engine/training.py',
 'src/universal_gnn/engine/generative/protocol.py','src/universal_gnn/engine/generative/evaluation.py',
 'src/universal_gnn/engine/generative/quality.py','tests/test_generation_heldout_runtime.py',
 'tests/test_generation_quality_runtime.py','tests/test_initialization_routes.py',
 'src/universal_gnn/engine/verification.py']
report=dict(status='passed',slurm_job_id=os.environ['SLURM_JOB_ID'],tests=counts,main_test_cases=len(cases),
 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 source_sha256={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sources},
 scope='CPU numerical protocol/heldout/quality/resume/initialization-route fixtures; original-model GPU experiments remain separate')
(output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
PY
