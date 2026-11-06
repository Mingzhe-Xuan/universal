# Full molecular execution

The closed domain is the existing eight official-backbone cases and one scratch
KNN+GCN directory plugin, all seed123 with900/100/99000 frames and300 epochs
maximum/patience30. Real joint CUDA/physics/original-network preparation and its
retained successful Slurm parent are required. CPU control tests cannot arm it.

`contracts.py` fixes the domain and full workload. `gates.py` checks the actual
preparation, source/package/configuration hashes and common batch. `runtime.py`
uses the existing full training, CPU post-processing and no-model independent
acceptance. `cohorts.py` separately re-scores the author's1000 test indices from
the complete99000 saved predictions against original labels. `submission.py`
retains managed requests and refuses foreign, unknown or purged claims.

The allocation estimate uses the slowest observed homogeneous100/mixed100
training average as a scheduling proxy for all300 training/validation epochs,
the full99000 heldout, initial/final/reload comparisons and normalization
traversal allowance. It includes50% reserve plus900 seconds, rounded to minutes
with at least one hour. It is not measured evaluation throughput or a proven
runtime bound. Author1000 metrics reuse saved heldout predictions; there is no
second model execution for that cohort. CPU scientific stages have explicit,
separate allocations. Full data, models, stopping rules and physics stay intact.

An execution gate permits a new run; only subsequent full training and independent
raw-label/physics/all-source/cohort checks establish scientific completion.

In CPU Slurm with the registered provider environment, retain a read-only plan:

```bash
PYTHONPATH=src python scripts/run_molecular_case.py plan \
  --case molecular--seed-123--forcefield--cgcnn--pretrained \
  --preparation runs/ACTUAL-PASSED-JOINT-PREPARATION \
  --preparation-terminal runs/ACTUAL-PASSED-JOINT-PREPARATION/terminal-parent.json \
  --post-seconds 86400 --verify-seconds 14400 --output runs/NEW-plan.json
```

These explicit CPU allocations are resource choices, not measured full molecular
post-processing times. The GPU budget is derived from the complete checked
workload. `gate` exports the checked execution gate; `submit` uses the same
options as `plan` and retains six exact requests. Both require fresh output paths
and real positive preparation. Existing/foreign/ambiguous claims stop dispatch.
Known matching jobs may be reused only while their Slurm identities remain
available; a missing handle never causes a fresh training request.

Managed `train` receives the checked preparation/terminal and its planned
`--budget-seconds`, writes only its fixed case directory, and calls the unchanged
training engine. `post --case CASE --output NEW` performs the original full raw
label/physics/source inference plus author-cohort assessment. `verify --case CASE
--postprocessing POST --output NEW` independently checks all saved outputs without
model execution and repeats the author-label calculation. A failed cohort marks
the stage failed even when its preceding full-source checks passed. Re-score
outputs keep original E/F and E/atom units and author index order.
