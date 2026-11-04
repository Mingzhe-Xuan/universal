#!/bin/bash
#SBATCH --job-name=ugnn-id-overlap
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=runs/id-overlap-%j.out
#SBATCH --error=runs/id-overlap-%j.err
set -euo pipefail
cd "${UGNN_SOURCE_SNAPSHOT:-/home/xmz/universal}"
export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
task_python="${UGNN_VENV:-/home/xmz/.venvs/universal-official}/bin/python"
: "${UGNN_AUDIT_CONFIG:?Set the complete frozen config}"
: "${UGNN_AUDIT_OUTPUT:?Set a new output directory}"
: "${UGNN_REFERENCE_RELATION:?Declare same_target/derived_target/different_target/unknown}"
"$task_python" -S scripts/audit_pretraining_ids.py --config "$UGNN_AUDIT_CONFIG" \
  --reference models/official/alignn/optb88vdw_bandgap_radius.zip \
  --reference-sha256 f59fb168f64a67f0d191f6b8f0d5402373275a5c9e4ff22a1b551b497b622369 \
  --id-prefix JVASP- --reference-target optb88vdw_bandgap \
  --relation "$UGNN_REFERENCE_RELATION" --output "$UGNN_AUDIT_OUTPUT"
