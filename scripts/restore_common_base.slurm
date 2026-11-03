#!/bin/bash
#SBATCH --job-name=ugnn-common-base
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=runs/common-base-%j.out
#SBATCH --error=runs/common-base-%j.err
set -euo pipefail
cd /home/xmz/universal
python3 -m unittest discover -s tests -p test_offline_wheel_archive.py -v
task_parts=models/official-install/arxiv-base-bootstrap/common-http
printf '%s  %s\n' f8ee179430e7d02d4ec987d0758c9968b9781e98ec01d2c2ed61ed0c7463f4c0 "$task_parts/manifest.json" | sha256sum -c -
python3 scripts/restore_offline_wheels.py "$task_parts/manifest.json" \
  --parts "$task_parts" --archive "$task_parts/common-wheels.tar" \
  --wheelhouse models/official-install/arxiv-linux-base --report "runs/common-resources-${SLURM_JOB_ID}.json"
/home/xmz/.venvs/universal/bin/python -m pip --python /home/xmz/.venvs/universal-base/bin/python install \
  --disable-pip-version-check --no-index --no-cache-dir --only-binary=:all: \
  --find-links models/official-install/arxiv-linux-base \
  'pip==25.3' 'PySocks==1.7.1' 'numpy==1.26.4' 'scipy==1.15.3' 'ase==3.27.0' \
  'PyYAML==6.0.3' 'pytest==9.1.1' 'torch-geometric==2.7.0' 'filelock==4.1.0' \
  'typing-extensions==4.16.0' 'sympy==1.14.0' 'networkx==3.4.2' 'jinja2==3.1.6' \
  'fsspec==2026.9.0' 'mpmath==1.3.0' 'MarkupSafe==3.0.4'
/home/xmz/.venvs/universal-base/bin/python -m pip check
/home/xmz/.venvs/universal-base/bin/python -m pip list --format=json > "runs/common-base-packages-${SLURM_JOB_ID}.json"
printf 'COMMON_BASE_INSTALLED_TORCH_GPU_AND_PROVIDER_CHECKS_STILL_REQUIRED\n'
